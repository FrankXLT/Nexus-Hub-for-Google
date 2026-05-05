/**
 * Module: Code.gs
 * Purpose: Nexus for Google - Apps Script Backend Router.
 * This file serves the web app interface and acts as a secure bridge to the Python VM.
 */

/**
 * Purpose: Includes HTML files for templating.
 * Expected Inputs: filename (string) - The name of the HTML file to include.
 * Expected Outputs: string - The HTML content.
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/**
 * Purpose: Serves the initial HTML interface for the web app.
 * Expected Inputs: e (Object) - The event object from Google Apps Script.
 * Expected Outputs: HtmlOutput - The rendered Index.html template.
 */
function doGet(e) {
  const template = HtmlService.createTemplateFromFile('Index');
  template.nexusConfig = JSON.stringify(NEXUS_CONFIG);
  return template.evaluate()
    .setTitle('Nexus')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Purpose: Securely stores the HMAC secret in the project properties.
 * Expected Inputs: secretString (string) - The exact secret used for authentication.
 * Expected Outputs: None.
 */
function configureHMAC(secretString) {
  // If no secret string is provided, halt execution and throw an error.
  if (!secretString) {
    throw new Error("Must provide a secret string.");
  }
  const scriptProperties = PropertiesService.getScriptProperties();
  scriptProperties.setProperty('NEXUS_HMAC_SECRET', secretString);
  Logger.log("HMAC Secret successfully stored. PLEASE DELETE THE STRING FROM THIS FILE NOW.");
}

/**
 * Purpose: Generates an HMAC-SHA256 signature for the given payload to verify sender identity.
 * Expected Inputs: 
 *   secret (string) - The shared secret key.
 *   payloadString (string) - The stringified JSON payload.
 * Expected Outputs: string - The hex-encoded signature.
 */
function generateHMACSignature_(secret, payloadString) {
  const byteSignature = Utilities.computeHmacSha256Signature(payloadString, secret);
  // Convert the byte array into a continuous hex string.
  // We loop over each byte, handle negatives, and format as 2-character hex.
  return byteSignature.map(function(byte) {
    // If the byte is negative, adjust it to a positive value (2's complement).
    const v = (byte < 0) ? 256 + byte : byte;
    return ("0" + v.toString(16)).slice(-2);
  }).join("");
}

/**
 * Purpose: Securely transmits a payload to the Python VM Webhook using HMAC signatures.
 * Expected Inputs: 
 *   endpoint (string) - The specific API route (e.g., '/api/update').
 *   payload (Object) - The JavaScript object containing the data to send.
 *   method (string) - HTTP method, defaults to 'post'.
 * Expected Outputs: Object - The parsed JSON response from the VM.
 */
function sendToNexusVM(endpoint, payload, method = 'post') {
  const scriptProperties = PropertiesService.getScriptProperties();
  const secret = scriptProperties.getProperty('NEXUS_HMAC_SECRET');
  
  // If the secret is not found, stop because we cannot authenticate.
  if (!secret) {
    throw new Error("NEXUS_HMAC_SECRET is not configured in Script Properties. Please run configureHMAC() first.");
  }
  
  // Inject timestamp for Replay Protection
  const currentTimestamp = Math.floor(Date.now() / 1000);
  payload.timestamp = currentTimestamp;
  
  const payloadString = JSON.stringify(payload);
  const signature = generateHMACSignature_(secret, payloadString);
  
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + endpoint;
  
  const options = {
    'method': method,
    'contentType': 'application/json',
    'headers': {
      'X-Nexus-Signature': signature
    },
    'muteHttpExceptions': true
  };
  
  if (method.toLowerCase() !== 'get') {
    options.payload = payloadString;
  }
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    // If the HTTP response indicates success (200-level), return the parsed JSON.
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(responseText);
    } 
    // Otherwise, throw an error containing the failure details.
    else {
      throw new Error("VM Error (" + responseCode + "): " + responseText);
    }
  } catch (error) {
    Logger.log("Failed to contact Nexus VM: " + error.message);
    throw new Error("Communication with Nexus VM failed. Ensure the VM is running and accessible.");
  }
}

/**
 * Purpose: Triggers a comprehensive diagnostic ping to the Python VM.
 * Expected Inputs: None.
 * Expected Outputs: Object - A dictionary with 'success' status and the diagnostic report data.
 */
function runSystemDiagnostics() {
  const payload = { action: "ping_diagnostics" };
  try {
    const result = sendToNexusVM("/api/health", payload);
    Logger.log("Diagnostic Ping Success: " + JSON.stringify(result));
    return { success: true, data: result };
  } catch (error) {
    Logger.log("Diagnostic Ping Failed: " + error.message);
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Runs a sandbox prompt against an artifact's raw text.
 * Expected Inputs: payload (Object) - Data containing artifact_id and prompt_string.
 * Expected Outputs: Object - A response object containing 'success' and 'data' or 'error'.
 */
function runSandboxPrompt(payload) {
  try {
    const result = sendToNexusVM("/api/sandbox", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Queues items for the materialization pipeline.
 * Expected Inputs: payload (Object) - Contains artifact_ids.
 * Expected Outputs: Object - A response object indicating success or failure.
 */
function materializeSelectedItems(payload) {
  try {
    const result = sendToNexusVM("/api/workflows/materialize", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Bulk updates multiple artifacts using continuation tokens for timeout protection.
 * Expected Inputs: payload (Object) - Contains artifact_ids and metadata to apply.
 * Expected Outputs: Object - Response indicating success or error.
 */
function bulkUpdateArtifacts(payload) {
  const MAX_BATCH_SIZE = 50;
  // If the payload contains more items than the maximum batch size, slice it into smaller parts.
  if (payload.artifact_ids && payload.artifact_ids.length > MAX_BATCH_SIZE) {
    const batch = payload.artifact_ids.slice(0, MAX_BATCH_SIZE);
    const remaining = payload.artifact_ids.slice(MAX_BATCH_SIZE);
    payload.artifact_ids = batch;
    payload.continuation_token = Utilities.base64Encode(JSON.stringify(remaining));
  }
  try {
    const result = sendToNexusVM("/api/bulk-update", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Executes an AST search via the backend API.
 * Expected Inputs: query (string) - The search string.
 * Expected Outputs: Object - The matching data.
 */
function searchArtifacts(query) {
  try {
    const payload = {};
    const result = sendToNexusVM("/api/artifacts/search?q=" + encodeURIComponent(query) + "&limit=50&offset=0", payload, 'get');
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Runs the AI RAG query.
 * Expected Inputs: payload (Object) - Contains the user's question.
 * Expected Outputs: Object - The AI response.
 */
function runAskAI(payload) {
  try {
    const result = sendToNexusVM("/api/ask", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Fetches user preferences for boot routing.
 * Expected Inputs: None.
 * Expected Outputs: Object - User settings data.
 */
function getUserPreferences() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/settings/pipeline";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    // If the request succeeds, parse and return the settings.
    if (responseCode >= 200 && responseCode < 300) {
      const data = JSON.parse(response.getContentText());
      return { success: true, data: data.settings };
    } 
    // Otherwise, throw an error.
    else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Fetches Heatmap data.
 * Expected Inputs: None.
 * Expected Outputs: Object - The heatmap analytics data.
 */
function getHeatmapData() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/analytics/heatmap";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    // If successful, return the parsed data.
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } 
    // Otherwise, throw an error.
    else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Fetches Threads Sankey data.
 * Expected Inputs: None.
 * Expected Outputs: Object - The thread analytics data.
 */
function getThreadsData() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/analytics/threads";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    // If successful, return the parsed data.
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } 
    // Otherwise, throw an error.
    else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Fetches ROI Dashboard data.
 * Expected Inputs: None.
 * Expected Outputs: Object - Return on investment and metrics data.
 */
function getROIDashboard() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/analytics/roi-dashboard";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    // If successful, wrap the data in a success envelope.
    if (responseCode >= 200 && responseCode < 300) {
      return { success: true, data: JSON.parse(response.getContentText()) };
    } 
    // Otherwise, throw an error.
    else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Pings Health API.
 * Expected Inputs: None.
 * Expected Outputs: Object - System health status.
 */
function pingHealthAPI() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/health";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    // If successful, mark the status as success and return data.
    if (responseCode >= 200 && responseCode < 300) {
      return { status: "success", data: JSON.parse(response.getContentText()) };
    } 
    // Otherwise, throw an error.
    else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Updates the Safe Mode pipeline settings.
 * Expected Inputs: payload (Object) - Contains safe mode configurations.
 * Expected Outputs: Object - Success response from VM.
 */
function updateSafeMode(payload) {
  try {
    const result = sendToNexusVM("/api/settings/pipeline", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Fetches configured retention rules.
 * Expected Inputs: None.
 * Expected Outputs: Object - Array of retention rule data.
 */
function getRetentionRules() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/retention/rules";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    // If the request succeeds, return parsed rules.
    if (response.getResponseCode() >= 200 && response.getResponseCode() < 300) {
      return JSON.parse(response.getContentText());
    } 
    // Otherwise, throw a general error.
    else {
      throw new Error("VM Error");
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Adds a new retention rule to the system.
 * Expected Inputs: payload (Object) - The rule data to add.
 * Expected Outputs: Object - Response indicating success or failure.
 */
function addRetentionRule(payload) {
  try {
    return sendToNexusVM("/api/retention/rules", payload);
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Deletes a specified retention rule.
 * Expected Inputs: payload (Object) - Contains the rule_id to delete.
 * Expected Outputs: Object - Status of the deletion request.
 */
function deleteRetentionRule(payload) {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/retention/rules/" + payload.rule_id;
  
  const options = { 'method': 'delete', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    // If the deletion was acknowledged, parse and return the response.
    if (response.getResponseCode() >= 200 && response.getResponseCode() < 300) {
      return JSON.parse(response.getContentText());
    } 
    // Otherwise, throw an error.
    else {
      throw new Error("VM Error");
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Manually triggers the retention sweep task.
 * Expected Inputs: None.
 * Expected Outputs: Object - Results of the sweep task trigger.
 */
function triggerRetentionSweep() {
  try {
    return sendToNexusVM("/api/retention/sweep", {});
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Fetches comprehensive pipeline settings from the VM.
 * Expected Inputs: None.
 * Expected Outputs: Object - Configuration JSON from the backend.
 */
function getPipelineSettings() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/settings/pipeline";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    // If successful, return parsed settings.
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } 
    // Otherwise, throw an error.
    else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Purpose: Saves updated pipeline settings to the VM.
 * Expected Inputs: payload (Object) - The new pipeline configuration options.
 * Expected Outputs: Object - Response confirming the save operation.
 */
function savePipelineSettings(payload) {
  try {
    const result = sendToNexusVM("/api/settings/pipeline", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Queues a historical import request based on a specific Gmail search query.
 * Expected Inputs: query (string) - The Gmail search string (e.g. "older_than:30d").
 * Expected Outputs: Object - VM confirmation of the queued job.
 */
function queueHistoricalImport(query) {
  try {
    const result = sendToNexusVM("/api/ingestion/queue-historical", { search_query: query });
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Updates custom extraction rules for a specific entity in the taxonomy.
 * Expected Inputs: 
 *   entityType (string) - "correspondents" or "purposes"
 *   id (string) - The entity ID
 *   rules (string) - The custom extraction rules payload.
 *   autoArchive (boolean) - Auto-archive setting (only applicable for purposes)
 * Expected Outputs: Object - Response containing the updated entity confirmation.
 */
function updateEntityRules(entityType, id, rules, autoArchive = false) {
  try {
    const payload = { custom_extraction_rules: rules };
    // If the entity is a purpose, we also apply the autoArchive flag.
    if (entityType === 'purposes') {
      payload.auto_archive = autoArchive;
    }
    const result = sendToNexusVM(`/api/entities/${entityType}/${id}`, payload, 'put');
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Submits a zero-shot taxonomy rule creation request to the VM.
 * Expected Inputs: payload (Object) - Contains artifact_ids and user instruction.
 * Expected Outputs: Object - Result of the rule execution.
 */
function submitZeroShotRule(payload) {
  try {
    const result = sendToNexusVM("/api/taxonomy/zero-shot-rule", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Purpose: Fetches Quota Governor stats from the VM to display health/usage.
 * Expected Inputs: None.
 * Expected Outputs: Object - Quota API response containing usage counts and limits.
 */
function getQuotaGovernor() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/health/quota";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    // If successful, return the parsed quota stats.
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } 
    // Otherwise, throw an error reporting the failure.
    else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}
