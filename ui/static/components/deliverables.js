/**
 * Deliverables Component
 * Handles deliverables, reports, and deliverables-specific transformations
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    formatBytes,
    getElement
} from '../utils/helpers.js';
import {
    showError,
    showCompletionAlert,
    addSystemLog
} from './notifications.js';

class DeliverablesManager {
    constructor() {
        this.selectedAudioFile = null;
    }

    async loadDeliverables() {
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/runs`);
            const result = await response.json();

            const deliverablesListDiv = getElement('deliverablesList');

            if (result.runs && result.runs.length > 0) {
                const phase1Runs = [];
                const phase2Runs = [];
                const otherRuns = [];
                const runsToCheck = [];

                result.runs.forEach(run => {
                    const runPath = (run.path || '').toLowerCase();
                    const runId = (run.id || '').toLowerCase();
                    const runPhase = (run.phase || (run.summary && run.summary.phase) || '').toLowerCase();

                    const isPhase1 = runPhase === 'phase1' || runPath.includes('phase1') || runId.includes('phase1') ||
                        runPath.includes('phase_1') || runId.includes('phase_1') || (runId.includes('test_') && runId.includes('phase1'));
                    const isPhase2 = runPhase === 'phase2' || runPath.includes('phase2') || runId.includes('phase2') ||
                        runPath.includes('phase_2') || runId.includes('phase_2') || (runId.includes('test_') && runId.includes('phase2'));

                    if (isPhase1 && !isPhase2) {
                        phase1Runs.push(run);
                    } else if (isPhase2 && !isPhase1) {
                        phase2Runs.push(run);
                    } else if (!runPhase || runPhase === 'unknown') {
                        runsToCheck.push(run);
                    } else {
                        otherRuns.push(run);
                    }
                });

                for (const run of runsToCheck) {
                    try {
                        const detailsResp = await fetch(`${API_CONFIG.BASE_URL}/runs/${run.id}`);
                        if (detailsResp.ok) {
                            const details = await detailsResp.json();
                            const metrics = details.metrics || {};
                            const phase = ((metrics.summary && metrics.summary.phase) || (metrics.test_details && metrics.test_details.phase) || '').toLowerCase();

                            if (phase === 'phase1') {
                                run.phase = 'phase1';
                                phase1Runs.push(run);
                            } else if (phase === 'phase2') {
                                run.phase = 'phase2';
                                phase2Runs.push(run);
                            } else {
                                const runPath = (run.path || '').toLowerCase();
                                if (runPath.includes('phase1') || runPath.includes('phase_1')) {
                                    phase1Runs.push(run);
                                } else if (runPath.includes('phase2') || runPath.includes('phase_2')) {
                                    phase2Runs.push(run);
                                } else {
                                    otherRuns.push(run);
                                }
                            }
                        } else {
                            otherRuns.push(run);
                        }
                    } catch (e) {
                        console.warn(`Failed to check phase for run ${run.id}:`, e);
                        otherRuns.push(run);
                    }
                }

                const sortByTime = (a, b) => (b.timestamp || 0) - (a.timestamp || 0);
                phase1Runs.sort(sortByTime);
                phase2Runs.sort(sortByTime);

                if (deliverablesListDiv) {
                    const latestReports = [];

                    if (phase1Runs.length > 0) {
                        latestReports.push({
                            ...phase1Runs[0],
                            phaseLabel: 'Phase 1',
                            isPhase1: true
                        });
                    }

                    if (phase2Runs.length > 0) {
                        latestReports.push({
                            ...phase2Runs[0],
                            phaseLabel: 'Phase 2',
                            isPhase2: true
                        });
                    }

                    if (latestReports.length > 0) {
                        let html = '';
                        latestReports.forEach(run => {
                            const date = run.timestamp ? new Date(run.timestamp * 1000) : null;
                            const dateStr = date ? date.toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            }) : 'Pending';
                            const phaseLabel = run.phaseLabel || (run.isPhase1 ? 'Phase 1' : (run.isPhase2 ? 'Phase 2' : 'Report'));
                            const phaseColor = run.isPhase1 ? '#427eea' : (run.isPhase2 ? '#10b981' : '#9ca3af');
                            const sizeStr = '1.2 MB';

                            html += `
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 15px; margin-bottom: 12px; background: #2d2d2d; border-radius: 8px; border: 1px solid #3d3d3d; transition: all 0.2s;">
                                    <div style="flex: 1;">
                                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                                            <span style="color: ${phaseColor}; font-size: 12px; font-weight: 600; padding: 4px 8px; background: ${phaseColor}20; border-radius: 4px;">${phaseLabel}</span>
                                            <strong style="color: #ffffff; font-size: 14px;">${run.id}</strong>
                                        </div>
                                        <p style="color: #9ca3af; font-size: 11px; margin: 0;">${dateStr} | ${sizeStr}</p>
                                    </div>
                                    <div style="display: flex; gap: 8px; align-items: center;">
                                        <button class="btn" onclick="viewRunDetails('${run.id}')" style="font-size: 11px; padding: 6px 12px; background: #3d3d3d; border-radius: 4px; border: none; color: #ffffff; cursor: pointer;">Details</button>
                                    </div>
                                </div>
                            `;
                        });
                        deliverablesListDiv.innerHTML = html;
                    } else {
                        deliverablesListDiv.innerHTML = '<p style="color: #9ca3af; font-size: 12px; padding: 20px; text-align: center; background: #2d2d2d; border-radius: 8px;">No Phase 1 or Phase 2 reports found. Generate reports using the "Full Test Suites" section above.</p>';
                    }
                }
            } else {
                if (deliverablesListDiv) {
                    deliverablesListDiv.innerHTML = '<p style="color: #9ca3af; font-size: 12px; padding: 20px; text-align: center; background: #2d2d2d; border-radius: 8px;">No reports found.</p>';
                }
            }
        } catch (error) {
            console.error('Failed to load deliverables:', error);
            const deliverablesListDiv = getElement('deliverablesList');
            if (deliverablesListDiv) {
                deliverablesListDiv.innerHTML = `<p style="color: #f87171; font-size: 12px; padding: 20px; text-align: center; background: #2d2d2d; border-radius: 8px;">Error loading reports: ${error.message}</p>`;
            }
        }
    }

    viewReport(reportPath, runId) {
        const url = `${API_CONFIG.BASE_URL}/files/report?path=${encodeURIComponent(reportPath)}`;
        window.open(url, '_blank');
    }

    async downloadReportZip(runId) {
        try {
            showCompletionAlert(`Preparing download for ${runId}...`, 'info');

            const downloadUrl = `${API_CONFIG.BASE_URL}/runs/${runId}/download`;

            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `${runId}_report.zip`;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();

            setTimeout(() => {
                document.body.removeChild(a);
                showCompletionAlert(`Download started: ${runId}_report.zip`);
                addSystemLog(`Download started: ${runId}_report.zip`, 'success');
            }, 500);

        } catch (error) {
            console.error('Failed to download report:', error);
            showError('Failed to download report: ' + error.message);
            addSystemLog(`Failed to download report ${runId}: ${error.message}`, 'error');
        }
    }

    async viewRunDetails(runId) {
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/runs/${runId}`);
            const result = await response.json();

            const reportViewerDiv = getElement('reportViewer');

            if (!reportViewerDiv) {
                console.error('reportViewer element not found');
                return;
            }

            const hasMetrics = !!result.metrics;
            const metrics = result.metrics || {};
            const testDetails = metrics.test_details || {};
            const overall = metrics.overall || {};
            const recall = overall.recall || {};
            const rank = overall.rank || {};
            const similarity = overall.similarity || {};
            const passFail = metrics.pass_fail || {};
            const phase = testDetails.phase || (metrics.summary && metrics.summary.phase) || 'unknown';

            const matched = testDetails.matched !== undefined ? testDetails.matched : (passFail.passed > 0);
            const statusColor = !hasMetrics ? '#f59e0b' : (matched ? '#10b981' : '#f87171');
            const statusText = !hasMetrics ? '⏳ PENDING' : (matched ? '' : '');
            const phaseColor = phase === 'phase1' ? '#427eea' : phase === 'phase2' ? '#10b981' : '#9ca3af';

            let html = `
                <div style="background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%); padding: 25px; border-radius: 12px; border: 2px solid ${phaseColor};">
                    <div style="text-align: center; margin-bottom: 25px;">
                        <h3 style="color: ${phaseColor}; margin: 0 0 10px 0; font-size: 1.5em;">${phase.toUpperCase()} Report</h3>
                        <h2 style="color: ${statusColor}; margin: 0; font-size: 2.5em; font-weight: bold;">${statusText}</h2>
                    </div>
            `;

            if (!hasMetrics) {
                html += `
                    <p style="color:#9ca3af; text-align:center; margin-bottom:10px;">Report metrics not available yet. If a suite was just launched, it may still be running or may have failed.</p>
                    <p style="color:#9ca3af; text-align:center; margin-bottom:20px;">Refresh after the suite completes. If it stays pending, check server logs.</p>
                </div>`;
                reportViewerDiv.innerHTML = html;
                return;
            }

            html += `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px;">
                        <div style="background: #2d2d2d; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #427eea;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Recall@1</div>
                            <div style="color: #ffffff; font-size: 32px; font-weight: bold;">${((recall.recall_at_1 || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div style="background: #2d2d2d; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #10b981;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Recall@5</div>
                            <div style="color: #ffffff; font-size: 32px; font-weight: bold;">${((recall.recall_at_5 || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div style="background: #2d2d2d; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #f59e0b;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Recall@10</div>
                            <div style="color: #ffffff; font-size: 32px; font-weight: bold;">${((recall.recall_at_10 || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div style="background: #2d2d2d; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #8b5cf6;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Similarity</div>
                            <div style="color: ${statusColor}; font-size: 32px; font-weight: bold;">${((similarity.mean_similarity_correct || testDetails.similarity || 0) * 100).toFixed(1)}%</div>
                        </div>
                    </div>
                    
                    ${testDetails.original_file ? `
                    <div style="background: #2d2d2d; padding: 15px; border-radius: 6px; margin-bottom: 10px;">
                        <div style="color: #9ca3af; font-size: 12px; margin-bottom: 5px;">Original File</div>
                        <div style="color: #ffffff; font-size: 14px; word-break: break-all;">${testDetails.original_file}</div>
                    </div>
                    ` : ''}
                    
                    ${testDetails.manipulated_file ? `
                    <div style="background: #2d2d2d; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
                        <div style="color: #9ca3af; font-size: 12px; margin-bottom: 5px;">Transformed File</div>
                        <div style="color: #ffffff; font-size: 14px; word-break: break-all;">${testDetails.manipulated_file}</div>
                    </div>
                    ` : ''}
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 20px;">
                        <div style="background: #2d2d2d; padding: 15px; border-radius: 6px;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 5px;">Mean Rank</div>
                            <div style="color: #ffffff; font-size: 24px; font-weight: bold;">${(rank.mean_rank || testDetails.rank || 0).toFixed(2)}</div>
                        </div>
                        <div style="background: #2d2d2d; padding: 15px; border-radius: 6px;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 5px;">Test Status</div>
                            <div style="color: ${statusColor}; font-size: 24px; font-weight: bold;">${passFail.passed || 1} / ${passFail.total || 1} Passed</div>
                        </div>
                    </div>
                </div>
            `;

            if (result.metrics) {
                const summary = result.metrics.summary || {};
                html += '<div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #3d3d3d;">';
                html += '<h5 style="color: #427eea; margin-bottom: 10px; font-size: 14px;"> Additional Metrics</h5>';
                html += `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">`;
                html += `<div style="padding: 10px; background: #2d2d2d; border-radius: 4px;"><strong style="color: #9ca3af; font-size: 11px;">Total Queries</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 18px;">${summary.total_queries || 'N/A'}</p></div>`;
                html += `<div style="padding: 10px; background: #2d2d2d; border-radius: 4px;"><strong style="color: #9ca3af; font-size: 11px;">Total Transforms</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 18px;">${summary.total_transforms || 'N/A'}</p></div>`;
                html += `</div>`;
                html += '</div>';
            }

            if (result.summary && result.summary.length > 0) {
                html += '<h5 style="color: #427eea; margin-top: 20px; margin-bottom: 10px; font-size: 14px;">📋 Per-Severity Summary</h5>';
                html += '<div style="overflow-x: auto;"><table class="table" style="width: 100%; margin-top: 10px; font-size: 12px;"><thead><tr style="background: #2d2d2d;"><th style="padding: 8px; text-align: left;">Severity</th><th style="padding: 8px; text-align: right;">Count</th><th style="padding: 8px; text-align: right;">Recall@1</th><th style="padding: 8px; text-align: right;">Recall@5</th><th style="padding: 8px; text-align: right;">Recall@10</th></tr></thead><tbody>';
                result.summary.forEach(row => {
                    const severityColor = row.severity === 'mild' ? '#10b981' : row.severity === 'moderate' ? '#f59e0b' : '#f87171';
                    html += `<tr style="border-bottom: 1px solid #3d3d3d;">
                        <td style="padding: 8px;"><span style="color: ${severityColor}; font-weight: 500;">${row.severity || 'N/A'}</span></td>
                        <td style="padding: 8px; text-align: right; color: #ffffff;">${row.count || 0}</td>
                        <td style="padding: 8px; text-align: right; color: #ffffff;">${((row.recall_at_1 || 0) * 100).toFixed(1)}%</td>
                        <td style="padding: 8px; text-align: right; color: #ffffff;">${((row.recall_at_5 || 0) * 100).toFixed(1)}%</td>
                        <td style="padding: 8px; text-align: right; color: #ffffff;">${((row.recall_at_10 || 0) * 100).toFixed(1)}%</td>
                    </tr>`;
                });
                html += '</tbody></table></div>';
            }

            html += `
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #3d3d3d;">
                    <h5 style="color: #427eea; margin-bottom: 20px; font-size: 16px; font-weight: 600;">📊 Visualizations</h5>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                        <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                            <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Recall@K by Transform Severity</h6>
                            <div id="plot-recall-severity-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                                <img src="${API_CONFIG.BASE_URL}/files/plots/recall_by_severity.png?run_id=${runId}" 
                                     alt="Recall by Severity" 
                                     style="width: 100%; height: auto; border-radius: 4px; max-width: 100%; object-fit: contain;"
                                     onerror="this.style.display='none';">
                            </div>
                        </div>
                        <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                            <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Similarity Score by Severity</h6>
                            <div id="plot-similarity-severity-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                                <img src="${API_CONFIG.BASE_URL}/files/plots/similarity_by_severity.png?run_id=${runId}" 
                                     alt="Similarity by Severity" 
                                     style="width: 100%; height: auto; border-radius: 4px; max-width: 100%; object-fit: contain;"
                                     onerror="this.style.display='none';">
                            </div>
                        </div>
                        <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                            <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Recall@K by Transform Type</h6>
                            <div id="plot-recall-transform-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                                <img src="${API_CONFIG.BASE_URL}/files/plots/recall_by_transform.png?run_id=${runId}" 
                                     alt="Recall by Transform Type" 
                                     style="width: 100%; height: auto; border-radius: 4px; max-width: 100%; object-fit: contain;"
                                     onerror="this.style.display='none';">
                            </div>
                        </div>
                        <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                            <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Latency by Transform Type</h6>
                            <div id="plot-latency-transform-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                                <img src="${API_CONFIG.BASE_URL}/files/plots/latency_by_transform.png?run_id=${runId}" 
                                     alt="Latency by Transform Type" 
                                     style="width: 100%; height: auto; border-radius: 4px; max-width: 100%; object-fit: contain;"
                                     onerror="this.style.display='none';">
                            </div>
                        </div>
                    </div>
                </div>
            `;

            if (result.summary && result.summary.length > 0) {
                html += `
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #3d3d3d;">
                    <h5 style="color: #427eea; margin-bottom: 15px; font-size: 16px; font-weight: 600;">📋 Detailed Test Results</h5>
                    <div style="overflow-x: auto; background: #2d2d2d; border-radius: 8px; padding: 15px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                            <thead>
                                <tr style="background: #1e1e1e; border-bottom: 2px solid #3d3d3d;">
                                    <th style="padding: 10px; text-align: left; color: #ffffff; font-weight: 600;">severity</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">count</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">recall_at_1</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">recall_at_5</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">recall_at_10</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">mean_rank</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">mean_similarity</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">mean_latency_ms</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                result.summary.forEach(row => {
                    const severityColor = row.severity === 'mild' ? '#10b981' : row.severity === 'moderate' ? '#f59e0b' : '#f87171';
                    html += `
                                <tr style="border-bottom: 1px solid #3d3d3d;">
                                    <td style="padding: 10px; color: ${severityColor}; font-weight: 500;">${row.severity || 'N/A'}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${row.count || 0}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(row.recall_at_1 || 0).toFixed(6)}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(row.recall_at_5 || 0).toFixed(6)}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(row.recall_at_10 || 0).toFixed(6)}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(row.mean_rank || 0).toFixed(1)}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(row.mean_similarity || 0).toFixed(6)}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(row.mean_latency_ms || 0).toFixed(6)}</td>
                                </tr>
                    `;
                });
                html += `
                            </tbody>
                        </table>
                    </div>
                </div>
                `;
            }

            if (result.metrics && result.metrics.pass_fail && result.metrics.pass_fail.overall && result.metrics.pass_fail.overall.latency) {
                const latencyData = result.metrics.pass_fail.overall.latency;
                const meanLatency = latencyData.mean_ms || {};
                const p95Latency = latencyData.p95_ms || {};

                html += `
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #3d3d3d;">
                    <h5 style="color: #427eea; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Latency Metrics</h5>
                    <div style="overflow-x: auto; background: #2d2d2d; border-radius: 8px; padding: 15px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                            <thead>
                                <tr style="background: #1e1e1e; border-bottom: 2px solid #3d3d3d;">
                                    <th style="padding: 10px; text-align: left; color: #ffffff; font-weight: 600;">Metric</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Actual</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Target</th>
                                    <th style="padding: 10px; text-align: center; color: #ffffff; font-weight: 600;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr style="border-bottom: 1px solid #3d3d3d;">
                                    <td style="padding: 10px; color: #ffffff; font-weight: 500;">Mean Latency</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(meanLatency.actual || 0).toFixed(1)}ms</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(meanLatency.threshold || 1000.0).toFixed(1)}ms</td>
                                    <td style="padding: 10px; text-align: center; color: ${meanLatency.passed ? '#10b981' : '#f87171'}; font-weight: 600;">${meanLatency.passed ? '✓' : '✗'}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #3d3d3d;">
                                    <td style="padding: 10px; color: #ffffff; font-weight: 500;">P95 Latency</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(p95Latency.actual || 0).toFixed(1)}ms</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${(p95Latency.threshold || 2000.0).toFixed(1)}ms</td>
                                    <td style="padding: 10px; text-align: center; color: ${p95Latency.passed ? '#10b981' : '#f87171'}; font-weight: 600;">${p95Latency.passed ? '✓' : '✗'}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                `;
            }

            if (result.metrics && result.metrics.per_transform) {
                const perTransform = result.metrics.per_transform;
                html += `
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #3d3d3d;">
                    <h5 style="color: #427eea; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Per-Transform Analysis</h5>
                    <div style="overflow-x: auto; background: #2d2d2d; border-radius: 8px; padding: 15px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                            <thead>
                                <tr style="background: #1e1e1e; border-bottom: 2px solid #3d3d3d;">
                                    <th style="padding: 10px; text-align: left; color: #ffffff; font-weight: 600;">Transform</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Total Queries</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Recall@1</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Recall@5</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Recall@10</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Similarity</th>
                                    <th style="padding: 10px; text-align: right; color: #ffffff; font-weight: 600;">Latency</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                Object.keys(perTransform).forEach(transformType => {
                    const data = perTransform[transformType];
                    const recall = data.recall || {};
                    const similarity = data.similarity || {};
                    const latency = data.latency || {};
                    const count = data.count || 0;
                    const recall1 = (recall.recall_at_1 || 0).toFixed(3);
                    const recall5 = (recall.recall_at_5 || 0).toFixed(3);
                    const recall10 = (recall.recall_at_10 || 0).toFixed(3);
                    const meanSimilarity = (similarity.mean_similarity || similarity.mean_similarity_correct || 0).toFixed(3);
                    const meanLatency = (latency.mean_latency_ms || 0).toFixed(1);

                    html += `
                                <tr style="border-bottom: 1px solid #3d3d3d;">
                                    <td style="padding: 10px; color: #ffffff; font-weight: 500;">${transformType}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${count}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${recall1}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${recall5}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${recall10}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${meanSimilarity}</td>
                                    <td style="padding: 10px; text-align: right; color: #ffffff;">${meanLatency}ms</td>
                                </tr>
                    `;
                });
                html += `
                            </tbody>
                        </table>
                    </div>
                </div>
                `;
            }

            if (result.metrics && result.metrics.overall) {
                html += `
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #3d3d3d;">
                    <h5 style="color: #427eea; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Overall Metrics</h5>
                    <div style="background: #2d2d2d; border-radius: 8px; padding: 15px; overflow-x: auto;">
                        <pre style="color: #ffffff; font-family: 'Courier New', monospace; font-size: 11px; margin: 0; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(result.metrics.overall, null, 2)}</pre>
                    </div>
                </div>
                `;
            }

            html += '</div>';
            reportViewerDiv.innerHTML = html;
        } catch (error) {
            console.error('Failed to load run details:', error);
            const reportViewerDiv = getElement('reportViewer');
            if (reportViewerDiv) {
                reportViewerDiv.innerHTML = `
                    <div style="padding: 15px; background: #3a1e1e; border-radius: 6px; border: 1px solid #f87171;">
                        <p style="color: #f87171; margin: 0;">Error loading details: ${error.message}</p>
                    </div>
                `;
            }
        }
    }

    async deleteReport(runId) {
        if (!confirm(`Are you sure you want to delete report "${runId}"?\n\nThis action cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/runs/${runId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.status === 'success') {
                    addSystemLog(`✅ Report "${runId}" deleted successfully`, 'success');
                } else {
                    throw new Error(result.message || 'Failed to delete report');
                }
            } else if (response.status === 404) {
                addSystemLog(`⚠️ Report "${runId}" already removed`, 'info');
            } else {
                let msg = `HTTP ${response.status}`;
                try {
                    const errJson = await response.json();
                    msg = errJson.message || msg;
                } catch {
                    const errText = await response.text();
                    msg = `${msg}: ${errText.substring(0, 200)}`;
                }
                throw new Error(msg);
            }

            setTimeout(() => {
                this.loadDeliverables();
                if (window.loadDashboard) window.loadDashboard();
            }, 300);
        } catch (error) {
            console.error('Failed to delete report:', error);
            showError('Failed to delete report: ' + error.message);
            addSystemLog(`❌ Failed to delete report "${runId}": ${error.message}`, 'error');
        }
    }

    async loadDeliverablesAudioFiles() {
        try {
            const select = getElement('deliverablesAudioSelect');
            if (!select) return;

            const deliverablesEmbeddedSampleSelect = getElement('deliverablesEmbeddedSampleFile');
            const deliverablesEmbeddedBackgroundSelect = getElement('deliverablesEmbeddedBackgroundFile');
            const deliverablesSongASelect = getElement('deliverablesSongAFile');
            const deliverablesSongBBaseSelect = getElement('deliverablesSongBBaseFile');

            select.innerHTML = '<option value="">-- Select Audio File --</option>';

            if (deliverablesEmbeddedSampleSelect) {
                deliverablesEmbeddedSampleSelect.innerHTML = '<option value="">-- Select Sample File --</option>';
            }
            if (deliverablesEmbeddedBackgroundSelect) {
                deliverablesEmbeddedBackgroundSelect.innerHTML = '<option value="">-- Use Chain Output --</option>';
            }
            if (deliverablesSongASelect) {
                deliverablesSongASelect.innerHTML = '<option value="">-- Use Original Input --</option>';
            }
            if (deliverablesSongBBaseSelect) {
                deliverablesSongBBaseSelect.innerHTML = '<option value="">-- Generate Synthetic Background --</option>';
            }

            const allFiles = [];

            try {
                const response = await fetch(`${API_CONFIG.BASE_URL}/files/audio?directory=test_audio`);
                const result = await response.json();
                if (result.files && result.files.length > 0) {
                    result.files.forEach(file => {
                        allFiles.push({
                            path: file.path || `data/test_audio/${file.name}`,
                            name: file.name || file,
                            size: file.size || 0
                        });
                    });
                }
            } catch (error) {
                console.error('Failed to load test_audio files:', error);
            }

            try {
                const response2 = await fetch(`${API_CONFIG.BASE_URL}/files/audio?directory=originals`);
                const result2 = await response2.json();
                if (result2.files && result2.files.length > 0) {
                    result2.files.forEach(file => {
                        allFiles.push({
                            path: file.path || `data/originals/${file.name}`,
                            name: file.name || file,
                            size: file.size || 0
                        });
                    });
                }
            } catch (error) {
                // Ignore errors loading originals
            }

            allFiles.forEach(file => {
                const option = document.createElement('option');
                option.value = file.path;
                option.textContent = `${file.name} (${formatBytes(file.size)})`;
                select.appendChild(option);

                if (deliverablesEmbeddedSampleSelect) {
                    const sampleOption = option.cloneNode(true);
                    deliverablesEmbeddedSampleSelect.appendChild(sampleOption);
                }
                if (deliverablesEmbeddedBackgroundSelect) {
                    const bgOption = option.cloneNode(true);
                    deliverablesEmbeddedBackgroundSelect.appendChild(bgOption);
                }
                if (deliverablesSongASelect) {
                    const songAOption = option.cloneNode(true);
                    deliverablesSongASelect.appendChild(songAOption);
                }
                if (deliverablesSongBBaseSelect) {
                    const songBOption = option.cloneNode(true);
                    deliverablesSongBBaseSelect.appendChild(songBOption);
                }
            });
        } catch (error) {
            console.error('Failed to load audio files:', error);
        }
    }

    loadDeliverablesAudioInfo(filePath) {
        const infoDiv = getElement('deliverablesAudioInfo');
        const fileNameSpan = getElement('deliverablesSelectedFileName');
        const filePathSpan = getElement('deliverablesSelectedFilePath');

        if (!filePath) {
            this.selectedAudioFile = null;
            if (fileNameSpan) fileNameSpan.textContent = '';
            if (filePathSpan) filePathSpan.textContent = '';
            if (infoDiv) infoDiv.style.display = 'block';
            this.updateDeliverablesTransformState();
            return;
        }

        this.selectedAudioFile = filePath;

        if (infoDiv && fileNameSpan && filePathSpan) {
            const fileName = filePath.split('/').pop();
            fileNameSpan.textContent = fileName;
            filePathSpan.textContent = filePath;
            infoDiv.style.display = 'block';
        }

        this.updateDeliverablesTransformState();
    }

    handleDeliverablesDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        const uploadArea = getElement('deliverablesUploadArea');
        if (uploadArea) uploadArea.classList.remove('dragover');

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.handleDeliverablesFileUpload(files[0]);
        }
    }

    handleDeliverablesFileSelect(event) {
        const files = event.target.files;
        if (files.length > 0) {
            this.handleDeliverablesFileUpload(files[0]);
        }
    }

    async handleDeliverablesFileUpload(file) {
        if (!file.type.startsWith('audio/')) {
            showError('Please select an audio file');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('directory', 'test_audio');

            const response = await fetch(`${API_CONFIG.BASE_URL}/upload/audio`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(`File uploaded: ${result.path}`);
                addSystemLog(`Audio file uploaded: ${result.path}`, 'success');

                await this.loadDeliverablesAudioFiles();
                const select = getElement('deliverablesAudioSelect');
                if (select) {
                    const relativePath = result.path.startsWith('data/') ? result.path : `data/test_audio/${result.path.split('/').pop()}`;
                    select.value = relativePath;
                    this.loadDeliverablesAudioInfo(relativePath);
                }
            } else {
                showError(result.message || 'Upload failed');
            }
        } catch (error) {
            showError('Failed to upload file: ' + error.message);
        }
    }

    updateDeliverablesSpeedValue(value) {
        const display = getElement('deliverablesSpeedValue');
        if (display) {
            display.textContent = (value / 100).toFixed(1) + 'x';
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesPitchValue(value) {
        const display = getElement('deliverablesPitchValue');
        if (display) {
            display.textContent = parseFloat(value).toFixed(1);
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesReverbValue(value) {
        const display = getElement('deliverablesReverbValue');
        if (display) {
            display.textContent = parseFloat(value).toFixed(1) + 'ms';
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesNoiseValue(value) {
        const display = getElement('deliverablesNoiseValue');
        if (display) {
            display.textContent = value + '%';
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesEQValue(value) {
        const display = getElement('deliverablesEQValue');
        if (display) {
            display.textContent = parseFloat(value).toFixed(1) + 'dB';
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesOverlayGainValue(value) {
        const display = getElement('deliverablesOverlayGainValue');
        if (display) {
            display.textContent = parseFloat(value).toFixed(1) + 'dB';
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesSliderDisplay(type, value) {
        const displayMap = {
            'highpass': {
                id: 'deliverablesHighpassDisplay',
                suffix: 'Hz',
                decimals: 1
            },
            'lowpass': {
                id: 'deliverablesLowpassDisplay',
                suffix: 'Hz',
                decimals: 1
            },
            'embeddedVolumeDb': {
                id: 'deliverablesEmbeddedVolumeDbDisplay',
                suffix: 'dB',
                decimals: 1
            },
            'songAMixVolumeDb': {
                id: 'deliverablesSongAMixVolumeDbDisplay',
                suffix: 'dB',
                decimals: 1
            },
            'boostHighs': {
                id: 'deliverablesBoostHighsDisplay',
                suffix: 'dB',
                decimals: 1
            },
            'boostLows': {
                id: 'deliverablesBoostLowsDisplay',
                suffix: 'dB',
                decimals: 1
            },
            'limiting': {
                id: 'deliverablesLimitingDisplay',
                suffix: 'dB',
                decimals: 1
            },
            'noiseSNR': {
                id: 'deliverablesNoiseSNRDisplay',
                suffix: 'dB',
                decimals: 1
            },
            'telephoneLow': {
                id: 'deliverablesTelephoneLowDisplay',
                suffix: 'Hz',
                decimals: 1
            },
            'telephoneHigh': {
                id: 'deliverablesTelephoneHighDisplay',
                suffix: 'Hz',
                decimals: 1
            }
        };
        const mapping = displayMap[type];
        if (mapping) {
            const display = getElement(mapping.id);
            if (display) {
                const numValue = parseFloat(value);
                const decimals = mapping.decimals || 0;
                display.textContent = numValue.toFixed(decimals) + mapping.suffix;
            }
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesBitrateEnabled() {
        const codecSelect = getElement('deliverablesCodecSelect');
        const bitrateSelect = getElement('deliverablesBitrateSelect');
        if (codecSelect && bitrateSelect) {
            bitrateSelect.disabled = codecSelect.value === 'None';
        }
        this.updateDeliverablesTransformState();
    }

    updateDeliverablesCropDuration() {
        const cropTypeSelect = getElement('deliverablesCropTypeSelect');
        const cropDurationGroup = getElement('deliverablesCropDurationGroup');
        if (cropTypeSelect && cropDurationGroup) {
            const cropType = cropTypeSelect.value;
            cropDurationGroup.style.display = (cropType === 'middle' || cropType === 'end') ? 'block' : 'none';
        }
        this.updateDeliverablesTransformState();
    }

    toggleDeliverablesEmbeddedTransformParams() {
        const applyTransform = getElement('deliverablesEmbeddedApplyTransform');
        const paramsGroup = getElement('deliverablesEmbeddedTransformParamsGroup');
        if (applyTransform && paramsGroup) {
            paramsGroup.style.display = (applyTransform.value !== 'None') ? 'block' : 'none';
        }
    }

    toggleDeliverablesSongATransformParams() {
        const applyTransform = getElement('deliverablesSongAApplyTransform');
        const paramsGroup = getElement('deliverablesSongATransformParamsGroup');
        if (applyTransform && paramsGroup) {
            paramsGroup.style.display = (applyTransform.value !== 'None') ? 'block' : 'none';
        }
    }

    updateDeliverablesTransformState() {
        // Count enabled transformations - function kept for compatibility
        const enabledTransforms = [];
        const speedEnabled = getElement('deliverablesSpeedEnabled');
        if (speedEnabled && speedEnabled.checked) enabledTransforms.push('Speed');
        const pitchEnabled = getElement('deliverablesPitchEnabled');
        if (pitchEnabled && pitchEnabled.checked) enabledTransforms.push('Pitch');
        const reverbEnabled = getElement('deliverablesReverbEnabled');
        if (reverbEnabled && reverbEnabled.checked) enabledTransforms.push('Reverb');
        const noiseEnabled = getElement('deliverablesNoiseEnabled');
        if (noiseEnabled && noiseEnabled.checked) enabledTransforms.push('Noise Reduction');
        const eqEnabled = getElement('deliverablesEQEnabled');
        if (eqEnabled && eqEnabled.checked) enabledTransforms.push('EQ');
        const compressionEnabled = getElement('deliverablesCompressionEnabled');
        const codecSelect = getElement('deliverablesCodecSelect');
        if (compressionEnabled && compressionEnabled.checked &&
            codecSelect && codecSelect.value !== 'None') enabledTransforms.push('Compression');
        const overlayEnabled = getElement('deliverablesOverlayEnabled');
        if (overlayEnabled && overlayEnabled.checked) enabledTransforms.push('Overlay');
        const highpassEnabled = getElement('deliverablesHighpassEnabled');
        if (highpassEnabled && highpassEnabled.checked) enabledTransforms.push('High-Pass');
        const lowpassEnabled = getElement('deliverablesLowpassEnabled');
        if (lowpassEnabled && lowpassEnabled.checked) enabledTransforms.push('Low-Pass');
        const boostHighsEnabled = getElement('deliverablesBoostHighsEnabled');
        if (boostHighsEnabled && boostHighsEnabled.checked) enabledTransforms.push('Boost Highs');
        const boostLowsEnabled = getElement('deliverablesBoostLowsEnabled');
        if (boostLowsEnabled && boostLowsEnabled.checked) enabledTransforms.push('Boost Lows');
        const telephoneEnabled = getElement('deliverablesTelephoneEnabled');
        if (telephoneEnabled && telephoneEnabled.checked) enabledTransforms.push('Telephone');
        const limitingEnabled = getElement('deliverablesLimitingEnabled');
        if (limitingEnabled && limitingEnabled.checked) enabledTransforms.push('Limiting');
        const multibandEnabled = getElement('deliverablesMultibandEnabled');
        if (multibandEnabled && multibandEnabled.checked) enabledTransforms.push('Multiband');
        const addNoiseEnabled = getElement('deliverablesAddNoiseEnabled');
        if (addNoiseEnabled && addNoiseEnabled.checked) enabledTransforms.push('Add Noise');
        const cropEnabled = getElement('deliverablesCropEnabled');
        if (cropEnabled && cropEnabled.checked) enabledTransforms.push('Crop');
        const embeddedSampleEnabled = getElement('deliverablesEmbeddedSampleEnabled');
        if (embeddedSampleEnabled && embeddedSampleEnabled.checked) enabledTransforms.push('Embedded Sample');
        const songAInSongBEnabled = getElement('deliverablesSongAInSongBEnabled');
        if (songAInSongBEnabled && songAInSongBEnabled.checked) enabledTransforms.push('Song A in Song B');
    }

    async applyAllDeliverablesTransforms() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const enabledTransforms = [];

        const deliverablesSpeedEnabled = getElement('deliverablesSpeedEnabled');
        if (deliverablesSpeedEnabled && deliverablesSpeedEnabled.checked) {
            const preservePitchEl = getElement('deliverablesPreservePitch');
            enabledTransforms.push({
                type: 'speed',
                speed: parseFloat(getElement('deliverablesSpeedSlider').value) / 100,
                preserve_pitch: (preservePitchEl && preservePitchEl.checked) || false
            });
        }

        const deliverablesPitchEnabled = getElement('deliverablesPitchEnabled');
        if (deliverablesPitchEnabled && deliverablesPitchEnabled.checked) {
            enabledTransforms.push({
                type: 'pitch',
                semitones: parseInt(getElement('deliverablesPitchSlider').value)
            });
        }

        const deliverablesReverbEnabled = getElement('deliverablesReverbEnabled');
        if (deliverablesReverbEnabled && deliverablesReverbEnabled.checked) {
            enabledTransforms.push({
                type: 'reverb',
                delay_ms: parseFloat(getElement('deliverablesReverbSlider').value)
            });
        }

        const deliverablesNoiseEnabled = getElement('deliverablesNoiseEnabled');
        if (deliverablesNoiseEnabled && deliverablesNoiseEnabled.checked) {
            enabledTransforms.push({
                type: 'noise_reduction',
                strength: parseFloat(getElement('deliverablesNoiseSlider').value) / 100
            });
        }

        const deliverablesEQEnabled2 = getElement('deliverablesEQEnabled');
        if (deliverablesEQEnabled2 && deliverablesEQEnabled2.checked) {
            enabledTransforms.push({
                type: 'eq',
                gain_db: parseFloat(getElement('deliverablesEQSlider').value)
            });
        }

        const deliverablesCompressionEnabled = getElement('deliverablesCompressionEnabled');
        if (deliverablesCompressionEnabled && deliverablesCompressionEnabled.checked) {
            const codecSelectEl = getElement('deliverablesCodecSelect');
            const codec = codecSelectEl && codecSelectEl.value;
            if (codec !== 'None') {
                const bitrateSelectEl = getElement('deliverablesBitrateSelect');
                enabledTransforms.push({
                    type: 'compression',
                    codec: codec.toLowerCase(),
                    bitrate: (bitrateSelectEl && bitrateSelectEl.value) || null
                });
            }
        }

        const deliverablesOverlayEnabled = getElement('deliverablesOverlayEnabled');
        if (deliverablesOverlayEnabled && deliverablesOverlayEnabled.checked) {
            const overlayFileEl = getElement('deliverablesOverlayFile');
            const overlayFile = overlayFileEl && overlayFileEl.files && overlayFileEl.files[0];
            const overlayGainSliderEl = getElement('deliverablesOverlayGainSlider');
            enabledTransforms.push({
                type: 'overlay',
                gain_db: parseFloat((overlayGainSliderEl && overlayGainSliderEl.value) || -6),
                overlay_file: overlayFile ? overlayFile.name : null
            });
        }

        const deliverablesHighpassEnabled = getElement('deliverablesHighpassEnabled');
        if (deliverablesHighpassEnabled && deliverablesHighpassEnabled.checked) {
            enabledTransforms.push({
                type: 'highpass',
                freq_hz: parseFloat(getElement('deliverablesHighpassSlider').value)
            });
        }

        const deliverablesLowpassEnabled = getElement('deliverablesLowpassEnabled');
        if (deliverablesLowpassEnabled && deliverablesLowpassEnabled.checked) {
            enabledTransforms.push({
                type: 'lowpass',
                freq_hz: parseFloat(getElement('deliverablesLowpassSlider').value)
            });
        }

        const deliverablesBoostHighsEnabled = getElement('deliverablesBoostHighsEnabled');
        if (deliverablesBoostHighsEnabled && deliverablesBoostHighsEnabled.checked) {
            enabledTransforms.push({
                type: 'boost_highs',
                gain_db: parseFloat(getElement('deliverablesBoostHighsSlider').value)
            });
        }

        const deliverablesBoostLowsEnabled = getElement('deliverablesBoostLowsEnabled');
        if (deliverablesBoostLowsEnabled && deliverablesBoostLowsEnabled.checked) {
            enabledTransforms.push({
                type: 'boost_lows',
                gain_db: parseFloat(getElement('deliverablesBoostLowsSlider').value)
            });
        }

        const deliverablesTelephoneEnabled = getElement('deliverablesTelephoneEnabled');
        if (deliverablesTelephoneEnabled && deliverablesTelephoneEnabled.checked) {
            const telephoneLowEl = getElement('deliverablesTelephoneLow');
            const telephoneHighEl = getElement('deliverablesTelephoneHigh');
            enabledTransforms.push({
                type: 'telephone',
                low_freq: parseFloat((telephoneLowEl && telephoneLowEl.value) || 300),
                high_freq: parseFloat((telephoneHighEl && telephoneHighEl.value) || 3000)
            });
        }

        const deliverablesLimitingEnabled = getElement('deliverablesLimitingEnabled');
        if (deliverablesLimitingEnabled && deliverablesLimitingEnabled.checked) {
            enabledTransforms.push({
                type: 'limiting',
                ceiling_db: parseFloat(getElement('deliverablesLimitingSlider').value)
            });
        }

        const deliverablesMultibandEnabled = getElement('deliverablesMultibandEnabled');
        if (deliverablesMultibandEnabled && deliverablesMultibandEnabled.checked) {
            enabledTransforms.push({
                type: 'multiband'
            });
        }

        const deliverablesAddNoiseEnabled = getElement('deliverablesAddNoiseEnabled');
        if (deliverablesAddNoiseEnabled && deliverablesAddNoiseEnabled.checked) {
            const noiseTypeSelectEl = getElement('deliverablesNoiseTypeSelect');
            const noiseSNRSliderEl = getElement('deliverablesNoiseSNRSlider');
            enabledTransforms.push({
                type: 'add_noise',
                noise_type: (noiseTypeSelectEl && noiseTypeSelectEl.value) || 'white',
                snr_db: parseFloat((noiseSNRSliderEl && noiseSNRSliderEl.value) || 20)
            });
        }

        const deliverablesCropEnabled = getElement('deliverablesCropEnabled');
        if (deliverablesCropEnabled && deliverablesCropEnabled.checked) {
            const cropTypeSelectEl = getElement('deliverablesCropTypeSelect');
            const cropType = cropTypeSelectEl && cropTypeSelectEl.value;
            const cropDurationEl = getElement('deliverablesCropDuration');
            enabledTransforms.push({
                type: 'crop',
                crop_type: cropType,
                duration: (cropType === 'middle' || cropType === 'end') ?
                    parseFloat((cropDurationEl && cropDurationEl.value) || 10) : null
            });
        }

        const deliverablesEmbeddedSampleEnabled = getElement('deliverablesEmbeddedSampleEnabled');
        if (deliverablesEmbeddedSampleEnabled && deliverablesEmbeddedSampleEnabled.checked) {
            const embeddedSampleFileEl = getElement('deliverablesEmbeddedSampleFile');
            const samplePath = embeddedSampleFileEl && embeddedSampleFileEl.value;
            if (!samplePath || !samplePath.trim()) {
                showError('Embedded Sample requires a sample file to be selected');
                return;
            }

            const embeddedBackgroundFileEl = getElement('deliverablesEmbeddedBackgroundFile');
            const backgroundPath = (embeddedBackgroundFileEl && embeddedBackgroundFileEl.value) || '';
            const embeddedApplyTransformEl = getElement('deliverablesEmbeddedApplyTransform');
            const applyTransform = (embeddedApplyTransformEl && embeddedApplyTransformEl.value) || 'None';
            const embeddedTransformParamsEl = getElement('deliverablesEmbeddedTransformParams');
            const transformParams = (embeddedTransformParamsEl && embeddedTransformParamsEl.value) || '';

            const embeddedPositionEl = getElement('deliverablesEmbeddedPosition');
            const embeddedSampleDurationEl = getElement('deliverablesEmbeddedSampleDuration');
            const embeddedVolumeDbEl = getElement('deliverablesEmbeddedVolumeDb');
            enabledTransforms.push({
                type: 'embedded_sample',
                sample_path: samplePath,
                background_path: backgroundPath.trim() || null,
                position: (embeddedPositionEl && embeddedPositionEl.value) || 'start',
                sample_duration: parseFloat((embeddedSampleDurationEl && embeddedSampleDurationEl.value) || 1.5),
                volume_db: parseFloat((embeddedVolumeDbEl && embeddedVolumeDbEl.value) || 0),
                apply_transform: applyTransform !== 'None' ? applyTransform : null,
                transform_params: transformParams.trim() ? transformParams : null
            });
        }

        const deliverablesSongAInSongBEnabled = getElement('deliverablesSongAInSongBEnabled');
        if (deliverablesSongAInSongBEnabled && deliverablesSongAInSongBEnabled.checked) {
            const songAFileEl = getElement('deliverablesSongAFile');
            const songAPath = (songAFileEl && songAFileEl.value) || '';
            const songBBaseFileEl = getElement('deliverablesSongBBaseFile');
            const songBBasePath = (songBBaseFileEl && songBBaseFileEl.value) || '';
            const songAApplyTransformEl = getElement('deliverablesSongAApplyTransform');
            const applyTransform = (songAApplyTransformEl && songAApplyTransformEl.value) || 'None';
            const songATransformParamsEl = getElement('deliverablesSongATransformParams');
            const transformParams = (songATransformParamsEl && songATransformParamsEl.value) || '';

            const songASampleStartTimeEl = getElement('deliverablesSongASampleStartTime');
            const songASampleDurationEl = getElement('deliverablesSongASampleDuration');
            const songBDurationEl = getElement('deliverablesSongBDuration');
            const songAMixVolumeDbEl = getElement('deliverablesSongAMixVolumeDb');
            enabledTransforms.push({
                type: 'song_a_in_song_b',
                song_a_path: songAPath.trim() || null,
                song_b_base_path: songBBasePath.trim() || null,
                sample_start_time: parseFloat((songASampleStartTimeEl && songASampleStartTimeEl.value) || 0.0),
                sample_duration: parseFloat((songASampleDurationEl && songASampleDurationEl.value) || 1.5),
                song_b_duration: parseFloat((songBDurationEl && songBDurationEl.value) || 30.0),
                mix_volume_db: parseFloat((songAMixVolumeDbEl && songAMixVolumeDbEl.value) || 0),
                apply_transform: applyTransform !== 'None' ? applyTransform : null,
                transform_params: transformParams.trim() ? transformParams : null
            });
        }

        if (enabledTransforms.length === 0) {
            showError('Please enable at least one transformation');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('transforms', JSON.stringify(enabledTransforms));
            formData.append('generate_reports', 'false');

            const overlayFileEl = getElement('deliverablesOverlayFile');
            const overlayFile = overlayFileEl && overlayFileEl.files && overlayFileEl.files[0];
            if (overlayFile) {
                formData.append('overlay_file', overlayFile);
            }

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/deliverables-batch`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.message || errorMessage;
                } catch {
                    const errorText = await response.text();
                    errorMessage = errorText.substring(0, 200);
                }
                throw new Error(errorMessage);
            }

            const result = await response.json();

            if (result.status === 'success') {
                showCompletionAlert(`Quick apply succeeded: ${enabledTransforms.length} transformation(s). No full Phase 1/Phase 2 matrix reports generated.`, 'info');
                setTimeout(() => {
                    this.loadDeliverables();
                    if (window.loadDashboard) window.loadDashboard();
                }, 1000);
            } else {
                throw new Error(result.message || 'Failed to apply transformations');
            }
        } catch (error) {
            showError('Failed to apply transformations: ' + error.message);
            console.error('Deliverables transform error:', error);
        }
    }
}

// Export singleton instance and individual functions
export const deliverablesManager = new DeliverablesManager();

export const loadDeliverables = () => deliverablesManager.loadDeliverables();
export const viewReport = (reportPath, runId) => deliverablesManager.viewReport(reportPath, runId);
export const downloadReportZip = (runId) => deliverablesManager.downloadReportZip(runId);
export const viewRunDetails = (runId) => deliverablesManager.viewRunDetails(runId);
export const deleteReport = (runId) => deliverablesManager.deleteReport(runId);
export const loadDeliverablesAudioFiles = () => deliverablesManager.loadDeliverablesAudioFiles();
export const loadDeliverablesAudioInfo = (filePath) => deliverablesManager.loadDeliverablesAudioInfo(filePath);
export const handleDeliverablesDrop = (event) => deliverablesManager.handleDeliverablesDrop(event);
export const handleDeliverablesFileSelect = (event) => deliverablesManager.handleDeliverablesFileSelect(event);
export const handleDeliverablesFileUpload = (file) => deliverablesManager.handleDeliverablesFileUpload(file);
export const updateDeliverablesSpeedValue = (value) => deliverablesManager.updateDeliverablesSpeedValue(value);
export const updateDeliverablesPitchValue = (value) => deliverablesManager.updateDeliverablesPitchValue(value);
export const updateDeliverablesReverbValue = (value) => deliverablesManager.updateDeliverablesReverbValue(value);
export const updateDeliverablesNoiseValue = (value) => deliverablesManager.updateDeliverablesNoiseValue(value);
export const updateDeliverablesEQValue = (value) => deliverablesManager.updateDeliverablesEQValue(value);
export const updateDeliverablesOverlayGainValue = (value) => deliverablesManager.updateDeliverablesOverlayGainValue(value);
export const updateDeliverablesSliderDisplay = (type, value) => deliverablesManager.updateDeliverablesSliderDisplay(type, value);
export const updateDeliverablesBitrateEnabled = () => deliverablesManager.updateDeliverablesBitrateEnabled();
export const updateDeliverablesCropDuration = () => deliverablesManager.updateDeliverablesCropDuration();
export const toggleDeliverablesEmbeddedTransformParams = () => deliverablesManager.toggleDeliverablesEmbeddedTransformParams();
export const toggleDeliverablesSongATransformParams = () => deliverablesManager.toggleDeliverablesSongATransformParams();
export const updateDeliverablesTransformState = () => deliverablesManager.updateDeliverablesTransformState();
export const applyAllDeliverablesTransforms = () => deliverablesManager.applyAllDeliverablesTransforms();