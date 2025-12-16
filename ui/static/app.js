// Audio Fingerprint Robustness Lab - Frontend JavaScript

const API_BASE = '/api';
let currentProcessId = null;
let logPollInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Show/hide transform params groups based on transform selection
    const embeddedApplyTransform = document.getElementById('embeddedApplyTransform');
    const embeddedTransformParamsGroup = document.getElementById('embeddedTransformParamsGroup');
    if (embeddedApplyTransform && embeddedTransformParamsGroup) {
        embeddedApplyTransform.addEventListener('change', function() {
            embeddedTransformParamsGroup.style.display = this.value !== 'None' ? 'block' : 'none';
        });
    }
    
    const songAApplyTransform = document.getElementById('songAApplyTransform');
    const songATransformParamsGroup = document.getElementById('songATransformParamsGroup');
    if (songAApplyTransform && songATransformParamsGroup) {
        songAApplyTransform.addEventListener('change', function() {
            songATransformParamsGroup.style.display = this.value !== 'None' ? 'block' : 'none';
        });
    }
    // Initialize test button state
    const originalDisplay = document.getElementById('originalTestDisplay');
    const transformedDisplay = document.getElementById('transformedTestDisplay');
    const testBtn = document.getElementById('testBtn');
    
    if (testBtn && originalDisplay && transformedDisplay) {
        // Check initial state and update button
        const hasOriginal = originalDisplay.value && originalDisplay.value.trim() !== '';
        const hasTransformed = transformedDisplay.value && transformedDisplay.value.trim() !== '';
        testBtn.disabled = !(hasOriginal && hasTransformed);
    }
    
    // Initialize progress indicators
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const overallCircle = document.querySelector('.progress-circle-fill.overall');
    const stepCircle = document.querySelector('.progress-circle-fill.step');
    
    if (overallCircle) {
        overallCircle.style.strokeDasharray = `${circumference} ${circumference}`;
        overallCircle.style.strokeDashoffset = circumference;
        overallCircle.classList.add('pending');
    }
    if (stepCircle) {
        stepCircle.style.strokeDasharray = `${circumference} ${circumference}`;
        stepCircle.style.strokeDashoffset = circumference;
        stepCircle.classList.add('pending');
    }
    
    checkStatus();
    loadDashboard();
    loadDeliverablesAudioFiles(); // Load deliverables audio files on page load
    loadDeliverables(); // Load deliverables on page load
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
    if (sectionId === 'manipulate') {
        loadManipulateAudioFiles();
        loadTestFileSelects();
    } else if (sectionId === 'deliverables') {
        loadDeliverables();
        loadDeliverablesAudioFiles();
    }
}

// Status Check
async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const status = await response.json();
        
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const sidebarStatusText = document.getElementById('sidebarStatusText');
        
        if (status.running_processes && status.running_processes.length > 0) {
            statusDot.className = 'status-dot warning';
            statusText.textContent = `${status.running_processes.length} process(es) running`;
            if (sidebarStatusText) {
                sidebarStatusText.textContent = `${status.running_processes.length} process(es) running`;
            }
            document.getElementById('currentProcess').textContent = `Running: ${status.running_processes.join(', ')}`;
        } else {
            statusDot.className = 'status-dot';
            statusText.textContent = 'System Ready';
            if (sidebarStatusText) {
                sidebarStatusText.textContent = 'System Ready';
            }
            document.getElementById('currentProcess').textContent = '';
        }
    } catch (error) {
        console.error('Status check failed:', error);
        document.getElementById('statusDot').className = 'status-dot error';
        document.getElementById('statusText').textContent = 'Connection Error';
        const sidebarStatusText = document.getElementById('sidebarStatusText');
        if (sidebarStatusText) {
            sidebarStatusText.textContent = 'Connection Error';
        }
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
                        <td>
                            <button class="btn" onclick="viewRun('${run.id}')" style="margin-right: 8px;">View</button>
                            <button class="btn" onclick="deleteReport('${run.id}')" style="background: #f87171; color: #ffffff;" title="Delete Report">🗑️ Delete</button>
                        </td>
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
    showSection('logs', null);
    
    const logsDiv = document.getElementById('systemLogs');
    if (logsDiv) {
    logsDiv.innerHTML = `<div class="log-line">${message}</div>`;
    }
    
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
            const logsDiv = document.getElementById('systemLogs');
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
        
        if (manifestList) {
        manifestList.innerHTML = '';
        }
        
        [ingestSelect, transformSelect, experimentSelect].forEach(select => {
            if (select) {
            select.innerHTML = '<option value="">-- Select Manifest --</option>';
            }
        });
        
        if (result.manifests && result.manifests.length > 0) {
            result.manifests.forEach(manifest => {
                if (manifestList) {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${manifest.name}</span>
                    <span>${formatBytes(manifest.size)}</span>
                `;
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
    // Logs section removed - function kept for compatibility but does nothing
    return;
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
    
    // Also populate embedded sample and song A in Song B selectors
    const embeddedBackgroundSelect = document.getElementById('embeddedBackgroundFile');
    const songBBaseSelect = document.getElementById('songBBaseFile');
    
    if (embeddedBackgroundSelect) {
        embeddedBackgroundSelect.innerHTML = '<option value="">-- Select Background File --</option>';
    }
    if (songBBaseSelect) {
        songBBaseSelect.innerHTML = '<option value="">-- Generate Synthetic Background --</option>';
    }
    
    allFiles.forEach(file => {
        const option = document.createElement('option');
        option.value = file.path;
        option.textContent = `${file.name} (${formatBytes(file.size)})`;
        select.appendChild(option);
        
        // Also add to embedded sample and song B selectors
        if (embeddedBackgroundSelect) {
            const opt1 = option.cloneNode(true);
            embeddedBackgroundSelect.appendChild(opt1);
        }
        if (songBBaseSelect) {
            const opt2 = option.cloneNode(true);
            songBBaseSelect.appendChild(opt2);
        }
    });
    
    // Update displays when selected file changes
    if (select) {
        select.addEventListener('change', function() {
            const filePath = this.value;
            if (filePath) {
                const fileName = filePath.split('/').pop();
                const embeddedDisplay = document.getElementById('embeddedSampleFileDisplay');
                const songADisplay = document.getElementById('songAFileDisplay');
                if (embeddedDisplay) embeddedDisplay.textContent = fileName;
                if (songADisplay) songADisplay.textContent = fileName;
            }
        });
    }
}

// Audio player state
let originalAudioPlaying = false;
let transformedAudioPlaying = false;

function loadAudioInfo() {
    const select = document.getElementById('manipulateAudioFile');
    if (!select) {
        console.error('[loadAudioInfo] manipulateAudioFile select not found!');
        return;
    }
    
    const filePath = select.value;
    console.log('[loadAudioInfo] Selected file path:', filePath);
    
    if (!filePath) {
        const audioInfo = document.getElementById('audioInfo');
        if (audioInfo) audioInfo.style.display = 'none';
        selectedAudioFile = null;
        updateTestDisplays(null, null);
        updateOriginalPlayer(null);
        console.log('[loadAudioInfo] No file selected, cleared displays');
        return;
    }
    
    selectedAudioFile = filePath;
    const fileName = select.options[select.selectedIndex]?.textContent || filePath.split('/').pop();
    
    const selectedFileName = document.getElementById('selectedFileName');
    const selectedFilePath = document.getElementById('selectedFilePath');
    const audioInfo = document.getElementById('audioInfo');
    
    if (selectedFileName) selectedFileName.textContent = fileName;
    if (selectedFilePath) selectedFilePath.textContent = filePath;
    if (audioInfo) audioInfo.style.display = 'block';
    
    console.log('[loadAudioInfo] Updated audio info display with:', fileName);
    
    // Update original audio player
    updateOriginalPlayer(filePath);
    
    // Update original test display in "Test Fingerprint Robustness" section
    // Preserve existing transformed path if it exists
    const transformedDisplay = document.getElementById('transformedTestDisplay');
    const existingTransformed = transformedDisplay?.value?.trim() || null;
    console.log('[loadAudioInfo] Updating test displays - Original:', filePath, 'Transformed (preserved):', existingTransformed);
    updateTestDisplays(filePath, existingTransformed);
    
    console.log('[loadAudioInfo] ✅ Original audio set in Test Fingerprint Robustness section');
}

function clearAudioSelection() {
    const select = document.getElementById('manipulateAudioFile');
    if (select) {
        select.value = '';
        loadAudioInfo();
    }
}

function updateOverlayFileName() {
    const fileInput = document.getElementById('overlayFile');
    const fileNameDisplay = document.getElementById('overlayFileName');
    if (fileInput && fileNameDisplay) {
        if (fileInput.files && fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
        } else {
            fileNameDisplay.textContent = 'No file chosen';
        }
    }
}

function updateDeliverablesOverlayFileName() {
    const fileInput = document.getElementById('deliverablesOverlayFile');
    const fileNameDisplay = document.getElementById('deliverablesOverlayFileName');
    if (fileInput && fileNameDisplay) {
        if (fileInput.files && fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
        } else {
            fileNameDisplay.textContent = 'No file chosen';
        }
    }
}

function generateWaveform(container, filePath) {
    // Simple waveform visualization - can be enhanced later
    if (!container) return;
    
    const bars = [];
    for (let i = 0; i < 50; i++) {
        const height = Math.random() * 60 + 20;
        bars.push(`<div class="waveform-bar" style="height: ${height}%;"></div>`);
    }
    container.innerHTML = `<div class="waveform-bars">${bars.join('')}</div>`;
}

function updateOriginalPlayer(filePath) {
    const player = document.getElementById('originalAudioPlayer');
    const playBtn = document.getElementById('originalPlayBtn');
    const infoDiv = document.getElementById('originalPlayerInfo');
    const waveformDiv = document.getElementById('originalWaveform');
    const testStatus = document.getElementById('originalTestStatus');
    
    if (!filePath) {
        if (player) {
            player.src = '';
            player.pause();
            player.onpause = null;
            player.onended = null;
        }
        if (playBtn) {
            playBtn.textContent = '▶';
            playBtn.disabled = true;
        }
        if (infoDiv) {
            infoDiv.textContent = 'No audio loaded.';
        }
        if (waveformDiv) {
            waveformDiv.innerHTML = '<div class="waveform-placeholder">🎤</div>';
        }
        if (testStatus) {
            testStatus.textContent = 'No original audio selected.';
        }
        originalAudioPlaying = false;
        return;
    }
    
    if (player) {
        player.src = `/api/files/audio-file?path=${encodeURIComponent(filePath)}`;
        player.load();
        player.onpause = () => {
            if (playBtn) playBtn.textContent = '▶';
            originalAudioPlaying = false;
        };
        player.onended = () => {
            if (playBtn) playBtn.textContent = '▶';
            originalAudioPlaying = false;
        };
    }
    if (playBtn) {
        playBtn.disabled = false;
        playBtn.textContent = '▶';
    }
    if (infoDiv) {
        const fileName = filePath.split('/').pop();
        infoDiv.textContent = `Loaded: ${fileName}`;
    }
    if (waveformDiv) {
        generateWaveform(waveformDiv, filePath);
    }
    if (testStatus) {
        testStatus.textContent = filePath.split('/').pop();
    }
    originalAudioPlaying = false;
}

function updateTransformedPlayer(filePath) {
    console.log('[updateTransformedPlayer] Called with filePath:', filePath);
    
    const player = document.getElementById('transformedAudioPlayer');
    const playBtn = document.getElementById('transformedPlayBtn');
    const infoDiv = document.getElementById('transformedPlayerInfo');
    const waveformDiv = document.getElementById('transformedWaveform');
    const testStatus = document.getElementById('transformedTestStatus');
    
    if (!filePath) {
        console.log('[updateTransformedPlayer] No filePath provided, clearing player');
        if (player) {
            player.src = '';
            player.pause();
            player.onpause = null;
            player.onended = null;
        }
        if (playBtn) {
            playBtn.textContent = '▶';
            playBtn.disabled = true;
        }
        if (infoDiv) {
            infoDiv.textContent = 'No transformed audio available.';
        }
        if (waveformDiv) {
            waveformDiv.innerHTML = '<div class="waveform-placeholder" style="display: flex; align-items: center; justify-content: center; height: 100%;"><div style="width: 100%; height: 2px; background: #3d3d3d;"></div></div>';
        }
        if (testStatus) {
            testStatus.textContent = 'No transformed audio available. Apply transforms first.';
        }
        transformedAudioPlaying = false;
        return;
    }
    
    if (!player) {
        console.error('[updateTransformedPlayer] Player element not found!');
        return;
    }
    
    const audioUrl = `/api/files/audio-file?path=${encodeURIComponent(filePath)}`;
    console.log('[updateTransformedPlayer] Setting audio src to:', audioUrl);
    
    player.src = audioUrl;
    
    // Add error handler to catch loading issues
    player.onerror = (e) => {
        console.error('[updateTransformedPlayer] Audio loading error:', e);
        console.error('[updateTransformedPlayer] Failed to load:', audioUrl);
        if (infoDiv) {
            infoDiv.innerHTML = `<p style="color: #f87171; font-size: 12px; margin: 0;">Error loading: ${filePath.split('/').pop()}</p>`;
        }
    };
    
    player.onloadeddata = () => {
        console.log('[updateTransformedPlayer] Audio loaded successfully:', audioUrl);
        console.log('[updateTransformedPlayer] Audio duration:', player.duration);
    };
    
    player.oncanplay = () => {
        console.log('[updateTransformedPlayer] Audio can play:', audioUrl);
    };
    
    player.onloadstart = () => {
        console.log('[updateTransformedPlayer] Audio loading started:', audioUrl);
    };
    
    player.load();
    player.onpause = () => {
        if (playBtn) playBtn.textContent = '▶';
        transformedAudioPlaying = false;
    };
    player.onended = () => {
        if (playBtn) playBtn.textContent = '▶';
        transformedAudioPlaying = false;
    };
    
    if (playBtn) {
        playBtn.disabled = false;
        playBtn.textContent = '▶';
    }
    if (infoDiv) {
        const fileName = filePath.split('/').pop();
        infoDiv.textContent = `Loaded: ${fileName}`;
        console.log('[updateTransformedPlayer] Updated info display with:', fileName);
    }
    if (waveformDiv) {
        generateWaveform(waveformDiv, filePath);
    }
    if (testStatus) {
        testStatus.textContent = filePath.split('/').pop();
    }
    transformedAudioPlaying = false;
}

function toggleOriginalPlayback() {
    const player = document.getElementById('originalAudioPlayer');
    const playBtn = document.getElementById('originalPlayBtn');
    
    if (!player || !playBtn || !player.src) return;
    
    if (originalAudioPlaying) {
        player.pause();
        playBtn.textContent = '▶';
        originalAudioPlaying = false;
    } else {
        // Pause transformed if playing
        const transformedPlayer = document.getElementById('transformedAudioPlayer');
        if (transformedAudioPlaying && transformedPlayer) {
            transformedPlayer.pause();
            const transformedBtn = document.getElementById('transformedPlayBtn');
            if (transformedBtn) transformedBtn.textContent = '▶';
            transformedAudioPlaying = false;
        }
        player.play().catch(err => {
            console.error('Error playing audio:', err);
            showError('Error playing audio: ' + err.message);
        });
        playBtn.textContent = '⏸';
        originalAudioPlaying = true;
    }
}

function toggleTransformedPlayback() {
    const player = document.getElementById('transformedAudioPlayer');
    const playBtn = document.getElementById('transformedPlayBtn');
    
    if (!player || !playBtn || !player.src) return;
    
    if (transformedAudioPlaying) {
        player.pause();
        playBtn.textContent = '▶';
        transformedAudioPlaying = false;
    } else {
        // Pause original if playing
        const originalPlayer = document.getElementById('originalAudioPlayer');
        if (originalAudioPlaying && originalPlayer) {
            originalPlayer.pause();
            const originalBtn = document.getElementById('originalPlayBtn');
            if (originalBtn) originalBtn.textContent = '▶';
            originalAudioPlaying = false;
        }
        player.play().catch(err => {
            console.error('Error playing audio:', err);
            showError('Error playing audio: ' + err.message);
        });
        playBtn.textContent = '⏸';
        transformedAudioPlaying = true;
    }
}

function updateOriginalTime() {
    const player = document.getElementById('originalAudioPlayer');
    const label = document.getElementById('originalTimeLabel');
    const playBtn = document.getElementById('originalPlayBtn');
    
    if (!player || !label) return;
    
    if (player.ended) {
        if (playBtn) playBtn.textContent = '▶';
        originalAudioPlaying = false;
    }
    
    const current = formatTime(player.currentTime);
    const duration = formatTime(player.duration || 0);
    label.textContent = `${current} / ${duration}`;
}

function updateTransformedTime() {
    const player = document.getElementById('transformedAudioPlayer');
    const label = document.getElementById('transformedTimeLabel');
    const playBtn = document.getElementById('transformedPlayBtn');
    
    if (!player || !label) return;
    
    if (player.ended) {
        if (playBtn) playBtn.textContent = '▶';
        transformedAudioPlaying = false;
    }
    
    const current = formatTime(player.currentTime);
    const duration = formatTime(player.duration || 0);
    label.textContent = `${current} / ${duration}`;
}

function updateOriginalDuration() {
    updateOriginalTime();
}

function updateTransformedDuration() {
    updateTransformedTime();
}

function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

// Handle file upload in manipulate section
function handleManipulateDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    const uploadArea = document.getElementById('manipulateUploadArea');
    if (uploadArea) uploadArea.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        handleManipulateFileUpload(files[0]);
    }
}

function handleManipulateFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        handleManipulateFileUpload(files[0]);
    }
}

async function handleManipulateFileUpload(file) {
    if (!file.type.startsWith('audio/')) {
        showError('Please select an audio file');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('directory', 'data/originals');
        
        const response = await fetch(`${API_BASE}/upload/audio`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(`File uploaded: ${result.path}`);
            addSystemLog(`Audio file uploaded: ${result.path}`, 'success');
            
            // Reload file list and select the uploaded file
            await loadManipulateAudioFiles();
            const select = document.getElementById('manipulateAudioFile');
            if (select) {
                select.value = result.path;
                loadAudioInfo();
            }
        } else {
            showError(result.message || 'Upload failed');
        }
    } catch (error) {
        showError('Failed to upload file: ' + error.message);
    }
}

async function applySpeedTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const speedSlider = document.getElementById('speedSlider');
    if (!speedSlider) {
        showError('Speed slider not found');
        return;
    }
    const speedRatio = parseFloat(speedSlider.value) / 100.0; // Convert from 50-200 to 0.5-2.0
    const preservePitch = document.getElementById('preservePitch')?.checked || false;
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
            // Update transformed test display and player - preserve original path
            if (result.output_path) {
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
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
    
    const pitchSlider = document.getElementById('pitchSlider');
    if (!pitchSlider) {
        showError('Pitch slider not found');
        return;
    }
    const semitones = parseInt(pitchSlider.value);
    console.log('[Pitch Transform] Slider value:', pitchSlider.value, 'Parsed semitones:', semitones);
    addSystemLog(`Applying pitch shift: ${semitones} semitones`, 'info');
    
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('semitones', semitones);
        formData.append('output_dir', outputDir);
        if (outputName) formData.append('output_name', outputName);
        
        console.log('[Pitch Transform] Sending request:', {
            input_path: selectedAudioFile,
            semitones: semitones,
            output_dir: outputDir,
            output_name: outputName
        });
        
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
        console.log('[Pitch Transform] Response:', result);
        
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Pitch transform applied: ${result.output_path} (${semitones} semitones)`, 'success');
            console.log('[Pitch Transform] Success! Output file:', result.output_path);
            loadManipulateAudioFiles();
            loadTestFileSelects();
            // Update transformed test display and player - preserve original path
            if (result.output_path) {
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
            }
        } else {
            console.error('[Pitch Transform] Failed:', result.message);
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        console.error('[Pitch Transform] Error:', error);
        addSystemLog(`Pitch transform error: ${error.message}`, 'error');
        showError('Failed to apply pitch transform: ' + error.message);
    }
}

async function applyReverbTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const reverbSlider = document.getElementById('reverbSlider');
    if (!reverbSlider) {
        showError('Reverb slider not found');
        return;
    }
    const delayMs = parseInt(reverbSlider.value);
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
            // Update transformed test display and player - preserve original path
            if (result.output_path) {
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
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
    
    const noiseSlider = document.getElementById('noiseSlider');
    if (!noiseSlider) {
        showError('Noise slider not found');
        return;
    }
    const reductionPercent = parseInt(noiseSlider.value);
    const reductionStrength = reductionPercent / 100.0;
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
        console.log('[Noise Reduction] Full response:', JSON.stringify(result, null, 2));
        
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Noise reduction applied: ${result.output_path}`, 'success');
            console.log('[Noise Reduction] Success! Output file:', result.output_path);
            console.log('[Noise Reduction] Output path type:', typeof result.output_path);
            
            loadManipulateAudioFiles();
            loadTestFileSelects();
            
            // Update transformed test display and player
            if (result.output_path) {
                console.log('[Noise Reduction] Calling updateTestDisplays with:', result.output_path);
                console.log('[Noise Reduction] Calling updateTransformedPlayer with:', result.output_path);
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
            } else {
                console.error('[Noise Reduction] No output_path in response:', result);
                showError('Transform succeeded but no output path returned');
            }
        } else {
            console.error('[Noise Reduction] Failed:', result.message);
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        console.error('[Noise Reduction] Error:', error);
        addSystemLog(`Noise reduction error: ${error.message}`, 'error');
        showError('Failed to apply noise reduction: ' + error.message);
    }
}

async function applyEQTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const eqSlider = document.getElementById('eqSlider');
    if (!eqSlider) {
        showError('EQ slider not found');
        return;
    }
    const gainDb = parseInt(eqSlider.value);
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
        console.log('[EQ Transform] Full response:', JSON.stringify(result, null, 2));
        
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`EQ transform applied: ${result.output_path}`, 'success');
            console.log('[EQ Transform] Success! Output file:', result.output_path);
            console.log('[EQ Transform] Output path type:', typeof result.output_path);
            
            loadManipulateAudioFiles();
            loadTestFileSelects();
            
            // Update transformed test display and player
            if (result.output_path) {
                console.log('[EQ Transform] Calling updateTestDisplays with:', result.output_path);
                console.log('[EQ Transform] Calling updateTransformedPlayer with:', result.output_path);
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
            } else {
                console.error('[EQ Transform] No output_path in response:', result);
                showError('Transform succeeded but no output path returned');
            }
        } else {
            console.error('[EQ Transform] Failed:', result.message);
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        console.error('[EQ Transform] Error:', error);
        addSystemLog(`EQ transform error: ${error.message}`, 'error');
        showError('Failed to apply EQ transform: ' + error.message);
    }
}

async function applyCompressionTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const codecSelect = document.getElementById('codecSelect');
    if (!codecSelect) {
        showError('Codec select not found');
        return;
    }
    const codec = codecSelect.value;
    if (codec === 'None') {
        showError('Please select a codec');
        return;
    }
    
    const bitrateSelect = document.getElementById('bitrateSelect');
    if (!bitrateSelect) {
        showError('Bitrate select not found');
        return;
    }
    const bitrate = bitrateSelect.value;
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
            // Update transformed test display and player - preserve original path
            if (result.output_path) {
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
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
    
    const overlayFileInput = document.getElementById('overlayFile');
    const overlayFile = overlayFileInput?.files?.[0] || null;
    
    const overlayGainSlider = document.getElementById('overlayGainSlider');
    if (!overlayGainSlider) {
        showError('Overlay gain slider not found');
        return;
    }
    const gainDb = parseInt(overlayGainSlider.value);
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
            // Update transformed test display and player - preserve original path
            if (result.output_path) {
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
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
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
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
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
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
    
    const outputDir = document.getElementById('manipulateOutputDir')?.value || 'data/manipulated';
    const outputName = document.getElementById('manipulateOutputName')?.value || null;
    
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
            // Update transformed test display - preserve original path
            if (result.output_path) {
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
                updateTransformedPlayer(result.output_path);
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
            resultDiv.style.display = 'block';
            
            let interpretation = '';
            if (result.similarity > 0.9) {
                interpretation = 'Strong match - fingerprint is very robust to this transformation.';
            } else if (result.similarity > 0.7) {
                interpretation = 'Good match - fingerprint is robust to this transformation.';
            } else if (result.matched) {
                interpretation = 'Moderate match - transformation affects fingerprint but still identifiable.';
            } else {
                interpretation = 'Fingerprint could not match transformed audio to original. This transformation may break fingerprint identification.';
            }
            
            detailsDiv.innerHTML = `
                <div style="margin-bottom: 15px;">
                    <h4 style="color: ${result.matched ? '#10b981' : '#f87171'}; margin: 0 0 10px 0;">${matchStatus}</h4>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 15px;">
                    <div>
                        <p style="color: #9ca3af; font-size: 12px; margin: 0 0 5px 0;">Similarity Score</p>
                        <p style="font-size: 24px; color: ${result.matched ? '#10b981' : '#f87171'}; margin: 0; font-weight: bold;">
                            ${similarityPercent}%
                        </p>
                        <p style="font-size: 12px; color: #9ca3af; margin: 5px 0 0 0;">${result.similarity.toFixed(3)}</p>
                    </div>
                    <div>
                        <p style="color: #9ca3af; font-size: 12px; margin: 0 0 5px 0;">Rank</p>
                        <p style="font-size: 20px; color: #ffffff; margin: 0; font-weight: bold;">
                            ${result.rank || '1'}
                        </p>
                        <p style="font-size: 12px; color: #9ca3af; margin: 5px 0 0 0;">${result.rank ? 'Position in search results' : 'Direct match'}</p>
                    </div>
                </div>
                ${result.top_match ? `
                <div style="margin-bottom: 15px; padding: 10px; background: #1e1e1e; border-radius: 4px; border: 1px solid #3d3d3d;">
                    <p style="color: #9ca3af; font-size: 12px; margin: 0 0 5px 0;">Top Match</p>
                    <p style="color: #ffffff; font-size: 14px; margin: 0; word-break: break-all;">${result.top_match}</p>
                </div>
                ` : ''}
                <div style="padding: 15px; background: ${result.matched ? '#1e3a2e' : '#3a1e1e'}; border-radius: 4px; border: 1px solid ${result.matched ? '#10b981' : '#f87171'};">
                    <p style="color: ${result.matched ? '#10b981' : '#f87171'}; font-size: 14px; margin: 0; font-weight: 500;">
                        ${result.matched ? '✅' : '❌'} ${interpretation}
                    </p>
                </div>
            `;
            
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

// Main transform router function
async function applyTransform(type) {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    switch(type) {
        case 'speed':
            await applySpeedTransform();
            break;
        case 'pitch':
            await applyPitchTransform();
            break;
        case 'reverb':
            await applyReverbTransform();
            break;
        case 'noise':
            await applyNoiseReductionTransform();
            break;
        case 'eq':
            await applyEQTransform();
            break;
        case 'compression':
            await applyCompressionTransform();
            break;
        case 'overlay':
            await applyOverlayTransform();
            break;
        case 'highpass':
            await applyHighpassTransform();
            break;
        case 'lowpass':
            await applyLowpassTransform();
            break;
        case 'boostHighs':
            await applyBoostHighsTransform();
            break;
        case 'boostLows':
            await applyBoostLowsTransform();
            break;
        case 'telephone':
            await applyTelephoneTransform();
            break;
        case 'limiting':
            await applyLimitingTransform();
            break;
        case 'multiband':
            await applyMultibandTransform();
            break;
        case 'addNoise':
            await applyAddNoiseTransform();
            break;
        case 'crop':
            await applyCropTransform();
            break;
        case 'embeddedSample':
            await applyEmbeddedSampleTransform();
            break;
        case 'songAInSongB':
            await applySongAInSongBTransform();
            break;
        default:
            showError(`Unknown transform type: ${type}`);
    }
}

// Update slider display values
function updateSliderDisplay(type, value) {
    let displayElement;
    
    // Map type to actual element ID
    switch(type) {
        case 'highpass':
            displayElement = document.getElementById('highpassDisplay');
            if (displayElement) displayElement.textContent = value + ' Hz';
            break;
        case 'lowpass':
            displayElement = document.getElementById('lowpassDisplay');
            if (displayElement) displayElement.textContent = value + ' Hz';
            break;
        case 'boostHighs':
            displayElement = document.getElementById('boostHighsDisplay');
            if (displayElement) displayElement.textContent = value + ' dB';
            break;
        case 'boostLows':
            displayElement = document.getElementById('boostLowsDisplay');
            if (displayElement) displayElement.textContent = value + ' dB';
            break;
        case 'limiting':
            displayElement = document.getElementById('limitingDisplay');
            if (displayElement) displayElement.textContent = value + ' dB';
            break;
        case 'noiseSNR':
            displayElement = document.getElementById('noiseSNRDisplay');
            if (displayElement) displayElement.textContent = value + ' dB';
            break;
        default:
            // Try generic pattern
            displayElement = document.getElementById(`${type}Display`);
            if (displayElement) {
                if (type === 'speed') {
                    displayElement.textContent = (parseFloat(value) / 100).toFixed(2) + 'x';
                } else if (type === 'pitch') {
                    displayElement.textContent = value + ' semitones';
                } else if (type === 'reverb') {
                    displayElement.textContent = value + ' ms';
                } else if (type === 'noise') {
                    displayElement.textContent = value + '%';
                } else if (type === 'eq') {
                    displayElement.textContent = value == 0 ? '0 dB' : (value > 0 ? '+' : '') + value + ' dB';
                } else if (type === 'overlay') {
                    displayElement.textContent = value + ' dB';
                }
            }
            break;
    }
}

// High-Pass Filter Transform
async function applyHighpassTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const freqHz = parseFloat(document.getElementById('highpassSlider')?.value || 150);
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('freq_hz', freqHz);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/eq/highpass`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`High-pass filter applied: ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply high-pass filter: ' + error.message);
    }
}

// Low-Pass Filter Transform
async function applyLowpassTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const freqHz = parseFloat(document.getElementById('lowpassSlider')?.value || 6000);
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('freq_hz', freqHz);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/eq/lowpass`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Low-pass filter applied: ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply low-pass filter: ' + error.message);
    }
}

// Boost Highs Transform
async function applyBoostHighsTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const gainDb = parseFloat(document.getElementById('boostHighsSlider')?.value || 6);
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('gain_db', gainDb);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/eq/boost-highs`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Boost highs applied: ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply boost highs: ' + error.message);
    }
}

// Boost Lows Transform
async function applyBoostLowsTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const gainDb = parseFloat(document.getElementById('boostLowsSlider')?.value || 6);
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('gain_db', gainDb);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/eq/boost-lows`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Boost lows applied: ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply boost lows: ' + error.message);
    }
}

// Telephone Filter Transform
async function applyTelephoneTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/eq/telephone`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Telephone filter applied: ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply telephone filter: ' + error.message);
    }
}

// Limiting Transform
async function applyLimitingTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const ceilingDb = parseFloat(document.getElementById('limitingSlider')?.value || -1);
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('ceiling_db', ceilingDb);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/dynamics/limiting`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Limiting applied: ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply limiting: ' + error.message);
    }
}

// Multiband Compression Transform
async function applyMultibandTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/dynamics/multiband`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Multiband compression applied: ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply multiband compression: ' + error.message);
    }
}

// Add Noise Transform
async function applyAddNoiseTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const noiseType = document.getElementById('noiseTypeSelect')?.value || 'white';
    const snrDb = parseFloat(document.getElementById('noiseSNRSlider')?.value || 20);
    
    try {
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('noise_type', noiseType);
        formData.append('snr_db', snrDb);
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/noise`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Noise added (${noiseType}): ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to add noise: ' + error.message);
    }
}

// Crop Transform
async function applyCropTransform() {
    if (!selectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const cropType = document.getElementById('cropTypeSelect')?.value || '10s';
    
    try {
        let endpoint = '';
        const formData = new FormData();
        formData.append('input_path', selectedAudioFile);
        formData.append('output_dir', 'data/manipulated');
        
        switch(cropType) {
            case '10s':
                endpoint = '/manipulate/crop/10s';
                break;
            case '5s':
                endpoint = '/manipulate/crop/5s';
                break;
            case 'middle':
                endpoint = '/manipulate/crop/middle';
                formData.append('duration', '10.0');
                break;
            case 'end':
                endpoint = '/manipulate/crop/end';
                formData.append('duration', '10.0');
                break;
            default:
                throw new Error('Invalid crop type');
        }
        
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Crop applied (${cropType}): ${result.output_path}`, 'success');
            updateTransformedPlayer(result.output_path);
            updateTestDisplays(selectedAudioFile, result.output_path);
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply crop: ' + error.message);
    }
}

// Embedded Sample Transform
async function applyEmbeddedSampleTransform() {
    if (!selectedAudioFile) {
        showError('Please select a sample audio file first');
        return;
    }
    
    const backgroundFile = document.getElementById('embeddedBackgroundFile')?.value;
    if (!backgroundFile) {
        showError('Please select a background audio file');
        return;
    }
    
    const position = document.getElementById('embeddedPosition')?.value || 'start';
    const sampleDuration = parseFloat(document.getElementById('embeddedSampleDuration')?.value || '1.5');
    const volumeDb = parseFloat(document.getElementById('embeddedVolumeDb')?.value || '0.0');
    const applyTransform = document.getElementById('embeddedApplyTransform')?.value || 'None';
    const transformParams = document.getElementById('embeddedTransformParams')?.value || null;
    
    try {
        const formData = new FormData();
        formData.append('sample_path', selectedAudioFile);
        formData.append('background_path', backgroundFile);
        formData.append('position', position);
        formData.append('sample_duration', sampleDuration.toString());
        formData.append('volume_db', volumeDb.toString());
        formData.append('apply_transform', applyTransform);
        if (transformParams) {
            formData.append('transform_params', transformParams);
        }
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/embedded-sample`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Embedded sample applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTransformedPlayer(result.output_path);
                updateTestDisplays(selectedAudioFile, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply embedded sample: ' + error.message);
    }
}

// Song A in Song B Transform
async function applySongAInSongBTransform() {
    if (!selectedAudioFile) {
        showError('Please select Song A audio file first');
        return;
    }
    
    const songBBaseFile = document.getElementById('songBBaseFile')?.value || null;
    const sampleStartTime = parseFloat(document.getElementById('songASampleStartTime')?.value || '0.0');
    const sampleDuration = parseFloat(document.getElementById('songASampleDuration')?.value || '1.5');
    const songBDuration = parseFloat(document.getElementById('songBDuration')?.value || '30.0');
    const applyTransform = document.getElementById('songAApplyTransform')?.value || 'None';
    const transformParams = document.getElementById('songATransformParams')?.value || null;
    const mixVolumeDb = parseFloat(document.getElementById('songAMixVolumeDb')?.value || '0.0');
    
    try {
        const formData = new FormData();
        formData.append('song_a_path', selectedAudioFile);
        if (songBBaseFile) {
            formData.append('song_b_base_path', songBBaseFile);
        }
        formData.append('sample_start_time', sampleStartTime.toString());
        formData.append('sample_duration', sampleDuration.toString());
        formData.append('song_b_duration', songBDuration.toString());
        formData.append('apply_transform', applyTransform);
        if (transformParams) {
            formData.append('transform_params', transformParams);
        }
        formData.append('mix_volume_db', mixVolumeDb.toString());
        formData.append('output_dir', 'data/manipulated');
        
        const response = await fetch(`${API_BASE}/manipulate/song-a-in-song-b`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(result.message);
            addSystemLog(`Song A in Song B applied: ${result.output_path}`, 'success');
            loadManipulateAudioFiles();
            loadTestFileSelects();
            if (result.output_path) {
                updateTransformedPlayer(result.output_path);
                updateTestDisplays(selectedAudioFile, result.output_path);
            }
        } else {
            showError(result.message || 'Transform failed');
        }
    } catch (error) {
        showError('Failed to apply Song A in Song B: ' + error.message);
    }
}

// Update test displays when files are loaded
function updateTestDisplays(originalPath, transformedPath) {
    console.log('[updateTestDisplays] Called with:', { originalPath, transformedPath });
    
    // Try new IDs first (manipulate_section.html), fallback to old IDs (index.html)
    const originalDisplay = document.getElementById('testOriginalPath') || document.getElementById('originalTestDisplay');
    const transformedDisplay = document.getElementById('testTransformedPath') || document.getElementById('transformedTestDisplay');
    const originalStatus = document.getElementById('originalTestStatus');
    const transformedStatus = document.getElementById('transformedTestStatus');
    const testBtn = document.getElementById('testFingerprintBtn') || document.getElementById('testBtn');
    
    if (!originalDisplay && !originalStatus) {
        console.error('[updateTestDisplays] originalTestDisplay/originalTestStatus element not found!');
    }
    if (!transformedDisplay && !transformedStatus) {
        console.error('[updateTestDisplays] transformedTestDisplay/transformedTestStatus element not found!');
    }
    if (!testBtn) {
        console.error('[updateTestDisplays] testBtn element not found!');
    }
    
    if (originalDisplay) {
        if (originalPath) {
            originalDisplay.value = originalPath;
            originalDisplay.style.color = '#4ade80';
            console.log('[updateTestDisplays] Set original path:', originalPath);
        } else {
            originalDisplay.value = '';
            originalDisplay.style.color = '#9ca3af';
            console.log('[updateTestDisplays] Cleared original path');
        }
    }
    
    if (originalStatus) {
        if (originalPath && originalPath.trim() !== '') {
            originalStatus.textContent = originalPath.split('/').pop();
        } else {
            originalStatus.textContent = 'No original audio selected.';
        }
    }
    
    if (transformedDisplay) {
        if (transformedPath) {
            transformedDisplay.value = transformedPath;
            transformedDisplay.style.color = '#4ade80';
            console.log('[updateTestDisplays] Set transformed path:', transformedPath);
        } else {
            // Don't clear transformed path if it's already set (preserve existing transformed audio)
            if (!transformedDisplay.value) {
                transformedDisplay.value = '';
                transformedDisplay.style.color = '#9ca3af';
            }
        }
    }
    
    if (transformedStatus) {
        if (transformedPath && transformedPath.trim() !== '') {
            transformedStatus.textContent = transformedPath.split('/').pop();
        } else {
            transformedStatus.textContent = 'No transformed audio available. Apply transforms first.';
        }
    }
    
    // Enable test button if both files are available
    if (testBtn) {
        const hasOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim() !== '') || (originalStatus && originalStatus.textContent !== 'No original audio selected.');
        const hasTransformed = (transformedDisplay && transformedDisplay.value && transformedDisplay.value.trim() !== '') || (transformedStatus && transformedStatus.textContent !== 'No transformed audio available. Apply transforms first.');
        
        console.log('[updateTestDisplays] Button state check:', {
            hasOriginal,
            hasTransformed,
            originalValue: originalDisplay?.value,
            transformedValue: transformedDisplay?.value
        });
        
        testBtn.disabled = !(hasOriginal && hasTransformed);
        console.log('[updateTestDisplays] Test button disabled:', testBtn.disabled);
    }
}

// Deliverables & Reports
async function loadDeliverables() {
    try {
        const response = await fetch(`${API_BASE}/runs`);
        const result = await response.json();
        
        const deliverablesListDiv = document.getElementById('deliverablesList');
        
        if (result.runs && result.runs.length > 0) {
            // Group runs by phase - check metrics.json for phase info if not in run object
            const phase1Runs = [];
            const phase2Runs = [];
            const otherRuns = [];
            
            // First pass: check runs with phase info
            const runsToCheck = [];
            result.runs.forEach(run => {
                const runPath = (run.path || '').toLowerCase();
                const runId = (run.id || '').toLowerCase();
                const runPhase = (run.phase || run.summary?.phase || '').toLowerCase();
                
                const isPhase1 = runPhase === 'phase1' || runPath.includes('phase1') || runId.includes('phase1') ||
                                 runPath.includes('phase_1') || runId.includes('phase_1') || (runId.includes('test_') && runId.includes('phase1'));
                const isPhase2 = runPhase === 'phase2' || runPath.includes('phase2') || runId.includes('phase2') ||
                                 runPath.includes('phase_2') || runId.includes('phase_2') || (runId.includes('test_') && runId.includes('phase2'));
                
                if (isPhase1 && !isPhase2) {
                    phase1Runs.push(run);
                } else if (isPhase2 && !isPhase1) {
                    phase2Runs.push(run);
                } else if (!runPhase || runPhase === 'unknown') {
                    // Need to check metrics.json directly
                    runsToCheck.push(run);
                } else {
                    otherRuns.push(run);
                }
            });
            
            // Second pass: check metrics.json for runs without phase info
            for (const run of runsToCheck) {
                try {
                    const detailsResp = await fetch(`${API_BASE}/runs/${run.id}`);
                    if (detailsResp.ok) {
                        const details = await detailsResp.json();
                        const metrics = details.metrics || {};
                        const phase = (metrics.summary?.phase || metrics.test_details?.phase || '').toLowerCase();
                        
                        if (phase === 'phase1') {
                            run.phase = 'phase1';
                            phase1Runs.push(run);
                        } else if (phase === 'phase2') {
                            run.phase = 'phase2';
                            phase2Runs.push(run);
                        } else {
                            // Check config file used - if it contains phase1/phase2 in path
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
            
            // Sort each group by timestamp (most recent first)
            const sortByTime = (a, b) => (b.timestamp || 0) - (a.timestamp || 0);
            phase1Runs.sort(sortByTime);
            phase2Runs.sort(sortByTime);
            
            // Only show the most recent Phase 1 and Phase 2 reports
            if (deliverablesListDiv) {
                const latestReports = [];
                
                // Add most recent Phase 1 report if available
                if (phase1Runs.length > 0) {
                    latestReports.push({...phase1Runs[0], phaseLabel: 'Phase 1', isPhase1: true});
                }
                
                // Add most recent Phase 2 report if available
                if (phase2Runs.length > 0) {
                    latestReports.push({...phase2Runs[0], phaseLabel: 'Phase 2', isPhase2: true});
                }
                
                if (latestReports.length > 0) {
                    let html = '';
                    latestReports.forEach(run => {
                        const date = run.timestamp ? new Date(run.timestamp * 1000) : null;
                        const dateStr = date ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Pending';
                        const reportPath = `${run.path}/final_report/report.html`;
                        const hasReport = run.has_summary || run.has_metrics;
                        
                        // Determine phase label and color
                        const phaseLabel = run.phaseLabel || (run.isPhase1 ? 'Phase 1' : (run.isPhase2 ? 'Phase 2' : 'Report'));
                        const phaseColor = run.isPhase1 ? '#427eea' : (run.isPhase2 ? '#10b981' : '#9ca3af');
                        
                        // Calculate size (placeholder - would need actual file size)
                        const sizeStr = '1.2 MB'; // Placeholder
                        
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
                                    ${hasReport ? `<button class="btn" onclick="viewReport('${reportPath}', '${run.id}')" style="font-size: 11px; padding: 6px 12px; background: #427eea; color: #ffffff; border-radius: 4px; border: none; cursor: pointer;" title="View Report">📄 View</button>` : ''}
                                    ${hasReport ? `<button class="btn" onclick="downloadReportZip('${run.id}')" style="font-size: 11px; padding: 6px 12px; background: #10b981; color: #ffffff; border-radius: 4px; border: none; cursor: pointer;" title="Download Report as ZIP">⬇️ Download</button>` : ''}
                                    <button class="btn" onclick="deleteReport('${run.id}')" style="font-size: 11px; padding: 6px 12px; background: #f87171; color: #ffffff; border-radius: 4px; border: none; cursor: pointer;" title="Delete Report">🗑️</button>
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
            // No reports found
            if (deliverablesListDiv) {
                deliverablesListDiv.innerHTML = '<p style="color: #9ca3af; font-size: 12px; padding: 20px; text-align: center; background: #2d2d2d; border-radius: 8px;">No reports found.</p>';
            }
        }
    } catch (error) {
        console.error('Failed to load deliverables:', error);
        const deliverablesListDiv = document.getElementById('deliverablesList');
        if (deliverablesListDiv) {
            deliverablesListDiv.innerHTML = `<p style="color: #f87171; font-size: 12px; padding: 20px; text-align: center; background: #2d2d2d; border-radius: 8px;">Error loading reports: ${error.message}</p>`;
        }
    }
}

function viewReport(reportPath, runId) {
    // Open report HTML in new tab
    const url = `/api/files/report?path=${encodeURIComponent(reportPath)}`;
    window.open(url, '_blank');
}

async function downloadReportZip(runId) {
    try {
        showCompletionAlert(`Preparing download for ${runId}...`, 'info');
        
        // Use direct window.location for large files to avoid memory issues
        const downloadUrl = `${API_BASE}/runs/${runId}/download`;
        
        // Create a temporary link and click it
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `${runId}_report.zip`;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Clean up after a delay
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

async function viewRunDetails(runId) {
    try {
        const response = await fetch(`${API_BASE}/runs/${runId}`);
        const result = await response.json();
        
        const reportViewerDiv = document.getElementById('reportViewer');
        
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
        const phase = testDetails.phase || metrics.summary?.phase || 'unknown';
        
        const matched = testDetails.matched !== undefined ? testDetails.matched : (passFail.passed > 0);
        const statusColor = !hasMetrics ? '#f59e0b' : (matched ? '#10b981' : '#f87171');
        const statusText = !hasMetrics ? '⏳ PENDING' : (matched ? '✅ MATCHED' : '❌ NOT MATCHED');
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
                        <div style="color: ${statusColor}; font-size: 24px; font-weight: bold;">${passFail.passed || 0} / ${passFail.total || 0} Passed</div>
                    </div>
                </div>
            </div>
        `;
        
        if (result.metrics) {
            const summary = result.metrics.summary || {};
            html += '<div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #3d3d3d;">';
            html += '<h5 style="color: #427eea; margin-bottom: 10px; font-size: 14px;">📊 Additional Metrics</h5>';
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
        
        // Add visualization diagrams section
        html += `
            <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #3d3d3d;">
                <h5 style="color: #427eea; margin-bottom: 20px; font-size: 16px; font-weight: 600;">📊 Visualizations</h5>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                    <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                        <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Recall@K by Transform Severity</h6>
                        <div id="plot-recall-severity-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                            <img src="/api/files/plots/recall_by_severity.png?run_id=${runId}" 
                                 alt="Recall by Severity" 
                                 style="width: 100%; height: auto; border-radius: 4px; max-width: 100%;"
                                 onload="this.parentElement.querySelector('.plot-placeholder')?.style.display='none';"
                                 onerror="this.style.display='none'; this.parentElement.querySelector('.plot-placeholder').style.display='flex';">
                            <div class="plot-placeholder" style="display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af; padding: 40px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 10px;">📊</div>
                                <p style="margin: 0; font-size: 14px; font-weight: 500;">Recall by Severity</p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #6b7280;">Chart not available</p>
                                <p style="margin: 10px 0 0 0; font-size: 11px; color: #9ca3af;">Plots require matplotlib/PIL to be installed</p>
                            </div>
                        </div>
                    </div>
                    <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                        <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Similarity Score by Severity</h6>
                        <div id="plot-similarity-severity-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                            <img src="/api/files/plots/similarity_by_severity.png?run_id=${runId}" 
                                 alt="Similarity by Severity" 
                                 style="width: 100%; height: auto; border-radius: 4px; max-width: 100%;"
                                 onload="this.parentElement.querySelector('.plot-placeholder')?.style.display='none';"
                                 onerror="this.style.display='none'; this.parentElement.querySelector('.plot-placeholder').style.display='flex';">
                            <div class="plot-placeholder" style="display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af; padding: 40px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 10px;">📊</div>
                                <p style="margin: 0; font-size: 14px; font-weight: 500;">Similarity by Severity</p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #6b7280;">Chart not available</p>
                                <p style="margin: 10px 0 0 0; font-size: 11px; color: #9ca3af;">Plots require matplotlib/PIL to be installed</p>
                            </div>
                        </div>
                    </div>
                    <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                        <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Recall@K by Transform Type</h6>
                        <div id="plot-recall-transform-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                            <img src="/api/files/plots/recall_by_transform.png?run_id=${runId}" 
                                 alt="Recall by Transform Type" 
                                 style="width: 100%; height: auto; border-radius: 4px; max-width: 100%;"
                                 onload="this.parentElement.querySelector('.plot-placeholder')?.style.display='none';"
                                 onerror="this.style.display='none'; this.parentElement.querySelector('.plot-placeholder').style.display='flex';">
                            <div class="plot-placeholder" style="display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af; padding: 40px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 10px;">📊</div>
                                <p style="margin: 0; font-size: 14px; font-weight: 500;">Recall by Transform Type</p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #6b7280;">Chart not available</p>
                                <p style="margin: 10px 0 0 0; font-size: 11px; color: #9ca3af;">Plots require matplotlib/PIL to be installed</p>
                            </div>
                        </div>
                    </div>
                    <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); position: relative;">
                        <h6 style="color: #1e1e1e; margin: 0 0 15px 0; font-size: 14px; font-weight: 600;">Latency by Transform Type</h6>
                        <div id="plot-latency-transform-${runId}" style="min-height: 200px; display: flex; align-items: center; justify-content: center;">
                            <img src="/api/files/plots/latency_by_transform.png?run_id=${runId}" 
                                 alt="Latency by Transform Type" 
                                 style="width: 100%; height: auto; border-radius: 4px; max-width: 100%;"
                                 onload="this.parentElement.querySelector('.plot-placeholder')?.style.display='none';"
                                 onerror="this.style.display='none'; this.parentElement.querySelector('.plot-placeholder').style.display='flex';">
                            <div class="plot-placeholder" style="display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af; padding: 40px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 10px;">📊</div>
                                <p style="margin: 0; font-size: 14px; font-weight: 500;">Latency by Transform</p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #6b7280;">Chart not available</p>
                                <p style="margin: 10px 0 0 0; font-size: 11px; color: #9ca3af;">Plots require matplotlib/PIL to be installed</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        html += '</div>';
        reportViewerDiv.innerHTML = html;
    } catch (error) {
        console.error('Failed to load run details:', error);
        const reportViewerDiv = document.getElementById('reportViewer');
        if (reportViewerDiv) {
            reportViewerDiv.innerHTML = `
                <div style="padding: 15px; background: #3a1e1e; border-radius: 6px; border: 1px solid #f87171;">
                    <p style="color: #f87171; margin: 0;">Error loading details: ${error.message}</p>
                </div>
            `;
        }
    }
}

async function deleteReport(runId) {
    if (!confirm(`Are you sure you want to delete report "${runId}"?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/runs/${runId}`, {
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
            // Treat missing as already deleted (idempotent)
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
        
        // Reload deliverables list and dashboard
        setTimeout(() => {
            loadDeliverables();
            loadDashboard();
        }, 300);
    } catch (error) {
        console.error('Failed to delete report:', error);
        showError('Failed to delete report: ' + error.message);
        addSystemLog(`❌ Failed to delete report "${runId}": ${error.message}`, 'error');
    }
}

// ============================================================================
// Deliverables Transformation Functions
// ============================================================================

// Deliverables transformation state
let deliverablesSelectedAudioFile = null;

// Load audio files into deliverables select
async function loadDeliverablesAudioFiles() {
    try {
        const select = document.getElementById('deliverablesAudioSelect');
        if (!select) return;
        
        select.innerHTML = '<option value="">-- Select Audio File --</option>';
        
        // Load from test_audio directory
        try {
            const response = await fetch(`${API_BASE}/files/audio?directory=test_audio`);
            const result = await response.json();
            if (result.files && result.files.length > 0) {
                result.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.path || `data/test_audio/${file.name}`;
                    option.textContent = file.name || file;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load test_audio files:', error);
        }
        
        // Also load from originals directory
        try {
            const response2 = await fetch(`${API_BASE}/files/audio?directory=originals`);
            const result2 = await response2.json();
            if (result2.files && result2.files.length > 0) {
                result2.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.path || `data/originals/${file.name}`;
                    option.textContent = file.name || file;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            // Ignore errors loading originals
        }
    } catch (error) {
        console.error('Failed to load audio files:', error);
    }
}

function loadDeliverablesAudioInfo(filePath) {
    const infoDiv = document.getElementById('deliverablesAudioInfo');
    const fileNameSpan = document.getElementById('deliverablesSelectedFileName');
    const filePathSpan = document.getElementById('deliverablesSelectedFilePath');
    
    if (!filePath) {
        deliverablesSelectedAudioFile = null;
        if (fileNameSpan) fileNameSpan.textContent = '';
        if (filePathSpan) filePathSpan.textContent = '';
        if (infoDiv) infoDiv.style.display = 'block';
        updateDeliverablesTransformState();
        return;
    }
    
    deliverablesSelectedAudioFile = filePath;
    
    if (infoDiv && fileNameSpan && filePathSpan) {
        const fileName = filePath.split('/').pop();
        fileNameSpan.textContent = fileName;
        filePathSpan.textContent = filePath;
        infoDiv.style.display = 'block';
    }
    
    updateDeliverablesTransformState();
}

// Deliverables file upload handlers
function handleDeliverablesDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    const uploadArea = document.getElementById('deliverablesUploadArea');
    if (uploadArea) uploadArea.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        handleDeliverablesFileUpload(files[0]);
    }
}

function handleDeliverablesFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        handleDeliverablesFileUpload(files[0]);
    }
}

async function handleDeliverablesFileUpload(file) {
    if (!file.type.startsWith('audio/')) {
        showError('Please select an audio file');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('directory', 'test_audio');
        
        const response = await fetch(`${API_BASE}/upload/audio`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showCompletionAlert(`File uploaded: ${result.path}`);
            addSystemLog(`Audio file uploaded: ${result.path}`, 'success');
            
            // Reload file list and select the uploaded file
            await loadDeliverablesAudioFiles();
            const select = document.getElementById('deliverablesAudioSelect');
            if (select) {
                // Extract relative path from result.path (e.g., "data/test_audio/filename.mp3")
                const relativePath = result.path.startsWith('data/') ? result.path : `data/test_audio/${result.path.split('/').pop()}`;
                select.value = relativePath;
                loadDeliverablesAudioInfo(relativePath);
            }
        } else {
            showError(result.message || 'Upload failed');
        }
    } catch (error) {
        showError('Failed to upload file: ' + error.message);
    }
}

// Update slider displays for deliverables
function updateDeliverablesSpeedValue(value) {
    const display = document.getElementById('deliverablesSpeedValue');
    if (display) {
        display.textContent = (value / 100).toFixed(1) + 'x';
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesPitchValue(value) {
    const display = document.getElementById('deliverablesPitchValue');
    if (display) {
        display.textContent = parseFloat(value).toFixed(1);
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesReverbValue(value) {
    const display = document.getElementById('deliverablesReverbValue');
    if (display) {
        display.textContent = parseFloat(value).toFixed(1) + 'ms';
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesNoiseValue(value) {
    const display = document.getElementById('deliverablesNoiseValue');
    if (display) {
        display.textContent = value + '%';
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesEQValue(value) {
    const display = document.getElementById('deliverablesEQValue');
    if (display) {
        display.textContent = parseFloat(value).toFixed(1) + 'dB';
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesOverlayGainValue(value) {
    const display = document.getElementById('deliverablesOverlayGainValue');
    if (display) {
        display.textContent = parseFloat(value).toFixed(1) + 'dB';
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesSliderDisplay(type, value) {
    const displayMap = {
        'highpass': { id: 'deliverablesHighpassDisplay', suffix: 'Hz', decimals: 1 },
        'lowpass': { id: 'deliverablesLowpassDisplay', suffix: 'Hz', decimals: 1 },
        'boostHighs': { id: 'deliverablesBoostHighsDisplay', suffix: 'dB', decimals: 1 },
        'boostLows': { id: 'deliverablesBoostLowsDisplay', suffix: 'dB', decimals: 1 },
        'limiting': { id: 'deliverablesLimitingDisplay', suffix: 'dB', decimals: 1 },
        'noiseSNR': { id: 'deliverablesNoiseSNRDisplay', suffix: 'dB', decimals: 1 },
        'telephoneLow': { id: 'deliverablesTelephoneLowDisplay', suffix: 'Hz', decimals: 1 },
        'telephoneHigh': { id: 'deliverablesTelephoneHighDisplay', suffix: 'Hz', decimals: 1 }
    };
    const mapping = displayMap[type];
    if (mapping) {
        const display = document.getElementById(mapping.id);
        if (display) {
            const numValue = parseFloat(value);
            const decimals = mapping.decimals || 0;
            display.textContent = numValue.toFixed(decimals) + mapping.suffix;
        }
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesBitrateEnabled() {
    const codecSelect = document.getElementById('deliverablesCodecSelect');
    const bitrateSelect = document.getElementById('deliverablesBitrateSelect');
    if (codecSelect && bitrateSelect) {
        bitrateSelect.disabled = codecSelect.value === 'None';
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesCropDuration() {
    const cropTypeSelect = document.getElementById('deliverablesCropTypeSelect');
    const cropDurationGroup = document.getElementById('deliverablesCropDurationGroup');
    if (cropTypeSelect && cropDurationGroup) {
        const cropType = cropTypeSelect.value;
        cropDurationGroup.style.display = (cropType === 'middle' || cropType === 'end') ? 'block' : 'none';
    }
    updateDeliverablesTransformState();
}

function updateDeliverablesTransformState() {
    // Count enabled transformations
    const enabledTransforms = [];
    
    if (document.getElementById('deliverablesSpeedEnabled')?.checked) enabledTransforms.push('Speed');
    if (document.getElementById('deliverablesPitchEnabled')?.checked) enabledTransforms.push('Pitch');
    if (document.getElementById('deliverablesReverbEnabled')?.checked) enabledTransforms.push('Reverb');
    if (document.getElementById('deliverablesNoiseEnabled')?.checked) enabledTransforms.push('Noise Reduction');
    if (document.getElementById('deliverablesEQEnabled')?.checked) enabledTransforms.push('EQ');
    if (document.getElementById('deliverablesCompressionEnabled')?.checked && 
        document.getElementById('deliverablesCodecSelect')?.value !== 'None') enabledTransforms.push('Compression');
    if (document.getElementById('deliverablesOverlayEnabled')?.checked) enabledTransforms.push('Overlay');
    if (document.getElementById('deliverablesHighpassEnabled')?.checked) enabledTransforms.push('High-Pass');
    if (document.getElementById('deliverablesLowpassEnabled')?.checked) enabledTransforms.push('Low-Pass');
    if (document.getElementById('deliverablesBoostHighsEnabled')?.checked) enabledTransforms.push('Boost Highs');
    if (document.getElementById('deliverablesBoostLowsEnabled')?.checked) enabledTransforms.push('Boost Lows');
    if (document.getElementById('deliverablesTelephoneEnabled')?.checked) enabledTransforms.push('Telephone');
    if (document.getElementById('deliverablesLimitingEnabled')?.checked) enabledTransforms.push('Limiting');
    if (document.getElementById('deliverablesMultibandEnabled')?.checked) enabledTransforms.push('Multiband');
    if (document.getElementById('deliverablesAddNoiseEnabled')?.checked) enabledTransforms.push('Add Noise');
    if (document.getElementById('deliverablesCropEnabled')?.checked) enabledTransforms.push('Crop');
    
    const count = enabledTransforms.length;
    // Transform count and apply button removed - no longer needed
}

// Apply all selected transformations (quick single run, no full reports)
async function applyAllDeliverablesTransforms() {
    if (!deliverablesSelectedAudioFile) {
        showError('Please select an audio file first');
        return;
    }
    
    const enabledTransforms = [];
    
    // Collect all enabled transformations
    if (document.getElementById('deliverablesSpeedEnabled')?.checked) {
        enabledTransforms.push({
            type: 'speed',
            speed: parseFloat(document.getElementById('deliverablesSpeedSlider').value) / 100,
            preserve_pitch: document.getElementById('deliverablesPreservePitch')?.checked || false
        });
    }
    
    if (document.getElementById('deliverablesPitchEnabled')?.checked) {
        enabledTransforms.push({
            type: 'pitch',
            semitones: parseInt(document.getElementById('deliverablesPitchSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesReverbEnabled')?.checked) {
        enabledTransforms.push({
            type: 'reverb',
            delay_ms: parseFloat(document.getElementById('deliverablesReverbSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesNoiseEnabled')?.checked) {
        enabledTransforms.push({
            type: 'noise_reduction',
            strength: parseFloat(document.getElementById('deliverablesNoiseSlider').value) / 100
        });
    }
    
    if (document.getElementById('deliverablesEQEnabled')?.checked) {
        enabledTransforms.push({
            type: 'eq',
            gain_db: parseFloat(document.getElementById('deliverablesEQSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesCompressionEnabled')?.checked) {
        const codec = document.getElementById('deliverablesCodecSelect')?.value;
        if (codec !== 'None') {
            enabledTransforms.push({
                type: 'compression',
                codec: codec.toLowerCase(),
                bitrate: document.getElementById('deliverablesBitrateSelect')?.value
            });
        }
    }
    
    if (document.getElementById('deliverablesOverlayEnabled')?.checked) {
        const overlayFile = document.getElementById('deliverablesOverlayFile')?.files[0];
        enabledTransforms.push({
            type: 'overlay',
            gain_db: parseFloat(document.getElementById('deliverablesOverlayGainSlider')?.value || -6),
            overlay_file: overlayFile ? overlayFile.name : null
        });
    }
    
    if (document.getElementById('deliverablesHighpassEnabled')?.checked) {
        enabledTransforms.push({
            type: 'highpass',
            freq_hz: parseFloat(document.getElementById('deliverablesHighpassSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesLowpassEnabled')?.checked) {
        enabledTransforms.push({
            type: 'lowpass',
            freq_hz: parseFloat(document.getElementById('deliverablesLowpassSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesBoostHighsEnabled')?.checked) {
        enabledTransforms.push({
            type: 'boost_highs',
            gain_db: parseFloat(document.getElementById('deliverablesBoostHighsSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesBoostLowsEnabled')?.checked) {
        enabledTransforms.push({
            type: 'boost_lows',
            gain_db: parseFloat(document.getElementById('deliverablesBoostLowsSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesTelephoneEnabled')?.checked) {
        enabledTransforms.push({
            type: 'telephone',
            low_freq: parseFloat(document.getElementById('deliverablesTelephoneLow')?.value || 300),
            high_freq: parseFloat(document.getElementById('deliverablesTelephoneHigh')?.value || 3000)
        });
    }
    
    if (document.getElementById('deliverablesLimitingEnabled')?.checked) {
        enabledTransforms.push({
            type: 'limiting',
            ceiling_db: parseFloat(document.getElementById('deliverablesLimitingSlider').value)
        });
    }
    
    if (document.getElementById('deliverablesMultibandEnabled')?.checked) {
        enabledTransforms.push({
            type: 'multiband'
        });
    }
    
    if (document.getElementById('deliverablesAddNoiseEnabled')?.checked) {
        enabledTransforms.push({
            type: 'add_noise',
            noise_type: document.getElementById('deliverablesNoiseTypeSelect')?.value || 'white',
            snr_db: parseFloat(document.getElementById('deliverablesNoiseSNRSlider')?.value || 20)
        });
    }
    
    if (document.getElementById('deliverablesCropEnabled')?.checked) {
        const cropType = document.getElementById('deliverablesCropTypeSelect')?.value;
        enabledTransforms.push({
            type: 'crop',
            crop_type: cropType,
            duration: (cropType === 'middle' || cropType === 'end') ? 
                parseFloat(document.getElementById('deliverablesCropDuration')?.value || 10) : null
        });
    }
    
    if (enabledTransforms.length === 0) {
        showError('Please enable at least one transformation');
        return;
    }
    
    try {
        // Call backend endpoint to apply all transforms (no full reports)
        const formData = new FormData();
        formData.append('input_path', deliverablesSelectedAudioFile);
        formData.append('transforms', JSON.stringify(enabledTransforms));
        formData.append('generate_reports', 'false');
        
        // Add overlay file if provided
        const overlayFile = document.getElementById('deliverablesOverlayFile')?.files[0];
        if (overlayFile) {
            formData.append('overlay_file', overlayFile);
        }
        
        const response = await fetch(`${API_BASE}/manipulate/deliverables-batch`, {
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
            // Reload deliverables/dashboard to refresh lists
            setTimeout(() => {
                loadDeliverables();
                loadDashboard();
            }, 1000);
        } else {
            throw new Error(result.message || 'Failed to apply transformations');
        }
    } catch (error) {
        showError('Failed to apply transformations: ' + error.message);
        console.error('Deliverables transform error:', error);
    }
}

// Progress Modal Management
let progressModalState = {
    phase: 'both',
    commandId: null,
    startTime: null,
    overallProgress: 0,
    stepProgress: 0,
    currentStep: 'Initializing...',
    currentStepIndex: 0,
    stepStartTime: null,
    isCancelled: false,
    pollInterval: null
};

// Step mapping for progress calculation
const STEP_MAPPING = {
    'Step 1: Ingesting': 15,
    'Step 2: Generating transforms': 30,
    'Step 3: Building FAISS index': 50,
    'Step 4: Running queries': 70,
    'Step 5: Analyzing results': 85,
    'Step 6: Capturing failures': 95,
    'Step 7: Generating report': 100
};

function showProgressModal(phase) {
    const modal = document.getElementById('progressModal');
    if (!modal) return;
    
    progressModalState.phase = phase;
    progressModalState.startTime = Date.now();
    progressModalState.stepStartTime = Date.now();
    progressModalState.overallProgress = 0;
    progressModalState.stepProgress = 0;
    progressModalState.currentStep = 'Initializing...';
    progressModalState.currentStepIndex = 0;
    progressModalState.isCancelled = false;
    
    // Reset UI
    updateProgressIndicator('overall', 0, 'Waiting...');
    updateProgressIndicator('step', 0, 'Waiting...');
    updateCurrentStep('Initializing...');
    updateTimeInfo();
    
    // Close button is enabled and will cancel the process if clicked
    const closeBtn = document.getElementById('progressModalClose');
    if (closeBtn) closeBtn.disabled = false;
    
    modal.style.display = 'flex';
    
    // Start time update interval
    if (progressModalState.timeInterval) {
        clearInterval(progressModalState.timeInterval);
    }
    progressModalState.timeInterval = setInterval(updateTimeInfo, 1000);
}

function closeProgressModal() {
    // If there's an active process, cancel it first
    if (progressModalState.commandId && !progressModalState.isCancelled) {
        cancelProgress();
        return;
    }
    
    const modal = document.getElementById('progressModal');
    if (!modal) return;
    
    modal.style.display = 'none';
    
    // Clear intervals
    if (progressModalState.pollInterval) {
        clearInterval(progressModalState.pollInterval);
        progressModalState.pollInterval = null;
    }
    if (progressModalState.timeInterval) {
        clearInterval(progressModalState.timeInterval);
        progressModalState.timeInterval = null;
    }
}

function updateProgressIndicator(type, percentage, status) {
    const percentageEl = document.getElementById(`${type}Percentage`);
    const statusEl = document.getElementById(`${type}Status`);
    const circleEl = document.querySelector(`.progress-circle-fill.${type}`);
    
    // Clamp percentage to valid range
    const clampedPercentage = Math.max(0, Math.min(100, percentage));
    
    if (percentageEl) percentageEl.textContent = `${Math.round(clampedPercentage)}%`;
    if (statusEl) {
        // Truncate long status text if needed
        const maxStatusLength = 30;
        const displayStatus = status.length > maxStatusLength 
            ? status.substring(0, maxStatusLength - 3) + '...' 
            : status;
        statusEl.textContent = displayStatus;
        statusEl.title = status; // Show full text on hover
    }
    
    if (circleEl) {
        const radius = 54;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (clampedPercentage / 100) * circumference;
        circleEl.style.strokeDasharray = `${circumference} ${circumference}`;
        circleEl.style.strokeDashoffset = offset;
        
        // Update color based on status
        circleEl.classList.remove('pending', 'error');
        if (clampedPercentage === 0) {
            circleEl.classList.add('pending');
        } else if (status.toLowerCase().includes('failed') || status.toLowerCase().includes('error')) {
            circleEl.classList.add('error');
        }
    }
    
    // Update state
    if (type === 'overall') {
        progressModalState.overallProgress = clampedPercentage;
    } else if (type === 'step') {
        progressModalState.stepProgress = clampedPercentage;
    }
}

function updateCurrentStep(step) {
    const stepEl = document.getElementById('currentStep');
    if (stepEl) {
        stepEl.textContent = `Current Step: ${step}`;
        progressModalState.currentStep = step;
    }
}

function updateTimeInfo() {
    if (!progressModalState.startTime) return;
    
    const elapsed = Date.now() - progressModalState.startTime;
    const seconds = Math.floor(elapsed / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    const h = String(hours).padStart(2, '0');
    const m = String(minutes % 60).padStart(2, '0');
    const s = String(seconds % 60).padStart(2, '0');
    
    const timeEl = document.getElementById('timeInfo');
    if (timeEl) {
        timeEl.textContent = `Time elapsed: ${h}:${m}:${s}`;
    }
}

// Step definitions with their order and step-level progress ranges
const STEP_DEFINITIONS = [
    { text: 'Step 1: Ingesting', keywords: ['ingest', 'ingesting'], stepIndex: 0, stepProgress: 0 },
    { text: 'Step 2: Generating transforms', keywords: ['transform', 'generating transforms'], stepIndex: 1, stepProgress: 0 },
    { text: 'Step 3: Building FAISS index', keywords: ['index', 'faiss', 'building'], stepIndex: 2, stepProgress: 0 },
    { text: 'Step 4: Running queries', keywords: ['query', 'queries', 'running queries'], stepIndex: 3, stepProgress: 0 },
    { text: 'Step 5: Analyzing results', keywords: ['analyze', 'analyzing', 'results'], stepIndex: 4, stepProgress: 0 },
    { text: 'Step 6: Capturing failures', keywords: ['failure', 'failures', 'capturing'], stepIndex: 5, stepProgress: 0 },
    { text: 'Step 7: Generating report', keywords: ['report', 'generating report'], stepIndex: 6, stepProgress: 0 }
];

function parseLogForProgress(logMessage, currentActivePhase) {
    if (!logMessage) return null;
    
    const message = logMessage.toLowerCase();
    const originalMessage = logMessage; // Keep original for parsing
    
    // Detect which phase is running
    let detectedPhase = null;
    if (message.includes('phase1') || message.includes('phase_1') || message.includes('test_matrix_phase1')) {
        detectedPhase = 'phase1';
    } else if (message.includes('phase2') || message.includes('phase_2') || message.includes('test_matrix_phase2')) {
        detectedPhase = 'phase2';
    } else {
        detectedPhase = currentActivePhase;
    }
    
    // Parse tqdm progress bar format: "desc: 45%|████▌     | 23/50 [00:30<00:35, 1.23s/it]"
    // Or simpler: "desc: 45%|████▌     | 23/50"
    const tqdmPattern = /(\d+)%\s*\|\s*[█▌▎▏\s]+\|\s*(\d+)\/(\d+)/;
    const tqdmMatch = originalMessage.match(tqdmPattern);
    
    let extractedProgress = null;
    let progressText = '';
    
    if (tqdmMatch) {
        const percentage = parseInt(tqdmMatch[1]);
        const current = parseInt(tqdmMatch[2]);
        const total = parseInt(tqdmMatch[3]);
        extractedProgress = percentage;
        progressText = `${current}/${total}`;
    } else {
        // Try to parse other progress formats
        // Pattern: "Processing file 3 of 10" or "Step 5 of 7" or "3/10"
        const filePattern = /(\d+)\s*(?:of|\/)\s*(\d+)/i;
        const fileMatch = originalMessage.match(filePattern);
        if (fileMatch) {
            const current = parseInt(fileMatch[1]);
            const total = parseInt(fileMatch[2]);
            extractedProgress = Math.round((current / total) * 100);
            progressText = `${current}/${total}`;
        }
        
        // Pattern: "X%" standalone
        const percentPattern = /(\d+)%/;
        const percentMatch = originalMessage.match(percentPattern);
        if (percentMatch && !extractedProgress) {
            extractedProgress = parseInt(percentMatch[1]);
        }
    }
    
    // Check for step markers
    let matchedStep = null;
    for (let i = 0; i < STEP_DEFINITIONS.length; i++) {
        const stepDef = STEP_DEFINITIONS[i];
        const stepLower = stepDef.text.toLowerCase();
        
        // Check if this step is mentioned in the log
        if (message.includes(stepLower) || 
            stepDef.keywords.some(keyword => message.includes(keyword))) {
            matchedStep = {
                phase: detectedPhase,
                stepIndex: stepDef.stepIndex,
                stepText: stepDef.text,
                stepProgress: extractedProgress !== null ? extractedProgress : 0,
                progressText: progressText
            };
            break;
        }
    }
    
    // If we found a step match, return it with progress
    if (matchedStep) {
        return matchedStep;
    }
    
    // If we extracted progress but didn't match a step, try to infer step from context
    if (extractedProgress !== null) {
        // Try to infer step from log content
        let inferredStep = null;
        if (message.includes('ingest') || message.includes('processing original')) {
            inferredStep = STEP_DEFINITIONS[0]; // Step 1: Ingesting
        } else if (message.includes('transform') || message.includes('generating')) {
            inferredStep = STEP_DEFINITIONS[1]; // Step 2: Generating transforms
        } else if (message.includes('index') || message.includes('faiss') || message.includes('building') || message.includes('embedding')) {
            inferredStep = STEP_DEFINITIONS[2]; // Step 3: Building FAISS index
        } else if (message.includes('query') || message.includes('running queries')) {
            inferredStep = STEP_DEFINITIONS[3]; // Step 4: Running queries
        } else if (message.includes('analyze') || message.includes('analyzing')) {
            inferredStep = STEP_DEFINITIONS[4]; // Step 5: Analyzing results
        } else if (message.includes('failure') || message.includes('capturing')) {
            inferredStep = STEP_DEFINITIONS[5]; // Step 6: Capturing failures
        } else if (message.includes('report') || message.includes('generating report')) {
            inferredStep = STEP_DEFINITIONS[6]; // Step 7: Generating report
        }
        
        if (inferredStep) {
            return {
                phase: detectedPhase,
                stepIndex: inferredStep.stepIndex,
                stepText: inferredStep.text,
                stepProgress: extractedProgress,
                progressText: progressText
            };
        }
    }
    
    // Check for completion
    if (message.includes('completed') || message.includes('finished') || 
        message.includes('experiment run:') || message.includes('report generated')) {
        return {
            phase: detectedPhase,
            stepIndex: STEP_DEFINITIONS.length - 1,
            stepText: 'Complete',
            stepProgress: 100,
            completed: true,
            progressText: '100%'
        };
    }
    
    // Check for errors
    if (message.includes('error') || message.includes('failed') || 
        message.includes('exception') || message.includes('traceback')) {
        return {
            phase: detectedPhase,
            stepText: 'Error',
            error: true
        };
    }
    
    return null;
}

function calculateOverallProgress(currentPhase, stepIndex, stepProgress) {
    // Calculate overall progress based on phase and step
    const totalSteps = STEP_DEFINITIONS.length;
    const stepWeight = 100 / totalSteps; // Each step is worth ~14.3%
    
    if (progressModalState.phase === 'both') {
        // Phase 1: steps 0-6 (0-50%), Phase 2: steps 0-6 (50-100%)
        if (currentPhase === 'phase1') {
            // Phase 1: 0-50%
            const baseProgress = (stepIndex / totalSteps) * 50;
            const stepContribution = (stepProgress / 100) * stepWeight * 0.5;
            return Math.min(baseProgress + stepContribution, 50);
        } else if (currentPhase === 'phase2') {
            // Phase 2: 50-100%
            const baseProgress = 50 + (stepIndex / totalSteps) * 50;
            const stepContribution = (stepProgress / 100) * stepWeight * 0.5;
            return Math.min(baseProgress + stepContribution, 100);
        }
    } else if (progressModalState.phase === 'phase1') {
        // Single Phase 1: 0-100%
        const baseProgress = (stepIndex / totalSteps) * 100;
        const stepContribution = (stepProgress / 100) * stepWeight;
        return Math.min(baseProgress + stepContribution, 100);
    } else if (progressModalState.phase === 'phase2') {
        // Single Phase 2: 0-100%
        const baseProgress = (stepIndex / totalSteps) * 100;
        const stepContribution = (stepProgress / 100) * stepWeight;
        return Math.min(baseProgress + stepContribution, 100);
    }
    
    return 0;
}

async function cancelProgress() {
    if (!progressModalState.commandId) {
        // No active process, just close modal
        closeProgressModal();
        return;
    }
    
    if (!confirm('Are you sure you want to cancel the report generation?')) {
        return;
    }
    
    try {
        const resp = await fetch(`${API_BASE}/process/${progressModalState.commandId}/cancel`, {
            method: 'POST'
        });
        
        if (resp.ok) {
            progressModalState.isCancelled = true;
            updateCurrentStep('Cancelling...');
            updateProgressIndicator('overall', progressModalState.overallProgress, 'Cancelled');
            updateProgressIndicator('step', progressModalState.stepProgress, 'Cancelled');
            
            // Stop polling
            if (progressModalState.pollInterval) {
                clearInterval(progressModalState.pollInterval);
                progressModalState.pollInterval = null;
            }
            
            showCompletionAlert('Report generation cancelled', 'info');
            setTimeout(() => {
                closeProgressModal();
                loadDeliverables();
                loadDashboard();
            }, 2000);
        } else {
            showError('Failed to cancel process');
        }
    } catch (error) {
        showError('Error cancelling process: ' + error.message);
    }
}

// Run full Phase 1/Phase 2 suites (uses full test matrices to generate comprehensive reports)
async function runPhaseSuite(phase = 'both') {
    try {
        const btnText = {
            both: 'Generating Phase 1 & 2…',
            phase1: 'Generating Phase 1…',
            phase2: 'Generating Phase 2…'
        }[phase] || 'Generating…';

        // Show progress modal
        showProgressModal(phase);

        const resp = await fetch(`${API_BASE}/process/generate-deliverables`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                // Use the manifest that contains local file paths
                manifest_path: 'data/manifests/files_manifest.csv',
                phase
            })
        });

        if (!resp.ok) {
            let msg = `HTTP ${resp.status}`;
            try {
                const data = await resp.json();
                msg = data.message || msg;
            } catch {
                const text = await resp.text();
                msg = `${msg}: ${text.substring(0, 200)}`;
            }
            closeProgressModal();
            throw new Error(msg);
        }

        const result = await resp.json();
        const commandId = result.command_id;
        progressModalState.commandId = commandId;

        // Poll for logs and show progress
        let lastLogCount = 0;
        let currentActivePhase = phase === 'both' ? 'phase1' : phase;
        
        const pollLogs = async () => {
            if (progressModalState.isCancelled) {
                return;
            }
            
            try {
                const logResp = await fetch(`${API_BASE}/process/${commandId}/logs`);
                if (logResp.ok) {
                    const logData = await logResp.json();
                    if (logData.logs && logData.logs.length > 0) {
                        // Process new logs
                        const newLogs = logData.logs.slice(lastLogCount);
                        if (newLogs.length > 0) {
                            // Track progress even if no step marker found (for continuous updates)
                            let foundProgressInBatch = false;
                            
                            newLogs.forEach(log => {
                                if (log.type === 'stdout' || log.type === 'stderr') {
                                    console.log(`[${commandId}] ${log.message}`);
                                    
                                    // Parse log for progress
                                    const progressInfo = parseLogForProgress(log.message, currentActivePhase);
                                    if (progressInfo) {
                                        foundProgressInBatch = true;
                                        if (progressInfo.error) {
                                            updateProgressIndicator('overall', progressModalState.overallProgress, 'Error');
                                            updateProgressIndicator('step', progressModalState.stepProgress, 'Error');
                                            updateCurrentStep('Error occurred');
                                        } else if (progressInfo.stepText) {
                                            // Check if this is a new step
                                            const isNewStep = progressInfo.stepIndex !== undefined && 
                                                             progressInfo.stepIndex !== progressModalState.currentStepIndex;
                                            
                                            if (isNewStep) {
                                                // New step started - reset step progress
                                                progressModalState.currentStepIndex = progressInfo.stepIndex;
                                                progressModalState.stepProgress = 0;
                                                progressModalState.stepStartTime = Date.now();
                                            }
                                            
                                            // Use extracted progress from logs if available, otherwise estimate based on time
                                            let stepProgress = progressInfo.stepProgress !== undefined ? progressInfo.stepProgress : 0;
                                            
                                            // If no progress extracted from log, use time-based estimation as fallback
                                            if (stepProgress === 0 && progressModalState.stepStartTime) {
                                                // Estimate step duration based on step type
                                                const stepDurations = {
                                                    0: 60000,  // Ingesting: ~60s
                                                    1: 120000, // Generating transforms: ~120s
                                                    2: 180000, // Building index: ~180s
                                                    3: 150000, // Running queries: ~150s
                                                    4: 30000,  // Analyzing: ~30s
                                                    5: 20000,  // Capturing failures: ~20s
                                                    6: 15000   // Generating report: ~15s
                                                };
                                                const estimatedStepDuration = stepDurations[progressModalState.currentStepIndex] || 60000;
                                                const timeInStep = Date.now() - progressModalState.stepStartTime;
                                                stepProgress = Math.min((timeInStep / estimatedStepDuration) * 100, 95); // Cap at 95% until completion
                                            }
                                            
                                            progressModalState.stepProgress = stepProgress;
                                            
                                            // Calculate overall progress
                                            const overallProgress = calculateOverallProgress(
                                                progressInfo.phase || currentActivePhase,
                                                progressModalState.currentStepIndex,
                                                stepProgress
                                            );
                                            progressModalState.overallProgress = overallProgress;
                                            
                                            // Build step display text with progress details
                                            let stepDisplayText = progressInfo.stepText;
                                            if (progressInfo.progressText) {
                                                stepDisplayText = `${progressInfo.stepText}: ${progressInfo.progressText}`;
                                            } else if (stepProgress > 0) {
                                                stepDisplayText = `${progressInfo.stepText}: ${Math.round(stepProgress)}%`;
                                            }
                                            
                                            // Update UI
                                            updateProgressIndicator('overall', overallProgress, progressInfo.completed ? 'Complete' : `${Math.round(overallProgress)}%`);
                                            updateProgressIndicator('step', stepProgress, stepDisplayText);
                                            updateCurrentStep(stepDisplayText);
                                            
                                            // If phase1 completes and we're running both, switch to phase2
                                            if (phase === 'both' && progressInfo.phase === 'phase1' && progressInfo.completed) {
                                                currentActivePhase = 'phase2';
                                                progressModalState.currentStepIndex = 0;
                                                progressModalState.stepProgress = 0;
                                                progressModalState.stepStartTime = Date.now();
                                                updateProgressIndicator('step', 0, 'Starting Phase 2...');
                                            }
                                            
                                            // If step completed, set to 100%
                                            if (progressInfo.completed) {
                                                progressModalState.stepProgress = 100;
                                                updateProgressIndicator('step', 100, `${progressInfo.stepText}: Complete`);
                                            }
                                        }
                                    }
                                }
                            });
                            
                            // If we found progress in this batch, update UI even if step didn't change
                            if (foundProgressInBatch && progressModalState.currentStepIndex !== undefined) {
                                // Recalculate overall progress based on current step progress
                                const overallProgress = calculateOverallProgress(
                                    currentActivePhase,
                                    progressModalState.currentStepIndex,
                                    progressModalState.stepProgress
                                );
                                progressModalState.overallProgress = overallProgress;
                                
                                // Update overall progress indicator
                                updateProgressIndicator('overall', overallProgress, `${Math.round(overallProgress)}%`);
                            }
                            
                            lastLogCount = logData.logs.length;
                        }
                        
                        // Check if completed
                        const completed = logData.logs.some(l => l.type === 'status' && l.message === 'completed');
                        const failed = logData.logs.some(l => l.type === 'status' && l.message === 'failed');
                        
                        if (completed || failed) {
                            const exitCodeLog = logData.logs.find(l => l.type === 'exit_code');
                            const exitCodeNum = exitCodeLog ? Number(exitCodeLog.message) : -1;
                            
                            if (failed || exitCodeNum !== 0) {
                                const errorLogs = logData.logs.filter(l => 
                                    l.type === 'error' || 
                                    (l.type === 'stderr' && l.message.toLowerCase().includes('error'))
                                );
                                const errorMsg = errorLogs.length > 0 
                                    ? errorLogs.map(l => l.message).join('; ')
                                    : `Process exited with code ${exitCodeNum}`;
                                
                                // Update progress to show error
                                updateProgressIndicator('overall', progressModalState.overallProgress, 'Failed');
                                updateProgressIndicator('step', progressModalState.stepProgress, 'Failed');
                                updateCurrentStep('Process failed');
                                
                                // Clear commandId so closeProgressModal doesn't try to cancel
                                progressModalState.commandId = null;
                                
                                // Stop polling
                                if (progressModalState.pollInterval) {
                                    clearTimeout(progressModalState.pollInterval);
                                    progressModalState.pollInterval = null;
                                }
                                
                                setTimeout(() => {
                                    closeProgressModal();
                                    showError('Failed to run suite: ' + errorMsg);
                                }, 3000);
                                return;
                            }
                            
                            // Success - update progress to 100%
                            updateProgressIndicator('overall', 100, 'Complete ✓');
                            updateProgressIndicator('step', 100, 'Complete ✓');
                            updateCurrentStep('Reports generated successfully!');
                            
                            // Clear commandId so closeProgressModal doesn't try to cancel
                            progressModalState.commandId = null;
                            
                            // Stop polling
                            if (progressModalState.pollInterval) {
                                clearTimeout(progressModalState.pollInterval);
                                progressModalState.pollInterval = null;
                            }
                            
                            setTimeout(() => {
                                closeProgressModal();
                                showCompletionAlert(`${btnText} completed successfully!`, 'success');
                                loadDeliverables();
                                loadDashboard();
                            }, 2000);
                            return;
                        }
                    }
                }
                
                // Continue polling every 1-2 seconds
                progressModalState.pollInterval = setTimeout(pollLogs, 1500);
            } catch (error) {
                if (error.message && error.message.includes('Process failed')) {
                    closeProgressModal();
                    showError('Failed to run suite: ' + error.message);
                } else {
                    console.error('Error polling logs:', error);
                    // Continue polling even on fetch errors (process might still be running)
                    progressModalState.pollInterval = setTimeout(pollLogs, 2000);
                }
            }
        };
        
        // Start polling after 1 second
        progressModalState.pollInterval = setTimeout(pollLogs, 1000);

    } catch (e) {
        closeProgressModal();
        showError(`Failed to run suite: ${e.message}`);
        console.error('Suite run error:', e);
    }
}
