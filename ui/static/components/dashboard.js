/**
 * Dashboard Component
 * Handles dashboard data loading and display
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    getElement
} from '../utils/helpers.js';

class DashboardManager {
    constructor() {
        this.apiBase = API_CONFIG.BASE_URL;
    }

    /**
     * Load and display dashboard data
     */
    async loadDashboard() {
        const statsGrid = getElement('dashboardStats');
        const recentRunsDiv = getElement('recentRuns');

        if (statsGrid) {
            statsGrid.innerHTML = '<p style="color: #9ca3af;">Loading dashboard data...</p>';
        }

        try {
            const [statusRes, runsRes] = await Promise.all([
                fetch(`${this.apiBase}/status`),
                fetch(`${this.apiBase}/runs`)
            ]);

            if (!statusRes.ok || !runsRes.ok) {
                throw new Error(`API request failed: ${statusRes.status} / ${runsRes.status}`);
            }

            const status = await statusRes.json();
            const runs = await runsRes.json();

            if (statsGrid) {
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <h3>${runs.runs ? runs.runs.length : 0}</h3>
                        <p>Total Runs</p>
                    </div>
                    <div class="stat-card">
                        <h3>${status.running_processes ? status.running_processes.length : 0}</h3>
                        <p>Active Processes</p>
                    </div>
                    <div class="stat-card">
                        <h3>✓</h3>
                        <p>System Status</p>
                    </div>
                `;
            }

            if (recentRunsDiv) {
                if (runs.runs && runs.runs.length > 0) {
                    recentRunsDiv.innerHTML = '<h3 style="margin-top: 20px;">Recent Runs</h3><table class="table"><thead><tr><th>Run ID</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead><tbody></tbody></table>';
                    const tbody = recentRunsDiv.querySelector('tbody');
                    runs.runs.slice(0, 5).forEach(run => {
                        const date = new Date(run.timestamp * 1000).toLocaleString();
                        tbody.innerHTML += `
                            <tr>
                                <td>${run.id}</td>
                                <td><span class="badge badge-${run.has_metrics ? 'success' : 'info'}">${run.has_metrics ? 'Complete' : 'In Progress'}</span></td>
                                <td>${date}</td>
                                <td>
                                    <button class="btn" onclick="deleteReport('${run.id}')" style="background: #f87171; color: #ffffff;" title="Delete Report">🗑️ Delete</button>
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    recentRunsDiv.innerHTML = '<p style="color: #9ca3af;">No runs yet. Start by creating test audio files.</p>';
                }
            }
        } catch (error) {
            console.error('Dashboard load failed:', error);
            if (statsGrid) {
                statsGrid.innerHTML = `<p style="color: #f87171;">Error loading dashboard: ${error.message}</p>`;
            }
            if (recentRunsDiv) {
                recentRunsDiv.innerHTML = `<p style="color: #f87171;">Error loading recent runs: ${error.message}</p>`;
            }
        }
    }
}

export const dashboardManager = new DashboardManager();
export const loadDashboard = () => dashboardManager.loadDashboard();