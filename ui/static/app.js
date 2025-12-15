// Audio Fingerprint Robustness Lab - Frontend JavaScript

const API_BASE = '/api';
let currentProcessId = null;
let logPollInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize test button state
    const originalDisplay = document.getElementById('originalTestDisplay');
    const transformedDisplay = document.getElementById('transformedTestDisplay');
    const testBtn = document.getElementById('testBtn');
    
    if (testBtn && originalDisplay && transformedDisplay) {
        // Check initial state and update button
        const hasOriginal = originalDisplay.value && originalDisplay.value.trim() !== '';
        const hasTransformed = transformedDisplay.value && transformedDisplay.value.trim() !== '';
        testBtn.disabled = !(hasOriginal && hasTransformed);
        console.log('[DOMContentLoaded] Initialized test button state:', {
            hasOriginal,
            hasTransformed,
            disabled: testBtn.disabled
        });
    }
    
    checkStatus();
    loadDashboard();
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

function updateOriginalPlayer(filePath) {
    const player = document.getElementById('originalAudioPlayer');
    const playBtn = document.getElementById('originalPlayBtn');
    const infoDiv = document.getElementById('originalPlayerInfo');
    
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
            infoDiv.innerHTML = '<p style="color: #9ca3af; font-size: 12px; margin: 0;">No audio loaded</p>';
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
        infoDiv.innerHTML = `<p style="color: #4ade80; font-size: 12px; margin: 0;">Loaded: ${fileName}</p>`;
    }
    originalAudioPlaying = false;
}

function updateTransformedPlayer(filePath) {
    console.log('[updateTransformedPlayer] Called with filePath:', filePath);
    
    const player = document.getElementById('transformedAudioPlayer');
    const playBtn = document.getElementById('transformedPlayBtn');
    const infoDiv = document.getElementById('transformedPlayerInfo');
    
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
            infoDiv.innerHTML = '<p style="color: #9ca3af; font-size: 12px; margin: 0;">No transformed audio available</p>';
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
        infoDiv.innerHTML = `<p style="color: #4ade80; font-size: 12px; margin: 0;">Loaded: ${fileName}</p>`;
        console.log('[updateTransformedPlayer] Updated info display with:', fileName);
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
            // Update transformed test display - preserve original path
            if (result.output_path) {
                const originalDisplay = document.getElementById('originalTestDisplay');
                const existingOriginal = originalDisplay?.value?.trim() || selectedAudioFile || null;
                updateTestDisplays(existingOriginal, result.output_path);
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
            
            // Auto-reload deliverables if report was generated
            if (result.report_id) {
                addSystemLog(`Report auto-generated: ${result.report_id}`, 'info');
                // Reload deliverables after a short delay
                setTimeout(() => {
                    if (document.getElementById('deliverables').classList.contains('active')) {
                        loadDeliverables();
                    }
                }, 2000);
            }
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
    console.log('[updateTestDisplays] Called with:', { originalPath, transformedPath });
    
    const originalDisplay = document.getElementById('originalTestDisplay');
    const transformedDisplay = document.getElementById('transformedTestDisplay');
    const testBtn = document.getElementById('testBtn');
    
    if (!originalDisplay) {
        console.error('[updateTestDisplays] originalTestDisplay element not found!');
    }
    if (!transformedDisplay) {
        console.error('[updateTestDisplays] transformedTestDisplay element not found!');
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
    
    // Enable test button if both files are available
    if (testBtn) {
        const hasOriginal = originalDisplay && originalDisplay.value && originalDisplay.value.trim() !== '';
        const hasTransformed = transformedDisplay && transformedDisplay.value && transformedDisplay.value.trim() !== '';
        
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

// Generate Deliverables
async function generateDeliverables() {
    const manifestSelect = document.getElementById('deliverablesManifest');
    const statusDiv = document.getElementById('deliverablesStatus');
    const statusText = document.getElementById('deliverablesStatusText');
    const generateBtn = document.getElementById('generateDeliverablesBtn');
    
    if (!manifestSelect || !statusDiv || !statusText || !generateBtn) {
        showError('Deliverables UI elements not found');
        return;
    }
    
    const manifestPath = manifestSelect.value;
    
    if (!confirm(`This will generate comprehensive Phase 1 and Phase 2 deliverables.\n\nThis may take a while depending on the number of audio files.\n\nManifest: ${manifestPath}\n\nContinue?`)) {
        return;
    }
    
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generating...';
    statusDiv.style.display = 'block';
    statusText.textContent = 'Starting generation...';
    
    try {
        const formData = new FormData();
        formData.append('manifest_path', manifestPath);
        formData.append('phase', 'both');
        
        const response = await fetch(`${API_BASE}/process/generate-deliverables`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'started') {
            statusText.textContent = 'Generation started. Check logs for progress...';
            startProcessMonitoring(result.command_id, 'Generating deliverables...', 'Generate Deliverables');
            addSystemLog(`Started generating deliverables: ${manifestPath}`, 'info');
            
            // Poll for completion and reload deliverables
            const checkInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`${API_BASE}/process/${result.command_id}/status`);
                    const status = await statusRes.json();
                    
                    if (status.status === 'completed') {
                        clearInterval(checkInterval);
                        statusText.textContent = '✅ Generation complete!';
                        generateBtn.disabled = false;
                        generateBtn.textContent = '📦 Generate Phase 1 & Phase 2 Deliverables';
                        addSystemLog('Deliverables generation completed', 'success');
                        // Reload deliverables list
                        setTimeout(() => loadDeliverables(), 2000);
                    } else if (status.status === 'error') {
                        clearInterval(checkInterval);
                        statusText.textContent = '❌ Generation failed';
                        generateBtn.disabled = false;
                        generateBtn.textContent = '📦 Generate Phase 1 & Phase 2 Deliverables';
                        addSystemLog('Deliverables generation failed', 'error');
                    }
                } catch (error) {
                    console.error('Error checking status:', error);
                }
            }, 3000);
        } else {
            throw new Error(result.message || 'Failed to start generation');
        }
    } catch (error) {
        showError('Failed to start deliverables generation: ' + error.message);
        generateBtn.disabled = false;
        generateBtn.textContent = '📦 Generate Phase 1 & Phase 2 Deliverables';
        statusText.textContent = '❌ Error: ' + error.message;
    }
}

async function generatePhase1Only() {
    const manifestSelect = document.getElementById('deliverablesManifest');
    const generateBtn = document.getElementById('generatePhase1Btn');
    
    if (!manifestSelect || !generateBtn) {
        showError('UI elements not found');
        return;
    }
    
    const manifestPath = manifestSelect.value;
    
    if (!confirm(`Generate Phase 1 deliverables only?\n\nManifest: ${manifestPath}`)) {
        return;
    }
    
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generating Phase 1...';
    
    try {
        const formData = new FormData();
        formData.append('manifest_path', manifestPath);
        formData.append('phase', 'phase1');
        
        const response = await fetch(`${API_BASE}/process/generate-deliverables`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'started') {
            startProcessMonitoring(result.command_id, 'Generating Phase 1 deliverables...', 'Generate Phase 1');
            addSystemLog(`Started generating Phase 1 deliverables: ${manifestPath}`, 'info');
            
            setTimeout(() => {
                generateBtn.disabled = false;
                generateBtn.textContent = '📊 Generate Phase 1 Only';
                loadDeliverables();
            }, 5000);
        } else {
            throw new Error(result.message || 'Failed to start');
        }
    } catch (error) {
        showError('Failed to start Phase 1 generation: ' + error.message);
        generateBtn.disabled = false;
        generateBtn.textContent = '📊 Generate Phase 1 Only';
    }
}

async function generatePhase2Only() {
    const manifestSelect = document.getElementById('deliverablesManifest');
    const generateBtn = document.getElementById('generatePhase2Btn');
    
    if (!manifestSelect || !generateBtn) {
        showError('UI elements not found');
        return;
    }
    
    const manifestPath = manifestSelect.value;
    
    if (!confirm(`Generate Phase 2 deliverables only?\n\nManifest: ${manifestPath}`)) {
        return;
    }
    
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Generating Phase 2...';
    
    try {
        const formData = new FormData();
        formData.append('manifest_path', manifestPath);
        formData.append('phase', 'phase2');
        
        const response = await fetch(`${API_BASE}/process/generate-deliverables`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'started') {
            startProcessMonitoring(result.command_id, 'Generating Phase 2 deliverables...', 'Generate Phase 2');
            addSystemLog(`Started generating Phase 2 deliverables: ${manifestPath}`, 'info');
            
            setTimeout(() => {
                generateBtn.disabled = false;
                generateBtn.textContent = '📊 Generate Phase 2 Only';
                loadDeliverables();
            }, 5000);
        } else {
            throw new Error(result.message || 'Failed to start');
        }
    } catch (error) {
        showError('Failed to start Phase 2 generation: ' + error.message);
        generateBtn.disabled = false;
        generateBtn.textContent = '📊 Generate Phase 2 Only';
    }
}

// Deliverables & Reports
async function loadDeliverables() {
    try {
        const response = await fetch(`${API_BASE}/runs`);
        const result = await response.json();
        
        const deliverablesListDiv = document.getElementById('deliverablesList');
        
        if (!deliverablesListDiv) {
            console.error('deliverablesList element not found');
            return;
        }
        
        if (result.runs && result.runs.length > 0) {
            // Group runs by phase (detect from path or ID)
            const phase1Runs = [];
            const phase2Runs = [];
            const otherRuns = [];
            
            result.runs.forEach(run => {
                const runPath = (run.path || '').toLowerCase();
                const runId = (run.id || '').toLowerCase();
                
                // Check if it's Phase 1 or Phase 2
                if (runPath.includes('phase1') || runId.includes('phase1') || 
                    runPath.includes('phase_1') || runId.includes('phase_1')) {
                    phase1Runs.push(run);
                } else if (runPath.includes('phase2') || runId.includes('phase2') || 
                          runPath.includes('phase_2') || runId.includes('phase_2')) {
                    phase2Runs.push(run);
                } else {
                    // Check final_report directory for phase indicators
                    const finalReportPath = `${run.path}/final_report/report.html`;
                    otherRuns.push(run);
                }
            });
            
            let html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">';
            
            // Phase 1 Section
            html += '<div class="group-box" style="background: #1e1e1e; padding: 20px; border-radius: 8px; border: 2px solid #427eea;">';
            html += '<h4 style="color: #427eea; margin-bottom: 15px; font-size: 1.2em;">📈 Phase 1: Core Manipulation</h4>';
            if (phase1Runs.length > 0) {
                phase1Runs.forEach(run => {
                    const date = new Date(run.timestamp * 1000).toLocaleString();
                    const reportPath = `${run.path}/final_report/report.html`;
                    const hasReport = run.has_summary || run.has_metrics;
                    
                    html += `
                        <div style="padding: 15px; margin-bottom: 12px; background: #2d2d2d; border-radius: 6px; border: 1px solid #3d3d3d; transition: all 0.2s;" 
                             onmouseover="this.style.borderColor='#427eea'; this.style.background='#2d3d4d';" 
                             onmouseout="this.style.borderColor='#3d3d3d'; this.style.background='#2d2d2d';">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div style="flex: 1;">
                                    <strong style="color: #ffffff; font-size: 14px; display: block; margin-bottom: 5px;">${run.id}</strong>
                                    <p style="color: #9ca3af; font-size: 11px; margin: 0 0 8px 0;">${date}</p>
                                    ${hasReport ? '<span style="background: #10b981; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 10px;">Complete</span>' : 
                                      '<span style="background: #f59e0b; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 10px;">In Progress</span>'}
                                </div>
                                <div style="display: flex; gap: 8px; margin-left: 10px;">
                                    ${hasReport ? `<button class="btn" onclick="viewReport('${reportPath}', '${run.id}')" style="font-size: 12px; padding: 6px 12px;">View Report</button>` : ''}
                                    <button class="btn" onclick="viewRunDetails('${run.id}')" style="font-size: 12px; padding: 6px 12px; background: #3d3d3d;">Details</button>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                html += '<p style="color: #9ca3af; padding: 20px; text-align: center;">No Phase 1 reports found.<br><small>Run Phase 1 tests to generate reports.</small></p>';
            }
            html += '</div>';
            
            // Phase 2 Section
            html += '<div class="group-box" style="background: #1e1e1e; padding: 20px; border-radius: 8px; border: 2px solid #10b981;">';
            html += '<h4 style="color: #10b981; margin-bottom: 15px; font-size: 1.2em;">📈 Phase 2: Structural Manipulation</h4>';
            if (phase2Runs.length > 0) {
                phase2Runs.forEach(run => {
                    const date = new Date(run.timestamp * 1000).toLocaleString();
                    const reportPath = `${run.path}/final_report/report.html`;
                    const hasReport = run.has_summary || run.has_metrics;
                    
                    html += `
                        <div style="padding: 15px; margin-bottom: 12px; background: #2d2d2d; border-radius: 6px; border: 1px solid #3d3d3d; transition: all 0.2s;" 
                             onmouseover="this.style.borderColor='#10b981'; this.style.background='#2d3d2d';" 
                             onmouseout="this.style.borderColor='#3d3d3d'; this.style.background='#2d2d2d';">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div style="flex: 1;">
                                    <strong style="color: #ffffff; font-size: 14px; display: block; margin-bottom: 5px;">${run.id}</strong>
                                    <p style="color: #9ca3af; font-size: 11px; margin: 0 0 8px 0;">${date}</p>
                                    ${hasReport ? '<span style="background: #10b981; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 10px;">Complete</span>' : 
                                      '<span style="background: #f59e0b; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 10px;">In Progress</span>'}
                                </div>
                                <div style="display: flex; gap: 8px; margin-left: 10px;">
                                    ${hasReport ? `<button class="btn" onclick="viewReport('${reportPath}', '${run.id}')" style="font-size: 12px; padding: 6px 12px;">View Report</button>` : ''}
                                    <button class="btn" onclick="viewRunDetails('${run.id}')" style="font-size: 12px; padding: 6px 12px; background: #3d3d3d;">Details</button>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                html += '<p style="color: #9ca3af; padding: 20px; text-align: center;">No Phase 2 reports found.<br><small>Run Phase 2 tests to generate reports.</small></p>';
            }
            html += '</div>';
            
            html += '</div>';
            
            // Other runs section
            if (otherRuns.length > 0) {
                html += '<div class="group-box" style="margin-top: 20px; background: #1e1e1e; padding: 20px; border-radius: 8px; border: 1px solid #3d3d3d;">';
                html += '<h4 style="color: #9ca3af; margin-bottom: 15px; font-size: 1.1em;">📊 Other Reports</h4>';
                otherRuns.forEach(run => {
                    const date = new Date(run.timestamp * 1000).toLocaleString();
                    const reportPath = `${run.path}/final_report/report.html`;
                    const hasReport = run.has_summary || run.has_metrics;
                    
                    html += `
                        <div style="padding: 12px; margin-bottom: 10px; background: #2d2d2d; border-radius: 6px; border: 1px solid #3d3d3d;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="color: #ffffff; font-size: 13px;">${run.id}</strong>
                                    <p style="color: #9ca3af; font-size: 10px; margin: 3px 0 0 0;">${date}</p>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    ${hasReport ? `<button class="btn" onclick="viewReport('${reportPath}', '${run.id}')" style="font-size: 11px; padding: 5px 10px;">View</button>` : ''}
                                    <button class="btn" onclick="viewRunDetails('${run.id}')" style="font-size: 11px; padding: 5px 10px; background: #3d3d3d;">Details</button>
                                </div>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }
            
            deliverablesListDiv.innerHTML = html;
        } else {
            deliverablesListDiv.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #9ca3af;">
                    <p style="font-size: 16px; margin-bottom: 10px;">No deliverables found</p>
                    <p style="font-size: 12px;">Run experiments using <code>generate_deliverables.py</code> to generate Phase 1 and Phase 2 reports.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to load deliverables:', error);
        const deliverablesListDiv = document.getElementById('deliverablesList');
        if (deliverablesListDiv) {
            deliverablesListDiv.innerHTML = `
                <div style="padding: 20px; background: #3a1e1e; border-radius: 6px; border: 1px solid #f87171;">
                    <p style="color: #f87171; margin: 0;">Error loading deliverables: ${error.message}</p>
                </div>
            `;
        }
    }
}

function viewReport(reportPath, runId) {
    // Open report HTML in new tab
    const url = `/api/files/report?path=${encodeURIComponent(reportPath)}`;
    window.open(url, '_blank');
}

async function viewRunDetails(runId) {
    try {
        const response = await fetch(`${API_BASE}/runs/${runId}`);
        const result = await response.json();
        
        const reportViewerDiv = document.getElementById('reportViewer');
        const visualReportViewerDiv = document.getElementById('visualReportViewer');
        
        if (!reportViewerDiv) {
            console.error('reportViewer element not found');
            return;
        }
        
        let html = '<div style="background: #1e1e1e; padding: 20px; border-radius: 8px; border: 1px solid #3d3d3d;">';
        html += `<h4 style="color: #ffffff; margin-bottom: 15px; border-bottom: 2px solid #427eea; padding-bottom: 10px;">Report: ${runId}</h4>`;
        
        if (result.metrics) {
            html += '<div style="margin-bottom: 20px;">';
            html += '<h5 style="color: #427eea; margin-bottom: 10px; font-size: 14px;">📊 Metrics Summary</h5>';
            const summary = result.metrics.summary || {};
            html += `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">`;
            html += `<div style="padding: 10px; background: #2d2d2d; border-radius: 4px;"><strong style="color: #9ca3af; font-size: 11px;">Total Queries</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 18px;">${summary.total_queries || 'N/A'}</p></div>`;
            html += `<div style="padding: 10px; background: #2d2d2d; border-radius: 4px;"><strong style="color: #9ca3af; font-size: 11px;">Total Transforms</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 18px;">${summary.total_transforms || 'N/A'}</p></div>`;
            html += `</div>`;
            
            if (result.metrics.overall) {
                html += '<h5 style="color: #427eea; margin-top: 15px; margin-bottom: 10px; font-size: 14px;">🎯 Overall Performance</h5>';
                const recall = result.metrics.overall.recall || {};
                const rank = result.metrics.overall.rank || {};
                const similarity = result.metrics.overall.similarity || {};
                
                html += `<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 10px;">`;
                html += `<div style="padding: 12px; background: #2d2d2d; border-radius: 4px; border-left: 3px solid #427eea;"><strong style="color: #9ca3af; font-size: 11px;">Recall@1</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 20px; font-weight: bold;">${((recall.recall_at_1 || 0) * 100).toFixed(1)}%</p></div>`;
                html += `<div style="padding: 12px; background: #2d2d2d; border-radius: 4px; border-left: 3px solid #10b981;"><strong style="color: #9ca3af; font-size: 11px;">Recall@5</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 20px; font-weight: bold;">${((recall.recall_at_5 || 0) * 100).toFixed(1)}%</p></div>`;
                html += `<div style="padding: 12px; background: #2d2d2d; border-radius: 4px; border-left: 3px solid #f59e0b;"><strong style="color: #9ca3af; font-size: 11px;">Recall@10</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 20px; font-weight: bold;">${((recall.recall_at_10 || 0) * 100).toFixed(1)}%</p></div>`;
                html += `</div>`;
                
                html += `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">`;
                html += `<div style="padding: 10px; background: #2d2d2d; border-radius: 4px;"><strong style="color: #9ca3af; font-size: 11px;">Mean Rank</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 16px;">${(rank.mean_rank || 0).toFixed(2)}</p></div>`;
                html += `<div style="padding: 10px; background: #2d2d2d; border-radius: 4px;"><strong style="color: #9ca3af; font-size: 11px;">Mean Similarity</strong><p style="color: #ffffff; margin: 5px 0 0 0; font-size: 16px;">${((similarity.mean_similarity_correct || 0) * 100).toFixed(1)}%</p></div>`;
                html += `</div>`;
            }
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
        
        html += '</div>';
        reportViewerDiv.innerHTML = html;
        
        // Also display in visual report viewer
        if (visualReportViewerDiv) {
            displayVisualReport(result, runId, visualReportViewerDiv);
        }
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

function displayVisualReport(result, runId, container) {
    if (!result.metrics) {
        container.innerHTML = '<p style="color: #9ca3af; text-align: center; padding: 40px;">No metrics available for this report.</p>';
        return;
    }
    
    const metrics = result.metrics;
    const testDetails = metrics.test_details || {};
    const overall = metrics.overall || {};
    const recall = overall.recall || {};
    const rank = overall.rank || {};
    const similarity = overall.similarity || {};
    const passFail = metrics.pass_fail || {};
    
    const matched = testDetails.matched !== undefined ? testDetails.matched : (passFail.passed > 0);
    const statusColor = matched ? '#10b981' : '#f87171';
    const statusText = matched ? '✅ MATCHED' : '❌ NOT MATCHED';
    
    let html = `
        <div style="background: #1e1e1e; padding: 25px; border-radius: 8px; border: 2px solid ${statusColor};">
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="color: ${statusColor}; margin: 0; font-size: 32px;">${statusText}</h2>
                <p style="color: #9ca3af; margin: 10px 0 0 0;">Report ID: ${runId}</p>
                ${testDetails.phase ? `<p style="color: #9ca3af; margin: 5px 0 0 0;">Phase: ${testDetails.phase.toUpperCase()}</p>` : ''}
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px;">
                <div style="background: #2d2d2d; padding: 20px; border-radius: 6px; border-left: 4px solid #427eea; text-align: center;">
                    <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Recall@1</div>
                    <div style="color: #ffffff; font-size: 28px; font-weight: bold;">${((recall.recall_at_1 || 0) * 100).toFixed(1)}%</div>
                </div>
                <div style="background: #2d2d2d; padding: 20px; border-radius: 6px; border-left: 4px solid #10b981; text-align: center;">
                    <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Recall@5</div>
                    <div style="color: #ffffff; font-size: 28px; font-weight: bold;">${((recall.recall_at_5 || 0) * 100).toFixed(1)}%</div>
                </div>
                <div style="background: #2d2d2d; padding: 20px; border-radius: 6px; border-left: 4px solid #f59e0b; text-align: center;">
                    <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Recall@10</div>
                    <div style="color: #ffffff; font-size: 28px; font-weight: bold;">${((recall.recall_at_10 || 0) * 100).toFixed(1)}%</div>
                </div>
                <div style="background: #2d2d2d; padding: 20px; border-radius: 6px; border-left: 4px solid #8b5cf6; text-align: center;">
                    <div style="color: #9ca3af; font-size: 12px; margin-bottom: 8px;">Similarity</div>
                    <div style="color: #ffffff; font-size: 28px; font-weight: bold;">${((similarity.mean_similarity_correct || testDetails.similarity || 0) * 100).toFixed(1)}%</div>
                </div>
            </div>
            
            ${testDetails.original_file ? `
            <div style="background: #2d2d2d; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
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
    
    container.innerHTML = html;
}
