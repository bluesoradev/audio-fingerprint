/**
 * Status Component
 * Handles server status checking and health monitoring
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    getElement
} from '../utils/helpers.js';

class StatusChecker {
    constructor() {
        this.apiBase = API_CONFIG.BASE_URL;
        this.timeout = API_CONFIG.TIMEOUT;
    }

    /**
     * Check server status with timeout and error handling
     */
    async checkStatus() {
        const statusDot = getElement('statusDot');
        const statusText = getElement('statusText');
        const sidebarStatusText = getElement('sidebarStatusText');
        const currentProcess = getElement('currentProcess');

        console.log('Checking server status at:', this.apiBase);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log('Status check timeout - server not responding');
                controller.abort();
            }, this.timeout);

            const response = await fetch(`${this.apiBase}/status`, {
                signal: controller.signal,
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                cache: 'no-cache'
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }

            const status = await response.json();

            if (status.running_processes && status.running_processes.length > 0) {
                if (statusDot) statusDot.className = 'status-dot warning';
                if (statusText) statusText.textContent = `${status.running_processes.length} process(es) running`;
                if (sidebarStatusText) {
                    sidebarStatusText.textContent = `${status.running_processes.length} process(es) running`;
                }
                if (currentProcess) currentProcess.textContent = `Running: ${status.running_processes.join(', ')}`;
            } else {
                if (statusDot) statusDot.className = 'status-dot';
                if (statusText) statusText.textContent = 'System Ready';
                if (sidebarStatusText) sidebarStatusText.textContent = 'System Ready';
                if (currentProcess) currentProcess.textContent = '';
            }
        } catch (error) {
            console.error('Status check failed:', error);

            const isNetworkError = error.name === 'TypeError' ||
                error.name === 'NetworkError' ||
                error.name === 'AbortError' ||
                error.message.includes('Failed to fetch') ||
                error.message.includes('NetworkError');

            if (statusDot) statusDot.className = 'status-dot error';
            if (statusText) statusText.textContent = 'Server Offline';
            if (sidebarStatusText) {
                sidebarStatusText.textContent = `Server Offline - Cannot connect to ${this.apiBase}`;
            }
            if (currentProcess) {
                currentProcess.textContent = `Connection Error: ${error.message}`;
            }
        }
    }

    /**
     * Start periodic status checking
     * @param {number} interval - Interval in milliseconds (default: 5000)
     */
    startPeriodicCheck(interval = 5000) {
        this.checkStatus();
        setInterval(() => this.checkStatus(), interval);
    }
}

export const statusChecker = new StatusChecker();
export const checkStatus = () => statusChecker.checkStatus();