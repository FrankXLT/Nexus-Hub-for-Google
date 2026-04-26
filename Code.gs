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
function sendToNexusVM(endpoint, payload) {
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
    'method': 'post',
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
 * Bulk updates multiple artifacts.
 * 
 * @param {Object} payload - The object containing artifact_ids and metadata.
 * @returns {Object} The JSON response from the VM.
 */
function bulkUpdateArtifacts(payload) {
  try {
    const result = sendToNexusVM("/api/bulk-update", payload);
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

