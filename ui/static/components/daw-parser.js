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
                    item.innerHTML = `
                        <div class="daw-file-info">
                            <div class="daw-file-name">${file.name}</div>
                            <div class="daw-file-meta">${file.type.toUpperCase()} • ${formatFileSize(file.size)} • ${new Date(file.modified).toLocaleDateString()}</div>
                        </div>
                        <div>
                            <button class="btn" onclick="parseDAWFile('${file.path}')" style="margin-right: 10px;">Parse</button>
                            <button class="btn" onclick="viewDAWMetadata('${file.path}')">View Metadata</button>
                        </div>
                    `;
                    fileList.appendChild(item);
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

    async parseDAWFile(filePath) {
        try {
            showNotification('Parsing DAW file...', 'info');
            const formData = new FormData();
            formData.append('file_path', filePath);

            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DAW.PARSE}`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                showNotification('DAW file parsed successfully!', 'success');
                this.displayDAWMetadata(result.metadata);
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
                this.displayDAWMetadata(metadata);
            } else {
                await this.parseDAWFile(filePath);
            }
        } catch (error) {
            showError('Error loading DAW metadata: ' + error.message);
        }
    }

    displayDAWMetadata(metadata) {
        const metadataView = getElement('dawMetadataView');
        if (!metadataView) return;

        if (!metadata) {
            metadataView.innerHTML = '<p style="color: #9ca3af; text-align: center; padding: 20px;">No metadata available</p>';
            return;
        }

        let html = '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">';

        html += `<div class="daw-stat-item"><span class="daw-stat-label">DAW Type:</span><span class="daw-stat-value">${metadata.daw_type || 'Unknown'}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Version:</span><span class="daw-stat-value">${metadata.version || 'Unknown'}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">MIDI Tracks:</span><span class="daw-stat-value">${metadata.midi_tracks || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Total Notes:</span><span class="daw-stat-value">${metadata.total_notes || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Arrangement Clips:</span><span class="daw-stat-value">${metadata.arrangement_clips || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Tempo Changes:</span><span class="daw-stat-value">${metadata.tempo_changes || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Plugin Chains:</span><span class="daw-stat-value">${metadata.plugin_chains || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Sample Sources:</span><span class="daw-stat-value">${metadata.sample_sources || 0}</span></div>`;
        html += `<div class="daw-stat-item"><span class="daw-stat-label">Automation Tracks:</span><span class="daw-stat-value">${metadata.automation_tracks || 0}</span></div>`;

        if (metadata.extracted_at) {
            html += `<div class="daw-stat-item"><span class="daw-stat-label">Extracted:</span><span class="daw-stat-value">${new Date(metadata.extracted_at).toLocaleString()}</span></div>`;
        }

        html += '</div>';

        metadataView.innerHTML = html;
    }
}

// Export singleton instance and individual functions
export const dawParserManager = new DAWParserManager();

export const loadDAWFiles = () => dawParserManager.loadDAWFiles();
export const handleDAWDrop = (event) => dawParserManager.handleDAWDrop(event);
export const handleDAWFileSelect = (event) => dawParserManager.handleDAWFileSelect(event);
export const uploadDAWFile = (file) => dawParserManager.uploadDAWFile(file);
export const parseDAWFile = (filePath) => dawParserManager.parseDAWFile(filePath);
export const viewDAWMetadata = (filePath) => dawParserManager.viewDAWMetadata(filePath);
export const displayDAWMetadata = (metadata) => dawParserManager.displayDAWMetadata(metadata);