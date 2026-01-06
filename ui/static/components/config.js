/**
 * Configuration Component
 * Handles configuration loading and saving
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    apiClient
} from '../api/client.js';
import {
    getElement
} from '../utils/helpers.js';
import {
    showError
} from './notifications.js';
import {
    safeJsonParse
} from '../utils/helpers.js';

class ConfigManager {
    /**
     * Load test matrix configuration
     */
    async loadTestMatrix() {
        try {
            const config = await apiClient.get(API_CONFIG.ENDPOINTS.CONFIG.TEST_MATRIX);
            const configElement = getElement('testMatrixConfig');
            if (configElement) {
                configElement.value = JSON.stringify(config, null, 2);
            }
        } catch (error) {
            console.error('Failed to load test matrix:', error);
        }
    }

    /**
     * Save test matrix configuration
     */
    async saveTestMatrix() {
        try {
            const configTextEl = getElement('testMatrixConfig');
            const configText = configTextEl && configTextEl.value;
            if (!configText) {
                showError('No configuration to save');
                return;
            }

            const config = safeJsonParse(configText);
            if (!config) {
                showError('Invalid JSON configuration');
                return;
            }

            const result = await apiClient.post(API_CONFIG.ENDPOINTS.CONFIG.TEST_MATRIX, config);

            if (result.status === 'success') {
                if (typeof addSystemLog === 'function') {
                    addSystemLog('Configuration saved successfully', 'success');
                }
            }
        } catch (error) {
            showError('Failed to save configuration: ' + error.message);
        }
    }
}

export const configManager = new ConfigManager();
export const loadTestMatrix = () => configManager.loadTestMatrix();
export const saveTestMatrix = () => configManager.saveTestMatrix();