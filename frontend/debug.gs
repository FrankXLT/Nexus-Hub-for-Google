/**
 * Module: debug.gs
 * Purpose: Centralized configuration and logging for the Nexus frontend.
 */

const NEXUS_CONFIG = {
  LOG_LEVEL: 'NORMAL', // 'NORMAL', 'VERBOSE', 'DEBUG'
  UI_FLAGS: {
    showRawPayloads: false,
    enableTraceRouting: false,
    mockDataMode: false
  }
};

/**
 * Unified server-side logger that respects the configured LOG_LEVEL.
 * @param {string} level - Log level ('INFO', 'WARN', 'ERROR', 'DEBUG')
 * @param {string} message - The message to log
 * @param {Object} [data] - Optional data to include
 */
function systemLog(level, message, data = null) {
  if (NEXUS_CONFIG.LOG_LEVEL === 'NORMAL' && (level === 'DEBUG' || level === 'VERBOSE')) return;
  if (NEXUS_CONFIG.LOG_LEVEL === 'VERBOSE' && level === 'DEBUG') return;

  const prefix = `[${level}] ${message}`;
  if (data) {
    if (level === 'ERROR') {
      console.error(prefix, data);
    } else {
      console.log(prefix, data);
    }
  } else {
    if (level === 'ERROR') {
      console.error(prefix);
    } else {
      console.log(prefix);
    }
  }
}
