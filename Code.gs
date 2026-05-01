/**
 * Nexus Hub for Google - Apps Script Backend Router
 * This file serves the web app and acts as a secure bridge to the Python VM.
 */

/**
 * Includes HTML files for templating.
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/**
 * Serves the initial HTML interface for the web app.
 *
 * @param {Object} e - The event object.
 * @returns {HtmlOutput} The rendered Index.html template.
 */
function doGet(e) {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('Nexus Hub')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * ACTION REQUIRED: ONE-TIME SETUP
 * Run this function once from the Apps Script editor to securely store your
 * shared HMAC secret in the project properties.
 * 
 * CRITICAL: After executing this function, IMMEDIATELY DELETE the secretString 
 * from the code editor to prevent credential leaks.
 * 
 * @param {string} secretString - The exact same string you placed in the VM's .env file.
 */
function configureHMAC(secretString) {
  if (!secretString) {
    throw new Error("Must provide a secret string.");
  }
  const scriptProperties = PropertiesService.getScriptProperties();
  scriptProperties.setProperty('NEXUS_HMAC_SECRET', secretString);
  Logger.log("HMAC Secret successfully stored. PLEASE DELETE THE STRING FROM THIS FILE NOW.");
}

/**
 * Generates an HMAC-SHA256 signature for the given payload.
 *
 * @param {string} secret - The shared secret key.
 * @param {string} payloadString - The stringified JSON payload.
 * @returns {string} The hex-encoded signature.
 */
function generateHMACSignature_(secret, payloadString) {
  const byteSignature = Utilities.computeHmacSha256Signature(payloadString, secret);
  // Convert byte array to hex string
  return byteSignature.map(function(byte) {
    const v = (byte < 0) ? 256 + byte : byte;
    return ("0" + v.toString(16)).slice(-2);
  }).join("");
}

/**
 * Securely transmits a payload to the Python VM Webhook.
 * 
 * WARNING: This function must ONLY be called asynchronously from the client-side UI
 * via `google.script.run.withSuccessHandler().sendToNexusVM(...)`. It should never
 * be invoked directly by other server-side triggers unless the context is fully trusted.
 * 
 * @param {string} endpoint - The specific API route (e.g., '/api/update').
 * @param {Object} payload - The JavaScript object containing the data to send.
 * @returns {Object} The JSON response from the VM, parsed as an object.
 */
function sendToNexusVM(endpoint, payload, method = 'post') {
  const scriptProperties = PropertiesService.getScriptProperties();
  const secret = scriptProperties.getProperty('NEXUS_HMAC_SECRET');
  
  if (!secret) {
    throw new Error("NEXUS_HMAC_SECRET is not configured in Script Properties. Please run configureHMAC() first.");
  }
  
  // Inject timestamp for Replay Protection
  const currentTimestamp = Math.floor(Date.now() / 1000);
  payload.timestamp = currentTimestamp;
  
  const payloadString = JSON.stringify(payload);
  const signature = generateHMACSignature_(secret, payloadString);
  
  // Ensure the VM_URL is also set in properties or define a constant here.
  // For development, assuming localhost proxy or specific IP.
  // In production, this should be the public HTTPS URL of your VM.
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + endpoint;
  
  const options = {
    'method': method,
    'contentType': 'application/json',
    'payload': payloadString,
    'headers': {
      'X-Nexus-Signature': signature
    },
    'muteHttpExceptions': true // Allow us to handle 401s gracefully
  };
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(responseText);
    } else {
      throw new Error("VM Error (" + responseCode + "): " + responseText);
    }
  } catch (error) {
    Logger.log("Failed to contact Nexus VM: " + error.message);
    throw new Error("Communication with Nexus VM failed. Ensure the VM is running and accessible.");
  }
}

/**
 * Triggers a comprehensive diagnostic ping to the Python VM.
 * 
 * WARNING: This function must ONLY be called asynchronously from the client-side UI
 * via `google.script.run.withSuccessHandler().runSystemDiagnostics()`.
 * 
 * @returns {Object} The diagnostic report JSON object from the VM.
 */
function runSystemDiagnostics() {
  const payload = {
    action: "ping_diagnostics"
  };
  
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
 * Runs a sandbox prompt against an artifact's raw text.
 * 
 * @param {Object} payload - The object containing artifact_id and prompt_string.
 * @returns {Object} The JSON response from the VM.
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
 * Queues items for the materialization pipeline.
 * @param {Object} payload - The object containing artifact_ids.
 * @returns {Object} The JSON response.
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
 * Bulk updates multiple artifacts using continuation tokens for timeout protection.
 * 
 * @param {Object} payload - The object containing artifact_ids and metadata.
 * @returns {Object} The JSON response from the VM.
 */
function bulkUpdateArtifacts(payload) {
  // Timeout protection: if payload specifies a continuation token, handle batching.
  const MAX_BATCH_SIZE = 50;
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
 * Executes an AST search via the backend API.
 * @param {string} query - The AST search string
 * @returns {Object} The JSON response.
 */
function searchArtifacts(query) {
  try {
    const payload = {}; // Payload just for signature timestamp
    const result = sendToNexusVM("/api/artifacts/search?q=" + encodeURIComponent(query) + "&limit=50&offset=0", payload, 'get');
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Runs the AI RAG query.
 * 
 * @param {Object} payload - The object containing the question.
 * @returns {Object} The JSON response from the VM.
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
 * Fetches user preferences for boot routing.
 * @returns {Object} The JSON response containing settings.
 */
function getUserPreferences() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/settings/pipeline";
  
  const options = {
    'method': 'get',
    'muteHttpExceptions': true
  };
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode < 300) {
      const data = JSON.parse(response.getContentText());
      return { success: true, data: data.settings };
    } else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Fetches Heatmap data.
 */
function getHeatmapData() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/analytics/heatmap";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Fetches Threads Sankey data.
 */
function getThreadsData() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/analytics/threads";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Fetches ROI Dashboard data.
 */
function getROIDashboard() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/analytics/roi-dashboard";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode < 300) {
      return { success: true, data: JSON.parse(response.getContentText()) };
    } else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Pings Health API.
 */
function pingHealthAPI() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/health";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode < 300) {
      return { status: "success", data: JSON.parse(response.getContentText()) };
    } else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Update Safe Mode.
 */
function updateSafeMode(payload) {
  try {
    const result = sendToNexusVM("/api/settings/pipeline", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Retention API Wrappers
function getRetentionRules() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/retention/rules";
  
  const options = { 'method': 'get', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    if (response.getResponseCode() >= 200 && response.getResponseCode() < 300) {
      return JSON.parse(response.getContentText());
    } else {
      throw new Error("VM Error");
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

function addRetentionRule(payload) {
  try {
    return sendToNexusVM("/api/retention/rules", payload);
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function deleteRetentionRule(payload) {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/retention/rules/" + payload.rule_id;
  
  const options = { 'method': 'delete', 'muteHttpExceptions': true };
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    if (response.getResponseCode() >= 200 && response.getResponseCode() < 300) {
      return JSON.parse(response.getContentText());
    } else {
      throw new Error("VM Error");
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

function triggerRetentionSweep() {
  try {
    return sendToNexusVM("/api/retention/sweep", {});
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Fetches pipeline settings from the VM.
 * @returns {Object} The JSON response containing settings.
 */
function getPipelineSettings() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/settings/pipeline";
  
  const options = {
    'method': 'get',
    'muteHttpExceptions': true
  };
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

/**
 * Saves pipeline settings to the VM.
 * @param {Object} payload - The settings payload.
 * @returns {Object} The JSON response.
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
 * Queues a historical import based on a Gmail search string.
 * @param {string} query - The search query.
 * @returns {Object} The JSON response.
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
 * Updates custom extraction rules for a specific entity.
 * @param {string} entityType - "correspondents" or "purposes"
 * @param {string} id - The entity ID
 * @param {string} rules - The custom extraction rules
 * @param {boolean} autoArchive - Auto-archive setting (only for purposes)
 * @returns {Object} The JSON response.
 */
function updateEntityRules(entityType, id, rules, autoArchive = false) {
  try {
    const payload = { custom_extraction_rules: rules };
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
 * Submits a zero-shot rule creation request to the VM.
 * @param {Object} payload - The object containing artifact_ids and instruction.
 * @returns {Object} The JSON response.
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
 * Fetches Quota Governor stats from the VM.
 * @returns {Object} The JSON response containing quota stats.
 */
function getQuotaGovernor() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const vmUrl = scriptProperties.getProperty('NEXUS_VM_URL') || "http://localhost:8000"; 
  const targetUrl = vmUrl + "/api/health/quota";
  
  const options = {
    'method': 'get',
    'muteHttpExceptions': true
  };
  
  try {
    const response = UrlFetchApp.fetch(targetUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode < 300) {
      return JSON.parse(response.getContentText());
    } else {
      throw new Error("VM Error (" + responseCode + "): " + response.getContentText());
    }
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}
