/**
 * DAW Parser Component
 * Handles DAW file upload, parsing, and metadata display
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    formatFileSize,
    getElement
} from '../utils/helpers.js';
import {
    showError,
    showNotification
} from './notifications.js';

class DAWParserManager {
    async loadDAWFiles() {
        const fileList = getElement('dawFileList');

        if (fileList) {
            fileList.innerHTML = '<p style="color: #9ca3af; text-align: center; padding: 20px;">Loading DAW files...</p>';
        }

        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DAW.FILES}`);

            if (!response.ok) {
                throw new Error(`Failed to fetch DAW files: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();

            if (data.daw_files && data.daw_files.length > 0) {
                fileList.innerHTML = '';
                data.daw_files.forEach(file => {
                    const item = document.createElement('div');
                    item.className = 'daw-file-item';
                    // Escape file path for use in onclick
                    const escapedPath = file.path.replace(/'/g, "\\'");
                    
                    item.innerHTML = `
                        <div class="daw-file-info">
                            <div class="daw-file-name" title="${file.name}">${file.name}</div>
                            <div class="daw-file-meta">${file.type.toUpperCase()} • ${formatFileSize(file.size)} • ${new Date(file.modified).toLocaleDateString()}</div>
                        </div>
                        <div class="daw-file-actions">
                            <button class="btn" onclick="parseDAWFile('${escapedPath}', true)">Parse (Detailed)</button>
                            <button class="btn" onclick="viewDAWMetadata('${escapedPath}')">View Metadata</button>
                        </div>
                    `;
                    fileList.appendChild(item);
                    
                    // Hide any "Parse" button with false parameter (in case it exists from cached code)
                    const buttons = item.querySelectorAll('button[onclick*="parseDAWFile"]');
                    buttons.forEach(btn => {
                        const onclick = btn.getAttribute('onclick') || '';
                        if (onclick.includes('parseDAWFile') && (onclick.includes(', false)') || onclick.includes(',false)'))) {
                            btn.style.display = 'none';
                        }
                    });
                });
            } else {
                if (fileList) {
                    fileList.innerHTML = '<p style="color: #9ca3af; text-align: center; padding: 20px;">No DAW files uploaded yet</p>';
                }
            }
        } catch (error) {
            console.error('Error loading DAW files:', error);
            if (fileList) {
                fileList.innerHTML = `<p style="color: #f87171; text-align: center; padding: 20px;">Error loading DAW files: ${error.message}. Please check your connection to the server.</p>`;
            }
        }
    }

    handleDAWDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        const uploadArea = getElement('dawUploadArea');
        if (uploadArea) uploadArea.classList.remove('dragover');

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.uploadDAWFile(files[0]);
        }
    }

    handleDAWFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.uploadDAWFile(file);
        }
    }

    async uploadDAWFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            showNotification('Uploading DAW file...', 'info');
            const response = await fetch(`${API_CONFIG.BASE_URL}/daw/upload`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                showNotification('DAW file uploaded successfully!', 'success');
                this.loadDAWFiles();
            } else {
                showError('Failed to upload DAW file: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            showError('Error uploading DAW file: ' + error.message);
        }
    }

    async parseDAWFile(filePath, detailed = false) {
        try {
            showNotification('Parsing DAW file...', 'info');
            const formData = new FormData();
            formData.append('file_path', filePath);
            formData.append('detailed', detailed ? 'true' : 'false');

            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DAW.PARSE}`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                showNotification('DAW file parsed successfully!', 'success');
                this.displayDAWMetadata(result.metadata, detailed);
            } else {
                showError('Failed to parse DAW file: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            showError('Error parsing DAW file: ' + error.message);
        }
    }

    async viewDAWMetadata(filePath) {
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DAW.METADATA}`);
            const data = await response.json();

            const fileName = filePath.split('/').pop().replace(/\.[^/.]+$/, '');
            const metadata = Object.values(data.metadata || {}).find(m =>
                m.project_path && m.project_path.includes(fileName)
            );

            if (metadata) {
                // Check if metadata has detailed data (check both old and new key names for compatibility)
                const hasDetailed = metadata.midi_data || metadata.arrangement || 
                                   metadata.automation_data || metadata.automation ||
                                   metadata.tempo_changes_data || metadata.plugin_chains_data ||
                                   metadata.sample_sources_data || metadata.key_changes_data;
                this.displayDAWMetadata(metadata, hasDetailed);
            } else {
                // Parse with detailed data by default when viewing
                await this.parseDAWFile(filePath, true);
            }
        } catch (error) {
            showError('Error loading DAW metadata: ' + error.message);
        }
    }

    displayDAWMetadata(metadata, detailed = false) {
        const metadataView = getElement('dawMetadataView');
        if (!metadataView) return;

        if (!metadata) {
            metadataView.innerHTML = '<p style="color: #9ca3af; text-align: center; padding: 20px;">No metadata available</p>';
            return;
        }

        // Check if we have detailed data (check both old and new key names for compatibility)
        const hasDetailed = metadata.midi_data || metadata.arrangement || 
                           metadata.automation_data || metadata.automation ||
                           metadata.tempo_changes_data || metadata.plugin_chains_data ||
                           metadata.sample_sources_data || metadata.key_changes_data;

        let html = '<div class="daw-metadata-container">';
        
        // Header with toggle and export buttons
        html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #374151;">';
        html += '<h3 style="margin: 0; color: #f3f4f6;">DAW Project Metadata</h3>';
        html += '<div style="display: flex; gap: 10px;">';
        
        if (hasDetailed) {
            html += `<button class="btn" onclick="toggleDAWDetailedView()" id="dawToggleDetailBtn" style="font-size: 12px; padding: 6px 12px;">Show Summary</button>`;
        } else {
            html += `<button class="btn" onclick="loadDAWDetailedView()" style="font-size: 12px; padding: 6px 12px;">Load Detailed View</button>`;
        }
        
        html += `<button class="btn" onclick="exportDAWMetadata()" style="font-size: 12px; padding: 6px 12px;">Export JSON</button>`;
        html += '</div></div>';

        // Summary Statistics (always shown)
        html += '<div id="dawSummaryView" style="display: block;">';
        html += '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px;">';

        html += `<div class="daw-stat-item"><span class="daw-stat-label">DAW Type:</span><span class="daw-stat-value">${metadata.daw_type || 'Unknown'}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Version:</span><span class="daw-stat-value">${metadata.version || 'Unknown'}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">MIDI Tracks:</span><span class="daw-stat-value">${metadata.midi_tracks || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Total Notes:</span><span class="daw-stat-value">${metadata.total_notes || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Arrangement Clips:</span><span class="daw-stat-value">${metadata.arrangement_clips || 0}</span></div>`;
        // Handle both number (count) and array cases to prevent [object Object] display
        const getCount = (value) => {
            if (Array.isArray(value)) return value.length;
            if (typeof value === 'number') return value;
            return 0;
        };
        
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Tempo Changes:</span><span class="daw-stat-value">${getCount(metadata.tempo_changes)}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Plugin Chains:</span><span class="daw-stat-value">${getCount(metadata.plugin_chains)}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Sample Sources:</span><span class="daw-stat-value">${getCount(metadata.sample_sources)}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Automation Tracks:</span><span class="daw-stat-value">${metadata.automation_tracks || 0}</span></div>`;

        if (metadata.extracted_at) {
            html += `<div class="daw-stat-item"><span class="daw-stat-label">Extracted:</span><span class="daw-stat-value">${new Date(metadata.extracted_at).toLocaleString()}</span></div>`;
        }

        html += '</div></div>';

        // Detailed View (shown if hasDetailed is true)
        if (hasDetailed) {
            html += '<div id="dawDetailedView" style="display: none; margin-top: 20px;">';
            
            // Tabs
            html += '<div class="daw-tabs daw-scrollable daw-scrollable-horizontal">';
            html += '<button class="daw-tab-btn active" onclick="switchDAWTab(\'midi\')">MIDI Data</button>';
            html += '<button class="daw-tab-btn" onclick="switchDAWTab(\'arrangement\')">Arrangement</button>';
            html += '<button class="daw-tab-btn" onclick="switchDAWTab(\'automation\')">Automation</button>';
            html += '<button class="daw-tab-btn" onclick="switchDAWTab(\'plugins\')">Plugins</button>';
            html += '<button class="daw-tab-btn" onclick="switchDAWTab(\'samples\')">Samples</button>';
            html += '<button class="daw-tab-btn" onclick="switchDAWTab(\'tempo\')">Tempo/Key</button>';
            html += '</div>';

            // MIDI Data Tab
            html += '<div id="dawTabMidi" class="daw-tab-content active">';
            if (metadata.midi_data && metadata.midi_data.length > 0) {
                metadata.midi_data.forEach((track, idx) => {
                    html += `<div class="daw-section" style="margin-bottom: 20px; padding: 15px; background: #1f2937; border-radius: 8px;">`;
                    html += `<h4 style="margin: 0 0 10px 0; color: #60a5fa;">Track ${idx + 1}: ${track.track_name || 'Unnamed'}</h4>`;
                    html += `<div style="color: #9ca3af; font-size: 12px; margin-bottom: 10px;">`;
                    html += `Notes: ${track.note_count || track.notes?.length || 0} | `;
                    if (track.instrument) html += `Instrument: ${track.instrument} | `;
                    html += `Volume: ${(track.volume || 1.0).toFixed(2)} | Pan: ${(track.pan || 0.0).toFixed(2)}`;
                    html += `</div>`;
                    
                    if (track.notes && track.notes.length > 0) {
                        html += `<div class="daw-scrollable daw-scrollable-vertical" style="max-height: 300px; overflow-y: auto;">`;
                        html += `<table style="width: 100%; border-collapse: collapse; font-size: 12px;">`;
                        html += `<thead><tr style="background: #111827;"><th style="padding: 8px; text-align: left;">Note</th><th style="padding: 8px; text-align: left;">Velocity</th><th style="padding: 8px; text-align: left;">Start</th><th style="padding: 8px; text-align: left;">Duration</th><th style="padding: 8px; text-align: left;">Channel</th></tr></thead>`;
                        html += `<tbody>`;
                        track.notes.slice(0, 100).forEach(note => {
                            html += `<tr style="border-bottom: 1px solid #374151;">`;
                            html += `<td style="padding: 6px;">${note.note}</td>`;
                            html += `<td style="padding: 6px;">${note.velocity}</td>`;
                            html += `<td style="padding: 6px;">${note.start_time.toFixed(2)}</td>`;
                            html += `<td style="padding: 6px;">${note.duration.toFixed(2)}</td>`;
                            html += `<td style="padding: 6px;">${note.channel || 0}</td>`;
                            html += `</tr>`;
                        });
                        if (track.notes.length > 100) {
                            html += `<tr><td colspan="5" style="padding: 8px; text-align: center; color: #9ca3af;">... and ${track.notes.length - 100} more notes</td></tr>`;
                        }
                        html += `</tbody></table></div>`;
                    }
                    html += `</div>`;
                });
            } else {
                html += '<p style="color: #9ca3af; text-align: center; padding: 20px;">No MIDI data available</p>';
            }
            html += '</div>';

            // Arrangement Tab
            html += '<div id="dawTabArrangement" class="daw-tab-content" style="display: none;">';
            if (metadata.arrangement && metadata.arrangement.clips && metadata.arrangement.clips.length > 0) {
                html += `<div style="margin-bottom: 15px; color: #9ca3af; font-size: 12px;">Total Length: ${metadata.arrangement.total_length?.toFixed(2) || 0} | Tracks: ${metadata.arrangement.tracks?.length || 0}</div>`;
                html += `<div class="daw-scrollable daw-scrollable-vertical" style="max-height: 400px; overflow-y: auto;">`;
                html += `<table style="width: 100%; border-collapse: collapse; font-size: 12px;">`;
                html += `<thead><tr style="background: #111827;"><th style="padding: 8px; text-align: left;">Clip Name</th><th style="padding: 8px; text-align: left;">Track</th><th style="padding: 8px; text-align: left;">Type</th><th style="padding: 8px; text-align: left;">Start</th><th style="padding: 8px; text-align: left;">End</th><th style="padding: 8px; text-align: left;">Duration</th></tr></thead>`;
                html += `<tbody>`;
                metadata.arrangement.clips.slice(0, 200).forEach(clip => {
                    html += `<tr style="border-bottom: 1px solid #374151;">`;
                    html += `<td style="padding: 6px;">${clip.clip_name || 'Unnamed'}</td>`;
                    html += `<td style="padding: 6px;">${clip.track_name || 'Unknown'}</td>`;
                    html += `<td style="padding: 6px;">${clip.clip_type || 'midi'}</td>`;
                    html += `<td style="padding: 6px;">${clip.start_time?.toFixed(2) || 0}</td>`;
                    html += `<td style="padding: 6px;">${clip.end_time?.toFixed(2) || 0}</td>`;
                    html += `<td style="padding: 6px;">${((clip.end_time || 0) - (clip.start_time || 0)).toFixed(2)}</td>`;
                    html += `</tr>`;
                });
                if (metadata.arrangement.clips.length > 200) {
                    html += `<tr><td colspan="6" style="padding: 8px; text-align: center; color: #9ca3af;">... and ${metadata.arrangement.clips.length - 200} more clips</td></tr>`;
                }
                html += `</tbody></table></div>`;
            } else {
                html += '<p style="color: #9ca3af; text-align: center; padding: 20px;">No arrangement data available</p>';
            }
            html += '</div>';

            // Automation Tab
            html += '<div id="dawTabAutomation" class="daw-tab-content" style="display: none;">';
            const automationData = metadata.automation_data || metadata.automation;
            if (automationData && Array.isArray(automationData) && automationData.length > 0) {
                automationData.forEach((auto, idx) => {
                    html += `<div class="daw-section" style="margin-bottom: 15px; padding: 15px; background: #1f2937; border-radius: 8px;">`;
                    html += `<h4 style="margin: 0 0 10px 0; color: #60a5fa;">${auto.parameter_name || 'Unknown Parameter'}</h4>`;
                    html += `<div style="color: #9ca3af; font-size: 12px; margin-bottom: 10px;">`;
                    html += `Track: ${auto.track_name || 'Unknown'} | Points: ${auto.point_count || auto.points?.length || 0}`;
                    html += `</div>`;
                    
                    if (auto.points && auto.points.length > 0) {
                        html += `<div class="daw-scrollable daw-scrollable-vertical" style="max-height: 200px; overflow-y: auto;">`;
                        html += `<table style="width: 100%; border-collapse: collapse; font-size: 11px;">`;
                        html += `<thead><tr style="background: #111827;"><th style="padding: 6px; text-align: left;">Time</th><th style="padding: 6px; text-align: left;">Value</th><th style="padding: 6px; text-align: left;">Curve</th></tr></thead>`;
                        html += `<tbody>`;
                        auto.points.slice(0, 50).forEach(point => {
                            html += `<tr style="border-bottom: 1px solid #374151;">`;
                            html += `<td style="padding: 4px;">${point.time?.toFixed(3) || 0}</td>`;
                            html += `<td style="padding: 4px;">${point.value?.toFixed(3) || 0}</td>`;
                            html += `<td style="padding: 4px;">${point.curve_type || '-'}</td>`;
                            html += `</tr>`;
                        });
                        if (auto.points.length > 50) {
                            html += `<tr><td colspan="3" style="padding: 6px; text-align: center; color: #9ca3af;">... and ${auto.points.length - 50} more points</td></tr>`;
                        }
                        html += `</tbody></table></div>`;
                    }
                    html += `</div>`;
                });
            } else {
                html += '<p style="color: #9ca3af; text-align: center; padding: 20px;">No automation data available</p>';
            }
            html += '</div>';

            // Plugins Tab
            html += '<div id="dawTabPlugins" class="daw-tab-content" style="display: none;">';
            const pluginChains = metadata.plugin_chains_data || metadata.plugin_chains;
            if (pluginChains && Array.isArray(pluginChains) && pluginChains.length > 0) {
                pluginChains.forEach(chain => {
                    html += `<div class="daw-section" style="margin-bottom: 15px; padding: 15px; background: #1f2937; border-radius: 8px;">`;
                    html += `<h4 style="margin: 0 0 10px 0; color: #60a5fa;">${chain.track_name || 'Unknown Track'}</h4>`;
                    html += `<div style="color: #9ca3af; font-size: 12px; margin-bottom: 10px;">Devices: ${chain.device_count || chain.devices?.length || 0}</div>`;
                    
                    if (chain.devices && chain.devices.length > 0) {
                        chain.devices.forEach(device => {
                            html += `<div style="margin-left: 15px; margin-bottom: 10px; padding: 10px; background: #111827; border-radius: 4px;">`;
                            html += `<div style="font-weight: 600; color: #f3f4f6; margin-bottom: 5px;">${device.device_name || 'Unknown'}</div>`;
                            html += `<div style="color: #9ca3af; font-size: 11px; margin-bottom: 5px;">Type: ${device.device_type || 'unknown'} | Parameters: ${device.parameter_count || device.parameters?.length || 0}</div>`;
                            if (device.parameters && device.parameters.length > 0) {
                                html += `<div style="font-size: 11px; color: #9ca3af;">`;
                                device.parameters.slice(0, 5).forEach(param => {
                                    html += `${param.parameter_name}: ${param.value?.toFixed(2) || 0}${param.unit || ''} | `;
                                });
                                if (device.parameters.length > 5) {
                                    html += `... and ${device.parameters.length - 5} more`;
                                }
                                html += `</div>`;
                            }
                            html += `</div>`;
                        });
                    }
                    html += `</div>`;
                });
            } else {
                html += '<p style="color: #9ca3af; text-align: center; padding: 20px;">No plugin data available</p>';
            }
            html += '</div>';

            // Samples Tab
            html += '<div id="dawTabSamples" class="daw-tab-content" style="display: none;">';
            const sampleSources = metadata.sample_sources_data || metadata.sample_sources;
            if (sampleSources && Array.isArray(sampleSources) && sampleSources.length > 0) {
                html += `<div class="daw-scrollable daw-scrollable-vertical" style="max-height: 400px; overflow-y: auto;">`;
                html += `<table style="width: 100%; border-collapse: collapse; font-size: 12px;">`;
                html += `<thead><tr style="background: #111827;"><th style="padding: 8px; text-align: left;">Sample Name</th><th style="padding: 8px; text-align: left;">Track</th><th style="padding: 8px; text-align: left;">Path</th></tr></thead>`;
                html += `<tbody>`;
                sampleSources.forEach(sample => {
                    html += `<tr style="border-bottom: 1px solid #374151;">`;
                    html += `<td style="padding: 6px;">${sample.sample_name || 'Unknown'}</td>`;
                    html += `<td style="padding: 6px;">${sample.track_name || 'Unknown'}</td>`;
                    html += `<td style="padding: 6px; font-size: 11px; color: #9ca3af;">${sample.file_path || '-'}</td>`;
                    html += `</tr>`;
                });
                html += `</tbody></table></div>`;
            } else {
                html += '<p style="color: #9ca3af; text-align: center; padding: 20px;">No sample data available</p>';
            }
            html += '</div>';

            // Tempo/Key Tab
            html += '<div id="dawTabTempo" class="daw-tab-content" style="display: none;">';
            html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">';
            
            // Tempo Changes
            html += '<div>';
            html += '<h4 style="color: #60a5fa; margin-bottom: 10px;">Tempo Changes</h4>';
            const tempoChanges = metadata.tempo_changes_data || metadata.tempo_changes;
            if (tempoChanges && Array.isArray(tempoChanges) && tempoChanges.length > 0) {
                html += `<table style="width: 100%; border-collapse: collapse; font-size: 12px;">`;
                html += `<thead><tr style="background: #111827;"><th style="padding: 8px; text-align: left;">Time</th><th style="padding: 8px; text-align: left;">Tempo (BPM)</th><th style="padding: 8px; text-align: left;">Time Sig</th></tr></thead>`;
                html += `<tbody>`;
                tempoChanges.forEach(tc => {
                    html += `<tr style="border-bottom: 1px solid #374151;">`;
                    html += `<td style="padding: 6px;">${tc.time?.toFixed(2) || 0}</td>`;
                    html += `<td style="padding: 6px;">${tc.tempo?.toFixed(2) || 0}</td>`;
                    html += `<td style="padding: 6px;">${tc.time_signature || '-'}</td>`;
                    html += `</tr>`;
                });
                html += `</tbody></table>`;
            } else {
                html += '<p style="color: #9ca3af; font-size: 12px;">No tempo changes</p>';
            }
            html += '</div>';
            
            // Key Changes
            html += '<div>';
            html += '<h4 style="color: #60a5fa; margin-bottom: 10px;">Key Changes</h4>';
            const keyChanges = metadata.key_changes_data || metadata.key_changes;
            if (keyChanges && Array.isArray(keyChanges) && keyChanges.length > 0) {
                html += `<table style="width: 100%; border-collapse: collapse; font-size: 12px;">`;
                html += `<thead><tr style="background: #111827;"><th style="padding: 8px; text-align: left;">Time</th><th style="padding: 8px; text-align: left;">Key</th><th style="padding: 8px; text-align: left;">Scale</th></tr></thead>`;
                html += `<tbody>`;
                keyChanges.forEach(kc => {
                    html += `<tr style="border-bottom: 1px solid #374151;">`;
                    html += `<td style="padding: 6px;">${kc.time?.toFixed(2) || 0}</td>`;
                    html += `<td style="padding: 6px;">${kc.key || '-'}</td>`;
                    html += `<td style="padding: 6px;">${kc.scale || '-'}</td>`;
                    html += `</tr>`;
                });
                html += `</tbody></table>`;
            } else {
                html += '<p style="color: #9ca3af; font-size: 12px;">No key changes</p>';
            }
            html += '</div>';
            
            html += '</div></div>';

            html += '</div>'; // End detailed view
        }

        html += '</div>'; // End container

        metadataView.innerHTML = html;
        
        // Store metadata for export
        window.currentDAWMetadata = metadata;
    }
}

// Helper functions for UI interactions
function toggleDAWDetailedView() {
    const summaryView = getElement('dawSummaryView');
    const detailedView = getElement('dawDetailedView');
    const toggleBtn = getElement('dawToggleDetailBtn');
    
    if (!summaryView || !detailedView) return;
    
    if (summaryView.style.display === 'none') {
        summaryView.style.display = 'block';
        detailedView.style.display = 'none';
        if (toggleBtn) toggleBtn.textContent = 'Show Detailed View';
    } else {
        summaryView.style.display = 'none';
        detailedView.style.display = 'block';
        if (toggleBtn) toggleBtn.textContent = 'Show Summary';
    }
}

function loadDAWDetailedView() {
    // Get current file path from stored metadata
    if (window.currentDAWMetadata && window.currentDAWMetadata.project_path) {
        // Extract file path from metadata
        const filePath = window.currentDAWMetadata.project_path;
        // Try to get file path from current metadata or file list
        const fileList = getElement('dawFileList');
        if (fileList) {
            const fileItems = fileList.querySelectorAll('.daw-file-item');
            for (const item of fileItems) {
                const parseBtn = item.querySelector('button[onclick*="parseDAWFile"]');
                if (parseBtn) {
                    const onclick = parseBtn.getAttribute('onclick');
                    // Match both old and new formats
                    const match = onclick.match(/parseDAWFile\('([^']+)'(?:,\s*(true|false))?\)/);
                    if (match && match[1]) {
                        dawParserManager.parseDAWFile(match[1], true);
                        return;
                    }
                }
            }
        }
        
        // Try to construct path from metadata
        if (filePath) {
            // Try relative path first
            dawParserManager.parseDAWFile(filePath, true);
            return;
        }
    }
    
    showError('Unable to determine file path. Please parse the file again with "Parse (Detailed)" button.');
}

function switchDAWTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.daw-tab-content');
    tabContents.forEach(tab => {
        tab.style.display = 'none';
        tab.classList.remove('active');
    });
    
    // Remove active class from all tabs
    const tabButtons = document.querySelectorAll('.daw-tab-btn');
    tabButtons.forEach(btn => btn.classList.remove('active'));
    
    // Map tab names to element IDs
    const tabIdMap = {
        'midi': 'dawTabMidi',
        'arrangement': 'dawTabArrangement',
        'automation': 'dawTabAutomation',
        'plugins': 'dawTabPlugins',
        'samples': 'dawTabSamples',
        'tempo': 'dawTabTempo'
    };
    
    // Show selected tab
    const tabId = tabIdMap[tabName.toLowerCase()];
    if (tabId) {
        const selectedTab = getElement(tabId);
        if (selectedTab) {
            selectedTab.style.display = 'block';
            selectedTab.classList.add('active');
        }
    }
    
    // Activate selected button
    const selectedBtn = Array.from(tabButtons).find(btn => {
        const btnText = btn.textContent.toLowerCase();
        return btnText.includes(tabName.toLowerCase()) || 
               (tabName === 'midi' && btnText.includes('midi')) ||
               (tabName === 'tempo' && btnText.includes('tempo'));
    });
    if (selectedBtn) {
        selectedBtn.classList.add('active');
    }
}

function exportDAWMetadata() {
    if (!window.currentDAWMetadata) {
        showError('No metadata available to export');
        return;
    }
    
    const dataStr = JSON.stringify(window.currentDAWMetadata, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `daw_metadata_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    showNotification('Metadata exported successfully!', 'success');
}

// Export singleton instance and individual functions
export const dawParserManager = new DAWParserManager();

export const loadDAWFiles = () => dawParserManager.loadDAWFiles();
export const handleDAWDrop = (event) => dawParserManager.handleDAWDrop(event);
export const handleDAWFileSelect = (event) => dawParserManager.handleDAWFileSelect(event);
export const uploadDAWFile = (file) => dawParserManager.uploadDAWFile(file);
export const parseDAWFile = (filePath, detailed = false) => dawParserManager.parseDAWFile(filePath, detailed);
export const viewDAWMetadata = (filePath) => dawParserManager.viewDAWMetadata(filePath);
export const displayDAWMetadata = (metadata) => dawParserManager.displayDAWMetadata(metadata);

// Export UI helper functions
window.toggleDAWDetailedView = toggleDAWDetailedView;
window.loadDAWDetailedView = loadDAWDetailedView;
window.switchDAWTab = switchDAWTab;
window.exportDAWMetadata = exportDAWMetadata;