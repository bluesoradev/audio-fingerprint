// Audio Fingerprint Robustness Lab - Frontend JavaScript

const API_BASE = '/api';
let currentProcessId = null;
let logPollInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    loadDashboard();
    loadManifests();
    loadRuns();
    loadTestMatrix();
    setInterval(checkStatus, 5000); // Check status every 5 seconds
});

// Navigation
function showSection(sectionId, eventElement) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
    
    // Update active nav item
    document.querySelectorAll('.nav-menu a').forEach(a => a.classList.remove('active'));
    if (eventElement) {
        eventElement.classList.add('active');
    } else {
        // Find the corresponding nav link and activate it
        document.querySelectorAll('.nav-menu a').forEach(a => {
            if (a.getAttribute('onclick') && a.getAttribute('onclick').includes(sectionId)) {
                a.classList.add('active');
            }
        });
    }

    // Load section-specific data
    if (sectionId === 'files') {
        loadAudioFiles();
    } else if (sectionId === 'runs') {
        loadRuns();
    } else if (sectionId === 'manipulate') {
        loadManipulateAudioFiles();
        loadTestFileSelects();
    }
}

// Status Check
async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const status = await response.json();
        
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        if (status.running_processes && status.running_processes.length > 0) {
            statusDot.className = 'status-dot warning';
            statusText.textContent = `${status.running_processes.length} process(es) running`;
            document.getElementById('currentProcess').textContent = `Running: ${status.running_processes.join(', ')}`;
        } else {
            statusDot.className = 'status-dot';
            statusText.textContent = 'System Ready';
            document.getElementById('currentProcess').textContent = '';
        }
    } catch (error) {
        console.error('Status check failed:', error);
        document.getElementById('statusDot').className = 'status-dot error';
        document.getElementById('statusText').textContent = 'Connection Error';
    }
}

// Dashboard
async function loadDashboard() {
    try {
        const [statusRes, runsRes] = await Promise.all([
            fetch(`${API_BASE}/status`),
            fetch(`${API_BASE}/runs`)
        ]);
        
        const status = await statusRes.json();
        const runs = await runsRes.json();
        
        // Display stats
        const statsGrid = document.getElementById('dashboardStats');
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
        
        // Recent runs
        const recentRunsDiv = document.getElementById('recentRuns');
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
                        <td><button class="btn" onclick="viewRun('${run.id}')">View</button></td>
                    </tr>
                `;
            });
        } else {
            recentRunsDiv.innerHTML = '<p>No runs yet. Start by creating test audio files.</p>';
        }
    } catch (error) {
        console.error('Dashboard load failed:', error);
    }
}

// Workflow Functions
async function createTestAudio() {
    const numFiles = document.getElementById('numFiles').value;
    const duration = document.getElementById('duration').value;
    const outputDir = document.getElementById('audioOutputDir').value;
    
    if (!numFiles || !duration || !outputDir) {
        showError('Please fill in all fields');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('num_files', numFiles);
        formData.append('duration', duration);
        formData.append('output_dir', outputDir);
        
        const response = await fetch(`${API_BASE}/process/create-test-audio`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        if (result.command_id) {
            startProcessMonitoring(result.command_id, 'Creating test audio files...', 'Create Test Audio');
            addSystemLog(`Started creating test audio: ${numFiles} files, ${duration}s each`, 'info');
        } else {
            showError('No command ID returned from server');
        }
    } catch (error) {
        console.error('Create test audio error:', error);
        showError('Failed to start process: ' + (error.message || 'Unknown error'));
    }
}

async function createManifest() {
    const audioDir = document.getElementById('audioDir').value;
    const output = document.getElementById('manifestOutput').value;
    
    try {
        const formData = new FormData();
        formData.append('audio_dir', audioDir);
        formData.append('output', output);
        
        const response = await fetch(`${API_BASE}/process/create-manifest`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.command_id) {
            startProcessMonitoring(result.command_id, 'Creating manifest...', 'Create Manifest');
            addSystemLog(`Started creating manifest from: ${audioDir}`, 'info');
        }
    } catch (error) {
        showError('Failed to start process: ' + error.message);
    }
}

async function ingestFiles() {
    const manifestPath = document.getElementById('ingestManifest').value;
    const sampleRate = document.getElementById('sampleRate').value;
    
    if (!manifestPath) {
        showError('Please select a manifest file');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('manifest_path', manifestPath);
        formData.append('output_dir', 'data');
        formData.append('sample_rate', sampleRate);
        
        const response = await fetch(`${API_BASE}/process/ingest`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.command_id) {
            startProcessMonitoring(result.command_id, 'Ingesting files...', 'Ingest Files');
            addSystemLog(`Started ingesting files from: ${manifestPath}`, 'info');
        }
    } catch (error) {
        showError('Failed to start process: ' + error.message);
    }
}

async function generateTransforms() {
    const manifestPath = document.getElementById('transformManifest').value;
    
    if (!manifestPath) {
        showError('Please select a manifest file');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('manifest_path', manifestPath);
        formData.append('test_matrix_path', 'config/test_matrix.yaml');
        formData.append('output_dir', 'data');
        
        const response = await fetch(`${API_BASE}/process/generate-transforms`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.command_id) {
            startProcessMonitoring(result.command_id, 'Generating transforms...', 'Generate Transforms');
            addSystemLog(`Started generating transforms from: ${manifestPath}`, 'info');
        }
    } catch (error) {
        showError('Failed to start process: ' + error.message);
    }
}

async function runExperiment() {
    const manifestPath = document.getElementById('experimentManifest').value;
    
    if (!manifestPath) {
        showError('Please select a manifest file');
        return;
    }
    
    if (!confirm('This will run the full experiment pipeline. Continue?')) {
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('config_path', 'config/test_matrix.yaml');
        formData.append('originals_path', manifestPath);
        
        const response = await fetch(`${API_BASE}/process/run-experiment`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.command_id) {
            startProcessMonitoring(result.command_id, 'Running full experiment...', 'Run Experiment');
            addSystemLog(`Started full experiment with manifest: ${manifestPath}`, 'info');
        }
    } catch (error) {
        showError('Failed to start process: ' + error.message);
    }
}

// Process Monitoring
function startProcessMonitoring(commandId, message, processName = 'Process') {
    currentProcessId = commandId;
    showSection('workflow', null);
    
    const logsDiv = document.getElementById('processLogs');
    logsDiv.style.display = 'block';
    logsDiv.innerHTML = `<div class="log-line">${message}</div>`;
    
    // Store process name for alerts
    if (!window.processNames) {
        window.processNames = {};
    }
    window.processNames[commandId] = processName;
    
    // Start polling for logs
    if (logPollInterval) {
        clearInterval(logPollInterval);
    }
    
    logPollInterval = setInterval(async () => {
        await pollLogs(commandId);
        await checkProcessStatus(commandId);
    }, 1000);
    
    // Also add to system logs
    addSystemLog(message, 'info');
}

async function pollLogs(commandId) {
    try {
        const response = await fetch(`${API_BASE}/process/${commandId}/logs`);
        const result = await response.json();
        
        if (result.logs && result.logs.length > 0) {
            const logsDiv = document.getElementById('processLogs');
            result.logs.forEach(log => {
                const line = document.createElement('div');
                line.className = `log-line ${log.type}`;
                line.textContent = log.message;
                logsDiv.appendChild(line);
            });
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }
    } catch (error) {
        console.error('Failed to poll logs:', error);
    }
}

async function checkProcessStatus(commandId) {
    try {
        const response = await fetch(`${API_BASE}/process/${commandId}/status`);
        const status = await response.json();
        
        // Handle different status values
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            if (logPollInterval) {
                clearInterval(logPollInterval);
                logPollInterval = null;
            }
            currentProcessId = null;
            
            // Get process name for alert
            const processName = window.processNames && window.processNames[commandId] ? window.processNames[commandId] : 'Process';
            
            addSystemLog(`Process ${status.status}: ${commandId}`, status.status === 'completed' ? 'success' : 'error');
            
            // Show completion alert
            if (status.status === 'completed') {
                showCompletionAlert(processName + ' completed successfully!');
            } else if (status.status === 'failed') {
                showCompletionAlert(processName + ' failed. Check logs for details.', 'error');
            } else if (status.status === 'cancelled') {
                showCompletionAlert(processName + ' was cancelled.', 'warning');
            }
            
            // Clean up process name
            if (window.processNames && window.processNames[commandId]) {
                delete window.processNames[commandId];
            }
            
            // Refresh dashboard and reload manifests
            loadDashboard();
            loadManifests();
            loadRuns();
            loadAudioFiles(); // Also refresh audio files list
        } else if (status.status === 'not_found') {
            // Process was cleaned up or never existed, stop polling
            if (logPollInterval) {
                clearInterval(logPollInterval);
                logPollInterval = null;
            }
            currentProcessId = null;
        }
        // For 'running' and 'starting' status, continue polling
    } catch (error) {
        console.error('Failed to check status:', error);
        // Don't stop polling on error, might be temporary network issue
    }
}

// File Management
async function loadManifests() {
    try {
        const response = await fetch(`${API_BASE}/files/manifests`);
        const result = await response.json();
        
        const manifestList = document.getElementById('manifestList');
        const ingestSelect = document.getElementById('ingestManifest');
        const transformSelect = document.getElementById('transformManifest');
        const experimentSelect = document.getElementById('experimentManifest');
        
        manifestList.innerHTML = '';
        [ingestSelect, transformSelect, experimentSelect].forEach(select => {
            select.innerHTML = '<option value="">-- Select Manifest --</option>';
        });
        
        if (result.manifests && result.manifests.length > 0) {
            result.manifests.forEach(manifest => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${manifest.name}</span>
                    <span>${formatBytes(manifest.size)}</span>
                `;
                manifestList.appendChild(li);
                
                [ingestSelect, transformSelect, experimentSelect].forEach(select => {
                    const option = document.createElement('option');
                    option.value = manifest.path;
                    option.textContent = manifest.name;
                    select.appendChild(option);
                });
            });
        }
    } catch (error) {
        console.error('Failed to load manifests:', error);
    }
}

async function loadAudioFiles() {
    const directory = document.getElementById('audioDirectory').value;
    
    try {
        const response = await fetch(`${API_BASE}/files/audio?directory=${directory}`);
        const result = await response.json();
        
        const fileList = document.getElementById('audioFileList');
        fileList.innerHTML = '';
        
        if (result.files && result.files.length > 0) {
            result.files.forEach(file => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${file.name}</span>
                    <span>${formatBytes(file.size)}</span>
                `;
                fileList.appendChild(li);
            });
        } else {
            fileList.innerHTML = '<li>No files found</li>';
        }
    } catch (error) {
        console.error('Failed to load audio files:', error);
    }
}

// File Upload
function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('uploadArea').classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    uploadFiles(files);
}

function handleDragOver(event) {
    event.preventDefault();
    document.getElementById('uploadArea').classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    document.getElementById('uploadArea').classList.remove('dragover');
}

function handleFileSelect(event) {
    const files = event.target.files;
    uploadFiles(files);
}

async function uploadFiles(files) {
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
            
            const response = await fetch(`${API_BASE}/upload/audio`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            if (result.status === 'success') {
                addSystemLog(`Uploaded: ${file.name}`, 'success');
                loadAudioFiles();
            }
        } catch (error) {
            showError(`Failed to upload ${file.name}: ${error.message}`);
        }
    }
}

// Results
async function loadRuns() {
    try {
        const response = await fetch(`${API_BASE}/runs`);
        const result = await response.json();
        
        const runsListDiv = document.getElementById('runsList');
        
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

function viewRun(runId) {
    window.open(`/report/${runId}`, '_blank');
}

function downloadReport(runId) {
    window.location.href = `/download/${runId}`;
}

// Configuration
async function loadTestMatrix() {
    try {
        const response = await fetch(`${API_BASE}/config/test-matrix`);
        const config = await response.json();
        
        document.getElementById('testMatrixConfig').value = JSON.stringify(config, null, 2);
    } catch (error) {
        console.error('Failed to load test matrix:', error);
    }
}

async function saveTestMatrix() {
    try {
        const configText = document.getElementById('testMatrixConfig').value;
        const config = JSON.parse(configText);
        
        const response = await fetch(`${API_BASE}/config/test-matrix`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            addSystemLog('Configuration saved successfully', 'success');
        }
    } catch (error) {
        showError('Failed to save configuration: ' + error.message);
    }
}

// Utilities
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function showError(message) {
    alert('Error: ' + message);
    addSystemLog('Error: ' + message, 'error');
}

function showCompletionAlert(message, type = 'success') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#ff9800'};
        color: white;
        padding: 20px 30px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        font-size: 16px;
        font-weight: 500;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    
    alertDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 24px;">${type === 'success' ? '✓' : type === 'error' ? '✗' : '⚠'}</span>
            <span>${message}</span>
        </div>
    `;
    
    // Add animation style if not already added
    if (!document.getElementById('alertAnimationStyle')) {
        const style = document.createElement('style');
        style.id = 'alertAnimationStyle';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 300);
    }, 5000);
    
    // Also show browser alert for important notifications
    if (type === 'success') {
        alert(message); // Browser alert for completion
    }
}

function addSystemLog(message, type = 'info') {
    const logsDiv = document.getElementById('systemLogs');
    const line = document.createElement('div');
    line.className = `log-line ${type}`;
    const timestamp = new Date().toLocaleTimeString();
    line.textContent = `[${timestamp}] ${message}`;
    logsDiv.appendChild(line);
    logsDiv.scrollTop = logsDiv.scrollHeight;
}

// Audio Manipulation Functions
let transformChain = [];
let selectedAudioFile = null;

async function loadManipulateAudioFiles() {
    // Load audio files from all directories
    const directories = ['originals', 'transformed', 'test_audio', 'manipulated'];
    const allFiles = [];
    
    for (const dir of directories) {
        try {
            const response = await fetch(`${API_BASE}/files/audio?directory=${dir}`);
            const result = await response.json();
            if (result.files) {
                allFiles.push(...result.files);
            }
        } catch (error) {
            console.error(`Failed to load files from ${dir}:`, error);
        }
    }
    
    const select = document.getElementById('manipulateAudioFile');
    if (!select) return;
    
    select.innerHTML = '<option value="">-- Select Audio File --</option>';
    
    allFiles.forEach(file => {
        const option = document.createElement('option');
        option.value = file.path;
        option.textContent = `${file.name} (${formatBytes(file.size)})`;
        select.appendChild(option);
    });
}

function loadAudioInfo() {
    const select = document.getElementById('manipulateAudioFile');
    if (!select) return;
    
    const filePath = select.value;
    
    if (!filePath) {
        const audioInfo = document.getElementById('audioInfo');
        if (audioInfo) audioInfo.style.display = 'none';
        selectedAudioFile = null;
        updateTestDisplays(null, null);
        return;
    }
    
    selectedAudioFile = filePath;
    const fileName = select.options[select.selectedIndex].textContent;
    
    const selectedFileName = document.getElementById('selectedFileName');
    const selectedFilePath = document.getElementById('selectedFilePath');
    const audioPreview = document.getElementById('audioPreview');
    const audioInfo = document.getElementById('audioInfo');
    
    if (selectedFileName) selectedFileName.textContent = fileName;
    if (selectedFilePath) selectedFilePath.textContent = filePath;
    if (audioPreview) audioPreview.src = `/api/files/audio-file?path=${encodeURIComponent(filePath)}`;
    if (audioInfo) audioInfo.style.display = 'block';
    
    // Update original test display
    updateTestDisplays(filePath, null);
}

async function applySpeedTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const speedSlider = document.getElementById('speedSlider');
    const speedRatio = parseFloat(speedSlider.value) / 100.0; // Convert from 50-200 to 0.5-2.0
    const preservePitch = document.getElementById('preservePitch').checked;
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('speed_ratio', speedRatio);
        formData.append('preserve_pitch', preservePitch);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/speed`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            // Try to parse error response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.message || errorMessage;
            } catch {
                // If not JSON, get text
                const errorText = await response.text();
                errorMessage = errorText.substring(0, 200); // Limit length
            }
            throw new Error(errorMessage);
        }
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Speed transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            // Update transformed test display
            if (result.output_path) {
                updateTestDisplays(null, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply speed transform: ' + error.message);
    }
}

async function applyPitchTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const semitones = parseInt(document.getElementById('pitchSlider').value);
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('semitones', semitones);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/pitch`, {
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
            showCompletionAlert(result.message);
            addSystemLog(`Pitch transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply pitch transform: ' + error.message);
    }
}

async function applyReverbTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const delayMs = parseInt(document.getElementById('reverbSlider').value);
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('delay_ms', delayMs);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/reverb`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Reverb transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTestDisplays(null, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply reverb transform: ' + error.message);
    }
}

async function applyNoiseReductionTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const reductionPercent = parseInt(document.getElementById('noiseSlider').value);
    const reductionStrength = reductionPercent / 100.0;
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('reduction_strength', reductionStrength);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/noise-reduction`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Noise reduction applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTestDisplays(null, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply noise reduction: ' + error.message);
    }
}

async function applyEQTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const gainDb = parseInt(document.getElementById('eqSlider').value);
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('gain_db', gainDb);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/eq`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`EQ transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTestDisplays(null, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply EQ transform: ' + error.message);
    }
}

async function applyCompressionTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const codec = document.getElementById('codecSelect').value;
    if (codec === 'None') {
        showError('Please select a codec');
        return;
    }
    
    const bitrate = document.getElementById('bitrateSelect').value;
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('codec', codec.toLowerCase());
        formData.append('bitrate', bitrate);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/encode`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Compression applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTestDisplays(null, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply compression: ' + error.message);
    }
}

async function applyOverlayTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const overlayFile = document.getElementById('overlayFile').files[0];
    const gainDb = parseInt(document.getElementById('overlayGainSlider').value);
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('gain_db', gainDb);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        // Upload overlay file if provided
        let overlayPath = null;
        if (overlayFile) {
            const uploadFormData = new FormData();
            uploadFormData.append('file', overlayFile);
            uploadFormData.append('directory', 'data/manipulated');
            
            const uploadResponse = await fetch(`${API_BASE}/upload/audio`, {
                method: 'POST',
                body: uploadFormData
            });
            
            const uploadResult = await uploadResponse.json();
            if (uploadResult.status === 'success') {
                overlayPath = uploadResult.path;
                formData.append('overlay_path', overlayPath);
            }
        }
        
        const response = await fetch(`${API_BASE}/manipulate/overlay`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Overlay transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTestDisplays(null, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply overlay transform: ' + error.message);
    }
}

async function applyNoiseTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    // This is for adding noise, not reducing it
    const snrDb = 20; // Default SNR
    const noiseType = 'white';
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('snr_db', snrDb);
        formData.append('noise_type', noiseType);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/noise`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Noise transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply noise transform: ' + error.message);
    }
}

async function applyEncodeTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const codec = document.getElementById('encodeCodec').value;
    const bitrate = document.getElementById('encodeBitrate').value;
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('codec', codec);
        formData.append('bitrate', bitrate);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/encode`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Encode transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply encode transform: ' + error.message);
    }
}

async function applyChopTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const removeStart = parseFloat(document.getElementById('chopStart').value);
    const removeEnd = parseFloat(document.getElementById('chopEnd').value);
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('remove_start', removeStart);
        formData.append('remove_end', removeEnd);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/chop`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Chop transform applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply chop transform: ' + error.message);
    }
}

function addToChain() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    // Get current transform settings from sliders
    const speedSlider = document.getElementById('speedSlider');
    const speedRatio = parseFloat(speedSlider.value) / 100.0;
    const preservePitch = document.getElementById('preservePitch').checked;
    const pitchSemitones = parseInt(document.getElementById('pitchSlider').value);
    const reverbMs = parseInt(document.getElementById('reverbSlider').value);
    const noisePercent = parseInt(document.getElementById('noiseSlider').value);
    const eqDb = parseInt(document.getElementById('eqSlider').value);
    const codec = document.getElementById('codecSelect').value;
    const bitrate = document.getElementById('bitrateSelect').value;
    const overlayGain = parseInt(document.getElementById('overlayGainSlider').value);
    
    let transformDesc = [];
    let transformParams = {};
    
    if (speedRatio !== 1.0) {
        transformDesc.push(`Speed: ${speedRatio.toFixed(2)}x`);
        transformParams.speed = speedRatio;
        transformParams.preserve_pitch = preservePitch;
    }
    
    if (pitchSemitones !== 0) {
        transformDesc.push(`Pitch: ${pitchSemitones > 0 ? '+' : ''}${pitchSemitones} semitones`);
        transformParams.semitones = pitchSemitones;
    }
    
    if (reverbMs > 0) {
        transformDesc.push(`Reverb: ${reverbMs}ms`);
        transformParams.delay_ms = reverbMs;
    }
    
    if (noisePercent > 0) {
        transformDesc.push(`Noise Reduction: ${noisePercent}%`);
        transformParams.reduction_strength = noisePercent / 100.0;
    }
    
    if (eqDb !== 0) {
        transformDesc.push(`EQ: ${eqDb > 0 ? '+' : ''}${eqDb} dB`);
        transformParams.gain_db = eqDb;
    }
    
    if (codec !== 'None') {
        transformDesc.push(`Compression: ${codec} @ ${bitrate}`);
        transformParams.codec = codec.toLowerCase();
        transformParams.bitrate = bitrate;
    }
    
    if (transformDesc.length === 0) {
        showError('Please configure at least one transform before adding to chain');
        return;
    }
    
    const transform = {
        type: 'combined',
        params: transformParams,
        description: transformDesc.join(', ')
    };
    
    transformChain.push(transform);
    updateChainDisplay();
    addSystemLog(`Added transform to chain: ${transform.description}`, 'info');
}

function clearChain() {
    transformChain = [];
    updateChainDisplay();
    addSystemLog('Transform chain cleared', 'info');
}

function updateChainDisplay() {
    const chainTextarea = document.getElementById('chainList');
    if (!chainTextarea) return;
    
    if (transformChain.length === 0) {
        chainTextarea.value = 'No transforms in chain yet.';
        return;
    }
    
    let chainText = '';
    transformChain.forEach((t, i) => {
        chainText += `${i + 1}. ${t.description || t.type} (${JSON.stringify(t.params)})\n`;
    });
    
    chainTextarea.value = chainText;
}

function removeFromChain(index) {
    transformChain.splice(index, 1);
    updateChainDisplay();
}

async function applyChainTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    if (transformChain.length === 0) {
        showError('Please add transforms to the chain first');
        return;
    }
    
    const outputDir = document.getElementById('manipulateOutputDir').value;
    const outputName = document.getElementById('manipulateOutputName').value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('transforms', JSON.stringify(transformChain));
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        const response = await fetch(`${API_BASE}/manipulate/chain`, {
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
            showCompletionAlert(result.message);
            addSystemLog(`Chain transform applied: ${result.output_path}`, 'success');
            clearChain();
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTestDisplays(null, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply chain transform: ' + error.message);
    }
}

async function loadTestFileSelects() {
    // Load files for fingerprint testing
    // The test displays are updated automatically when files are loaded/transformed
    await loadManipulateAudioFiles();
}

async function testFingerprintRobustness() {
    const originalDisplay = document.getElementById('originalTestDisplay');
    const transformedDisplay = document.getElementById('transformedTestDisplay');
    const originalFile = originalDisplay.value;
    const manipulatedFile = transformedDisplay.value;
    
    if (!originalFile || !manipulatedFile) {
        showError('Please load both original and transformed audio files first');
        return;
    }
    
    if (originalFile === manipulatedFile) {
        showError('Original and transformed files must be different');
        return;
    }
    
    const resultDiv = document.getElementById('testResults');
    const detailsDiv = document.getElementById('testResultsContent');
    const testBtn = document.getElementById('testBtn');
    
    // Show loading state
    resultDiv.style.display = 'block';
    resultDiv.className = 'test-results';
    testBtn.disabled = true;
    detailsDiv.innerHTML = '<p>🔄 Testing fingerprint match... This may take a moment.</p>';
    
    try {
        const formData = new FormData();
        formData.append('original_path', originalFile);
        formData.append('manipulated_path', manipulatedFile);
        
        const response = await fetch(`${API_BASE}/test/fingerprint`, {
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
        
        testBtn.disabled = false;
        
        if (result.status === 'success') {
            const matchStatus = result.matched ? '✓ MATCHED' : '✗ NOT MATCHED';
            const matchClass = result.matched ? 'success' : 'error';
            const similarityPercent = (result.similarity * 100).toFixed(1);
            const directSim = result.direct_similarity ? (result.direct_similarity * 100).toFixed(1) : null;
            
            resultDiv.className = `test-results ${matchClass}`;
            
            let resultText = `${matchStatus}\n\n`;
            resultText += `Similarity Score: ${result.similarity.toFixed(3)} (${similarityPercent}%)\n`;
            if (result.rank) {
                resultText += `Rank: ${result.rank} (position in search results)\n`;
            } else {
                resultText += `Rank: 1 (direct similarity match)\n`;
            }
            resultText += `Top Match: ${result.top_match || 'N/A'}\n\n`;
            
            if (result.similarity > 0.9) {
                resultText += 'Interpretation: Strong match - fingerprint is very robust to this transformation.';
            } else if (result.similarity > 0.7) {
                resultText += 'Interpretation: Good match - fingerprint is robust to this transformation.';
            } else if (result.matched) {
                resultText += 'Interpretation: Moderate match - transformation affects fingerprint but still identifiable.';
            } else {
                resultText += 'Interpretation: Fingerprint could not match transformed audio to original. This transformation may break fingerprint identification.';
            }
            
            detailsDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">${resultText}</pre>`;
            
            addSystemLog(`Fingerprint test: ${matchStatus} (${similarityPercent}% similarity)`, result.matched ? 'success' : 'warning');
        } else {
            resultDiv.className = 'test-results error';
            detailsDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">Error: ${result.message || 'Test failed'}</pre>`;
        }
    } catch (error) {
        testBtn.disabled = false;
        resultDiv.className = 'test-results error';
        detailsDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">Error testing fingerprint: ${error.message}\n\nPlease ensure:\n1. Fingerprint model is properly configured\n2. Audio files are valid and accessible\n3. Required dependencies are installed</pre>`;
    }
}

// Update test displays when files are loaded
function updateTestDisplays(originalPath, transformedPath) {
    const originalDisplay = document.getElementById('originalTestDisplay');
    const transformedDisplay = document.getElementById('transformedTestDisplay');
    const testBtn = document.getElementById('testBtn');
    
    if (originalDisplay && originalPath) {
        originalDisplay.value = originalPath;
        originalDisplay.style.color = '#4ade80';
    } else if (originalDisplay && !originalPath) {
        originalDisplay.value = '';
        originalDisplay.style.color = '#9ca3af';
    }
    
    if (transformedDisplay && transformedPath) {
        transformedDisplay.value = transformedPath;
        transformedDisplay.style.color = '#4ade80';
    } else if (transformedDisplay && !transformedPath) {
        transformedDisplay.value = '';
        transformedDisplay.style.color = '#9ca3af';
    }
    
    // Enable test button if both files are available
    if (testBtn) {
        const hasOriginal = originalDisplay && originalDisplay.value;
        const hasTransformed = transformedDisplay && transformedDisplay.value;
        testBtn.disabled = !(hasOriginal && hasTransformed);
    }
}
