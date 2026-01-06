/**
 * File Manager Component
 * Handles file management: manifests, audio files, uploads, runs
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    apiClient
} from '../api/client.js';
import {
    formatBytes,
    getElement
} from '../utils/helpers.js';
import {
    showError
} from './notifications.js';

class FileManager {
    constructor() {
        this.apiBase = API_CONFIG.BASE_URL;
    }

    /**
     * Load manifests
     */
    async loadManifests() {
        try {
            const result = await apiClient.get(API_CONFIG.ENDPOINTS.FILES.MANIFESTS);

            const manifestList = getElement('manifestList');
            const ingestSelect = getElement('ingestManifest');
            const transformSelect = getElement('transformManifest');
            const experimentSelect = getElement('experimentManifest');

            if (manifestList) manifestList.innerHTML = '';

            [ingestSelect, transformSelect, experimentSelect].forEach(select => {
                if (select) select.innerHTML = '<option value="">-- Select Manifest --</option>';
            });

            if (result.manifests && result.manifests.length > 0) {
                result.manifests.forEach(manifest => {
                    if (manifestList) {
                        const li = document.createElement('li');
                        li.innerHTML = `<span>${manifest.name}</span><span>${formatBytes(manifest.size)}</span>`;
                        manifestList.appendChild(li);
                    }

                    [ingestSelect, transformSelect, experimentSelect].forEach(select => {
                        if (select) {
                            const option = document.createElement('option');
                            option.value = manifest.path;
                            option.textContent = manifest.name;
                            select.appendChild(option);
                        }
                    });
                });
            }
        } catch (error) {
            console.error('Failed to load manifests:', error);
        }
    }

    /**
     * Load audio files
     */
    async loadAudioFiles() {
        const directory = getElement('audioDirectory') ? .value;

        try {
            const result = await apiClient.get(`${API_CONFIG.ENDPOINTS.FILES.AUDIO}?directory=${directory}`);

            const fileList = getElement('audioFileList');
            if (!fileList) return;

            fileList.innerHTML = '';

            if (result.files && result.files.length > 0) {
                result.files.forEach(file => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span>${file.name}</span><span>${formatBytes(file.size)}</span>`;
                    fileList.appendChild(li);
                });
            } else {
                fileList.innerHTML = '<li>No files found</li>';
            }
        } catch (error) {
            console.error('Failed to load audio files:', error);
        }
    }

    /**
     * Upload files
     * @param {FileList} files - Files to upload
     */
    async uploadFiles(files) {
        const directory = 'originals';

        for (let file of files) {
            if (!file.type.startsWith('audio/')) {
                showError(`${file.name} is not an audio file`);
                continue;
            }

            try {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('directory', directory);

                const result = await apiClient.upload(API_CONFIG.ENDPOINTS.UPLOAD.AUDIO, formData);

                if (result.status === 'success') {
                    this.loadAudioFiles();
                }
            } catch (error) {
                showError(`Failed to upload ${file.name}: ${error.message}`);
            }
        }
    }

    /**
     * Load runs
     */
    async loadRuns() {
        try {
            const result = await apiClient.get(API_CONFIG.ENDPOINTS.RUNS);
            const runsListDiv = getElement('runsList');

            if (!runsListDiv) return;

            if (result.runs && result.runs.length > 0) {
                runsListDiv.innerHTML = '<table class="table"><thead><tr><th>Run ID</th><th>Date</th><th>Status</th><th>Actions</th></tr></thead><tbody></tbody></table>';
                const tbody = runsListDiv.querySelector('tbody');

                result.runs.forEach(run => {
                    const date = new Date(run.timestamp * 1000).toLocaleString();
                    tbody.innerHTML += `
                        <tr>
                            <td>${run.id}</td>
                            <td>${date}</td>
                            <td><span class="badge badge-${run.has_metrics ? 'success' : 'info'}">${run.has_metrics ? 'Complete' : 'In Progress'}</span></td>
                            <td>
                                <button class="btn" onclick="viewRun('${run.id}')">View</button>
                                ${run.has_summary ? `<button class="btn" onclick="downloadReport('${run.id}')">Download</button>` : ''}
                            </td>
                        </tr>
                    `;
                });
            } else {
                runsListDiv.innerHTML = '<p>No runs found. Run an experiment to see results here.</p>';
            }
        } catch (error) {
            console.error('Failed to load runs:', error);
        }
    }

    /**
     * Handle file drop
     */
    handleDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        const uploadArea = getElement('uploadArea');
        if (uploadArea) uploadArea.classList.remove('dragover');
        this.uploadFiles(event.dataTransfer.files);
    }

    /**
     * Handle drag over
     */
    handleDragOver(event) {
        event.preventDefault();
        const uploadArea = getElement('uploadArea');
        if (uploadArea) uploadArea.classList.add('dragover');
    }

    /**
     * Handle drag leave
     */
    handleDragLeave(event) {
        event.preventDefault();
        const uploadArea = getElement('uploadArea');
        if (uploadArea) uploadArea.classList.remove('dragover');
    }

    /**
     * Handle file select
     */
    handleFileSelect(event) {
        this.uploadFiles(event.target.files);
    }
}

export const fileManager = new FileManager();
export const loadManifests = () => fileManager.loadManifests();
export const loadAudioFiles = () => fileManager.loadAudioFiles();
export const uploadFiles = (files) => fileManager.uploadFiles(files);
export const loadRuns = () => fileManager.loadRuns();
export const handleDrop = (event) => fileManager.handleDrop(event);
export const handleDragOver = (event) => fileManager.handleDragOver(event);
export const handleDragLeave = (event) => fileManager.handleDragLeave(event);
export const handleFileSelect = (event) => fileManager.handleFileSelect(event);