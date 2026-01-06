/**
 * Legacy Functions Module
 * Contains original app.js functions that will be gradually migrated to proper modules
 * This module maintains all functionality while allowing gradual refactoring
 */

// Import dependencies
import {
    API_CONFIG
} from '../config/api.js';
import {
    formatBytes,
    formatTime,
    formatTimeWithMs,
    formatFileSize,
    getElement,
    querySelector,
    querySelectorAll
} from '../utils/helpers.js';
import {
    showError,
    showCompletionAlert,
    showNotification,
    notificationManager
} from './notifications.js';

// Export API_BASE for backward compatibility
export const API_BASE = API_CONFIG.BASE_URL;

// State management
export let currentProcessId = null;
export let logPollInterval = null;
export let transformChain = [];
export let selectedAudioFile = null;
export let originalAudioPlaying = false;
export let transformedAudioPlaying = false;
export let deliverablesSelectedAudioFile = null;

// Export state setters
export const setCurrentProcessId = (id) => {
    currentProcessId = id;
};
export const setLogPollInterval = (interval) => {
    logPollInterval = interval;
};
export const setTransformChain = (chain) => {
    transformChain = chain;
};
export const setSelectedAudioFile = (file) => {
    selectedAudioFile = file;
};
export const setOriginalAudioPlaying = (playing) => {
    originalAudioPlaying = playing;
};
export const setTransformedAudioPlaying = (playing) => {
    transformedAudioPlaying = playing;
};
export const setDeliverablesSelectedAudioFile = (file) => {
    deliverablesSelectedAudioFile = file;
};

// Re-export utilities
export {
    formatBytes,
    formatTime,
    formatTimeWithMs,
    formatFileSize,
    getElement,
    querySelector,
    querySelectorAll
};
export {
    showError,
    showCompletionAlert,
    showNotification
};

// Note: All other functions from the original app.js will be imported here
// and then re-exported. This allows gradual migration to proper component modules.