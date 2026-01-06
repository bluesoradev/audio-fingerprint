/**
 * Process Monitor Component
 * Handles process monitoring, log polling, and status tracking
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
    showCompletionAlert
} from './notifications.js';

class ProcessMonitor {
    constructor() {
        this.apiBase = API_CONFIG.BASE_URL;
        this.currentProcessId = null;
        this.logPollInterval = null;
    }

    /**
     * Start monitoring a process
     * @param {string} commandId - Process command ID
     * @param {string} message - Initial message
     * @param {string} processName - Process name for alerts
     */
    startProcessMonitoring(commandId, message, processName = 'Process') {
        this.currentProcessId = commandId;

        if (typeof window.showSection === 'function') {
            window.showSection('logs', null);
        }

        const logsDiv = getElement('systemLogs');
        if (logsDiv) {
            logsDiv.innerHTML = `<div class="log-line">${message}</div>`;
        }

        if (!window.processNames) {
            window.processNames = {};
        }
        window.processNames[commandId] = processName;

        if (this.logPollInterval) {
            clearInterval(this.logPollInterval);
        }

        this.logPollInterval = setInterval(async () => {
            await this.pollLogs(commandId);
            await this.checkProcessStatus(commandId);
        }, 1000);
    }

    /**
     * Poll logs for a process
     * @param {string} commandId - Process command ID
     */
    async pollLogs(commandId) {
        try {
            const result = await apiClient.get(API_CONFIG.ENDPOINTS.PROCESS.LOGS(commandId));

            if (result.logs && result.logs.length > 0) {
                const logsDiv = getElement('systemLogs');
                result.logs.forEach(log => {
                    const line = document.createElement('div');
                    line.className = `log-line ${log.type}`;
                    line.textContent = log.message;
                    logsDiv ? .appendChild(line);
                });
                if (logsDiv) logsDiv.scrollTop = logsDiv.scrollHeight;
            }
        } catch (error) {
            console.error('Failed to poll logs:', error);
        }
    }

    /**
     * Check process status
     * @param {string} commandId - Process command ID
     */
    async checkProcessStatus(commandId) {
        try {
            const status = await apiClient.get(API_CONFIG.ENDPOINTS.PROCESS.STATUS(commandId));

            if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                if (this.logPollInterval) {
                    clearInterval(this.logPollInterval);
                    this.logPollInterval = null;
                }
                this.currentProcessId = null;

                const processName = window.processNames ? . [commandId] || 'Process';

                if (status.status === 'completed') {
                    showCompletionAlert(processName + ' completed successfully!');
                } else if (status.status === 'failed') {
                    showCompletionAlert(processName + ' failed. Check logs for details.', 'error');
                } else if (status.status === 'cancelled') {
                    showCompletionAlert(processName + ' was cancelled.', 'warning');
                }

                if (window.processNames ? . [commandId]) {
                    delete window.processNames[commandId];
                }

                if (typeof loadDashboard === 'function') loadDashboard();
                if (typeof loadManifests === 'function') loadManifests();
                if (typeof loadRuns === 'function') loadRuns();
                if (typeof loadAudioFiles === 'function') loadAudioFiles();
            } else if (status.status === 'not_found') {
                if (this.logPollInterval) {
                    clearInterval(this.logPollInterval);
                    this.logPollInterval = null;
                }
                this.currentProcessId = null;
            }
        } catch (error) {
            console.error('Failed to check status:', error);
        }
    }

    /**
     * Get current process ID
     */
    getCurrentProcessId() {
        return this.currentProcessId;
    }
}

export const processMonitor = new ProcessMonitor();
export const startProcessMonitoring = (commandId, message, processName) =>
    processMonitor.startProcessMonitoring(commandId, message, processName);
export const pollLogs = (commandId) => processMonitor.pollLogs(commandId);
export const checkProcessStatus = (commandId) => processMonitor.checkProcessStatus(commandId);