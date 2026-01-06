/**
 * Audio Manipulation Component
 * Handles all audio transformation functions and file management
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    formatBytes,
    formatTime,
    getElement
} from '../utils/helpers.js';
import {
    showError,
    showCompletionAlert,
    addSystemLog
} from './notifications.js';

class AudioManipulationManager {
    constructor() {
        this.transformChain = [];
        this.selectedAudioFile = null;
        this.originalAudioPlaying = false;
        this.transformedAudioPlaying = false;
    }

    async loadManipulateAudioFiles() {
        console.log('loadManipulateAudioFiles called');

        // Show loading state
        const audioSelect = getElement('manipulateAudioFile');
        if (audioSelect) {
            audioSelect.innerHTML = '<option value="">Loading audio files...</option>';
        }

        // Load audio files from all directories
        const directories = ['originals', 'transformed', 'test_audio', 'manipulated'];
        const allFiles = [];

        for (const dir of directories) {
            try {
                const response = await fetch(`${API_CONFIG.BASE_URL}/files/audio?directory=${dir}`);
                const result = await response.json();
                if (result.files) {
                    allFiles.push(...result.files);
                }
            } catch (error) {
                console.error(`Failed to load files from ${dir}:`, error);
            }
        }

        const select = getElement('manipulateAudioFile');
        if (!select) return;

        select.innerHTML = '<option value="">-- Select Audio File --</option>';

        // Also populate embedded sample and song A in Song B selectors (Manipulate Audio section)
        const embeddedBackgroundSelect = getElement('embeddedBackgroundFile');
        const songBBaseSelect = getElement('songBBaseFile');

        // Also populate Deliverables section selectors
        const deliverablesEmbeddedSampleSelect = getElement('deliverablesEmbeddedSampleFile');
        const deliverablesEmbeddedBackgroundSelect = getElement('deliverablesEmbeddedBackgroundFile');
        const deliverablesSongASelect = getElement('deliverablesSongAFile');
        const deliverablesSongBBaseSelect = getElement('deliverablesSongBBaseFile');

        if (embeddedBackgroundSelect) {
            embeddedBackgroundSelect.innerHTML = '<option value="">-- Select Background File --</option>';
        }
        if (songBBaseSelect) {
            songBBaseSelect.innerHTML = '<option value="">-- Generate Synthetic Background --</option>';
        }
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

        allFiles.forEach(file => {
            const option = document.createElement('option');
            option.value = file.path;
            option.textContent = `${file.name} (${formatBytes(file.size)})`;
            select.appendChild(option);

            // Also add to embedded sample and song B selectors (Manipulate Audio section)
            if (embeddedBackgroundSelect) {
                const opt1 = option.cloneNode(true);
                embeddedBackgroundSelect.appendChild(opt1);
            }
            if (songBBaseSelect) {
                const opt2 = option.cloneNode(true);
                songBBaseSelect.appendChild(opt2);
            }

            // Also add to Deliverables section selectors
            if (deliverablesEmbeddedSampleSelect) {
                const sampleOption = option.cloneNode(true);
                deliverablesEmbeddedSampleSelect.appendChild(sampleOption);
            }
            if (deliverablesEmbeddedBackgroundSelect) {
                const bgDeliverablesOption = option.cloneNode(true);
                deliverablesEmbeddedBackgroundSelect.appendChild(bgDeliverablesOption);
            }
            if (deliverablesSongASelect) {
                const songAOption = option.cloneNode(true);
                deliverablesSongASelect.appendChild(songAOption);
            }
            if (deliverablesSongBBaseSelect) {
                const songBBaseDeliverablesOption = option.cloneNode(true);
                deliverablesSongBBaseSelect.appendChild(songBBaseDeliverablesOption);
            }
        });

        // Update displays when selected file changes
        if (select) {
            select.addEventListener('change', () => {
                const filePath = select.value;
                if (filePath) {
                    const fileName = filePath.split('/').pop();
                    const embeddedDisplay = getElement('embeddedSampleFileDisplay');
                    const songADisplay = getElement('songAFileDisplay');
                    if (embeddedDisplay) embeddedDisplay.textContent = fileName;
                    if (songADisplay) songADisplay.textContent = fileName;
                }
            });
        }
    }

    loadAudioInfo() {
        const select = getElement('manipulateAudioFile');
        if (!select) {
            console.error('[loadAudioInfo] manipulateAudioFile select not found!');
            return;
        }

        const filePath = select.value;
        console.log('[loadAudioInfo] Selected file path:', filePath);

        if (!filePath) {
            const audioInfo = getElement('audioInfo');
            if (audioInfo) audioInfo.style.display = 'none';
            this.selectedAudioFile = null;
            this.updateTestDisplays(null, null);
            this.updateOriginalPlayer(null);
            console.log('[loadAudioInfo] No file selected, cleared displays');
            return;
        }

        this.selectedAudioFile = filePath;
        const fileName = (select.options[select.selectedIndex] && select.options[select.selectedIndex].textContent) || filePath.split('/').pop();

        const selectedFileName = getElement('selectedFileName');
        const selectedFilePath = getElement('selectedFilePath');
        const audioInfo = getElement('audioInfo');

        if (selectedFileName) selectedFileName.textContent = fileName;
        if (selectedFilePath) selectedFilePath.textContent = filePath;
        if (audioInfo) audioInfo.style.display = 'block';

        console.log('[loadAudioInfo] Updated audio info display with:', fileName);

        // Update original audio player
        this.updateOriginalPlayer(filePath);

        // Update original test display in "Test Fingerprint Robustness" section
        // Preserve existing transformed path if it exists
        const transformedDisplay = getElement('transformedTestDisplay');
        const existingTransformed = transformedDisplay ?.value ?.trim() || null;
        console.log('[loadAudioInfo] Updating test displays - Original:', filePath, 'Transformed (preserved):', existingTransformed);
        this.updateTestDisplays(filePath, existingTransformed);

        console.log('[loadAudioInfo] ✅ Original audio set in Test Fingerprint Robustness section');
    }

    clearAudioSelection() {
        const select = getElement('manipulateAudioFile');
        if (select) {
            select.value = '';
            this.loadAudioInfo();
        }
    }

    updateOverlayFileName() {
        const fileInput = getElement('overlayFile');
        const fileNameDisplay = getElement('overlayFileName');
        if (fileInput && fileNameDisplay) {
            if (fileInput.files && fileInput.files.length > 0) {
                fileNameDisplay.textContent = fileInput.files[0].name;
            } else {
                fileNameDisplay.textContent = 'No file chosen';
            }
        }
    }

    updateDeliverablesOverlayFileName() {
        const fileInput = getElement('deliverablesOverlayFile');
        const fileNameDisplay = getElement('deliverablesOverlayFileName');
        if (fileInput && fileNameDisplay) {
            if (fileInput.files && fileInput.files.length > 0) {
                fileNameDisplay.textContent = fileInput.files[0].name;
            } else {
                fileNameDisplay.textContent = 'No file chosen';
            }
        }
    }

    generateWaveform(container, filePath) {
        // Simple waveform visualization - can be enhanced later
        if (!container) return;

        const bars = [];
        for (let i = 0; i < 50; i++) {
            const height = Math.random() * 60 + 20;
            bars.push(`<div class="waveform-bar" style="height: ${height}%;"></div>`);
        }
        container.innerHTML = `<div class="waveform-bars">${bars.join('')}</div>`;
    }

    updateOriginalPlayer(filePath) {
        const player = getElement('originalAudioPlayer');
        const playBtn = getElement('originalPlayBtn');
        const infoDiv = getElement('originalPlayerInfo');
        const waveformDiv = getElement('originalWaveform');
        const testStatus = getElement('originalTestStatus');

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
            this.originalAudioPlaying = false;
            return;
        }

        if (player) {
            player.src = `${API_CONFIG.BASE_URL}/files/audio-file?path=${encodeURIComponent(filePath)}`;
            player.load();
            player.onpause = () => {
                if (playBtn) playBtn.textContent = '▶';
                this.originalAudioPlaying = false;
                if (window.stopFrequencyVisualization) window.stopFrequencyVisualization();
            };
            player.onended = () => {
                if (playBtn) playBtn.textContent = '▶';
                this.originalAudioPlaying = false;
                if (window.stopFrequencyVisualization) window.stopFrequencyVisualization();
            };
        player.onloadedmetadata = () => {
            // Load waveform when audio metadata is loaded
            if (window.audioPlayerManager && window.audioPlayerManager.loadWaveformData) {
                window.audioPlayerManager.loadWaveformData(player);
            }
            // Update waveform display with actual duration
            if (window.updateWaveformDisplay) {
                window.updateWaveformDisplay();
            }
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
            this.generateWaveform(waveformDiv, filePath);
        }
        if (testStatus) {
            testStatus.textContent = filePath.split('/').pop();
        }
        this.originalAudioPlaying = false;
    }

    updateTransformedPlayer(filePath) {
        console.log('[updateTransformedPlayer] Called with filePath:', filePath);

        const player = getElement('transformedAudioPlayer');
        const playBtn = getElement('transformedPlayBtn');
        const infoDiv = getElement('transformedPlayerInfo');
        const waveformDiv = getElement('transformedWaveform');
        const testStatus = getElement('transformedTestStatus');

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
            this.transformedAudioPlaying = false;
            return;
        }

        if (!player) {
            console.error('[updateTransformedPlayer] Player element not found!');
            return;
        }

        const audioUrl = `${API_CONFIG.BASE_URL}/files/audio-file?path=${encodeURIComponent(filePath)}`;
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
            // Load waveform when audio is loaded
            if (window.audioPlayerManager && window.audioPlayerManager.loadWaveformData) {
                window.audioPlayerManager.loadWaveformData(player);
            }
            // Update waveform display with actual duration
            if (window.updateWaveformDisplay) {
                window.updateWaveformDisplay();
            }
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
            this.transformedAudioPlaying = false;
        };
        player.onended = () => {
            if (playBtn) playBtn.textContent = '▶';
            this.transformedAudioPlaying = false;
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
            this.generateWaveform(waveformDiv, filePath);
        }
        if (testStatus) {
            testStatus.textContent = filePath.split('/').pop();
        }
        this.transformedAudioPlaying = false;
    }

    toggleOriginalPlayback() {
        const player = getElement('originalAudioPlayer');
        const playBtn = getElement('originalPlayBtn');

        if (!player || !playBtn || !player.src) return;

        if (this.originalAudioPlaying) {
            player.pause();
            playBtn.textContent = '▶';
            this.originalAudioPlaying = false;
            if (window.stopFrequencyVisualization) window.stopFrequencyVisualization();
        } else {
            // Pause transformed if playing
            const transformedPlayer = getElement('transformedAudioPlayer');
            if (this.transformedAudioPlaying && transformedPlayer) {
                transformedPlayer.pause();
                const transformedBtn = getElement('transformedPlayBtn');
                if (transformedBtn) transformedBtn.textContent = '▶';
                this.transformedAudioPlaying = false;
            }
            player.play().catch(err => {
                console.error('Error playing audio:', err);
                showError('Error playing audio: ' + err.message);
            });
            playBtn.textContent = '⏸';
            this.originalAudioPlaying = true;
            if (window.startFrequencyVisualization) window.startFrequencyVisualization(player);
        }
    }

    toggleTransformedPlayback() {
        const player = getElement('transformedAudioPlayer');
        const playBtn = getElement('transformedPlayBtn');

        if (!player || !playBtn || !player.src) return;

        if (this.transformedAudioPlaying) {
            player.pause();
            playBtn.textContent = '▶';
            this.transformedAudioPlaying = false;
            if (window.stopFrequencyVisualization) window.stopFrequencyVisualization();
        } else {
            // Pause original if playing
            const originalPlayer = getElement('originalAudioPlayer');
            if (this.originalAudioPlaying && originalPlayer) {
                originalPlayer.pause();
                const originalBtn = getElement('originalPlayBtn');
                if (originalBtn) originalBtn.textContent = '▶';
                this.originalAudioPlaying = false;
            }
            player.play().catch(err => {
                console.error('Error playing audio:', err);
                showError('Error playing audio: ' + err.message);
            });
            playBtn.textContent = '⏸';
            this.transformedAudioPlaying = true;
            if (window.startFrequencyVisualization) window.startFrequencyVisualization(player);
        }
    }

    updateOriginalTime() {
        const player = getElement('originalAudioPlayer');
        const label = getElement('originalTimeLabel');
        const playBtn = getElement('originalPlayBtn');

        if (!player || !label) return;

        if (player.ended) {
            if (playBtn) playBtn.textContent = '▶';
            this.originalAudioPlaying = false;
            if (window.stopFrequencyVisualization) window.stopFrequencyVisualization();
        }

        const current = formatTime(player.currentTime);
        const duration = formatTime(player.duration || 0);
        label.textContent = `${current} / ${duration}`;

        // Update playhead position
        if (player.duration) {
            const percentage = (player.currentTime / player.duration) * 100;
            if (window.updatePlayheadPosition) window.updatePlayheadPosition(percentage / 100);
        }
    }

    updateTransformedTime() {
        const player = getElement('transformedAudioPlayer');
        const label = getElement('transformedTimeLabel');
        const playBtn = getElement('transformedPlayBtn');

        if (!player || !label) return;

        if (player.ended) {
            if (playBtn) playBtn.textContent = '▶';
            this.transformedAudioPlaying = false;
            if (window.stopFrequencyVisualization) window.stopFrequencyVisualization();
        }

        const current = formatTime(player.currentTime);
        const duration = formatTime(player.duration || 0);
        label.textContent = `${current} / ${duration}`;

        // Update playhead position
        if (player.duration) {
            const percentage = (player.currentTime / player.duration) * 100;
            if (window.updatePlayheadPosition) window.updatePlayheadPosition(percentage / 100);
        }
    }

    updateOriginalDuration() {
        this.updateOriginalTime();
    }

    updateTransformedDuration() {
        this.updateTransformedTime();
    }

    // Handle file upload in manipulate section
    handleManipulateDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        const uploadArea = getElement('manipulateUploadArea');
        if (uploadArea) uploadArea.classList.remove('dragover');

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.handleManipulateFileUpload(files[0]);
        }
    }

    handleManipulateFileSelect(event) {
        const files = event.target.files;
        if (files.length > 0) {
            this.handleManipulateFileUpload(files[0]);
        }
    }

    async handleManipulateFileUpload(file) {
        if (!file.type.startsWith('audio/')) {
            showError('Please select an audio file');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('directory', 'data/originals');

            const response = await fetch(`${API_CONFIG.BASE_URL}/upload/audio`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(`File uploaded: ${result.path}`);
                addSystemLog(`Audio file uploaded: ${result.path}`, 'success');

                // Reload file list and select the uploaded file
                await this.loadManipulateAudioFiles();
                const select = getElement('manipulateAudioFile');
                if (select) {
                    select.value = result.path;
                    this.loadAudioInfo();
                }
            } else {
                showError(result.message || 'Upload failed');
            }
        } catch (error) {
            showError('Failed to upload file: ' + error.message);
        }
    }

    async applySpeedTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const speedSlider = getElement('speedSlider');
        if (!speedSlider) {
            showError('Speed slider not found');
            return;
        }
        const speedRatio = parseFloat(speedSlider.value) / 100.0;
        const preservePitchEl = getElement('preservePitch');
        const preservePitch = (preservePitchEl && preservePitchEl.checked) || false;
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('speed_ratio', speedRatio);
            formData.append('preserve_pitch', preservePitch);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/speed`, {
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
                addSystemLog(`Speed transform applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply speed transform: ' + error.message);
        }
    }

    async applyPitchTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const pitchSlider = getElement('pitchSlider');
        if (!pitchSlider) {
            showError('Pitch slider not found');
            return;
        }
        const semitones = parseInt(pitchSlider.value);
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('semitones', semitones);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/pitch`, {
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
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply pitch transform: ' + error.message);
        }
    }

    async applyReverbTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const reverbSlider = getElement('reverbSlider');
        if (!reverbSlider) {
            showError('Reverb slider not found');
            return;
        }
        const delayMs = parseInt(reverbSlider.value);
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('delay_ms', delayMs);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/reverb`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Reverb transform applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply reverb transform: ' + error.message);
        }
    }

    async applyNoiseReductionTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const noiseSlider = getElement('noiseSlider');
        if (!noiseSlider) {
            showError('Noise slider not found');
            return;
        }
        const reductionPercent = parseInt(noiseSlider.value);
        const reductionStrength = reductionPercent / 100.0;
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('reduction_strength', reductionStrength);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/noise-reduction`, {
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
                addSystemLog(`Noise reduction applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply noise reduction: ' + error.message);
        }
    }

    async applyEQTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const eqSlider = getElement('eqSlider');
        if (!eqSlider) {
            showError('EQ slider not found');
            return;
        }
        const gainDb = parseInt(eqSlider.value);
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('gain_db', gainDb);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/eq`, {
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
                addSystemLog(`EQ transform applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply EQ transform: ' + error.message);
        }
    }

    async applyCompressionTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const codecSelect = getElement('codecSelect');
        if (!codecSelect) {
            showError('Codec select not found');
            return;
        }
        const codec = codecSelect.value;
        if (codec === 'None') {
            showError('Please select a codec');
            return;
        }

        const bitrateSelect = getElement('bitrateSelect');
        if (!bitrateSelect) {
            showError('Bitrate select not found');
            return;
        }
        const bitrate = bitrateSelect.value;
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('codec', codec.toLowerCase());
            formData.append('bitrate', bitrate);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/encode`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Compression applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply compression: ' + error.message);
        }
    }

    async applyOverlayTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const overlayFileInput = getElement('overlayFile');
        const overlayFile = (overlayFileInput && overlayFileInput.files && overlayFileInput.files[0]) || null;

        const overlayGainSlider = getElement('overlayGainSlider');
        if (!overlayGainSlider) {
            showError('Overlay gain slider not found');
            return;
        }
        const gainDb = parseInt(overlayGainSlider.value);
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('gain_db', gainDb);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            let overlayPath = null;
            if (overlayFile) {
                const uploadFormData = new FormData();
                uploadFormData.append('file', overlayFile);
                uploadFormData.append('directory', 'data/manipulated');

                const uploadResponse = await fetch(`${API_CONFIG.BASE_URL}/upload/audio`, {
                    method: 'POST',
                    body: uploadFormData
                });

                const uploadResult = await uploadResponse.json();
                if (uploadResult.status === 'success') {
                    overlayPath = uploadResult.path;
                    formData.append('overlay_path', overlayPath);
                }
            }

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/overlay`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Overlay transform applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply overlay transform: ' + error.message);
        }
    }

    async applyNoiseTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const snrDb = 20;
        const noiseType = 'white';
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('snr_db', snrDb);
            formData.append('noise_type', noiseType);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/noise`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Noise transform applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply noise transform: ' + error.message);
        }
    }

    async applyEncodeTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const codec = getElement('encodeCodec').value;
        const bitrate = getElement('encodeBitrate').value;
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputName = getElement('manipulateOutputName').value || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('codec', codec);
            formData.append('bitrate', bitrate);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/encode`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Encode transform applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply encode transform: ' + error.message);
        }
    }

    async applyChopTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const removeStart = parseFloat(getElement('chopStart').value);
        const removeEnd = parseFloat(getElement('chopEnd').value);
        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputName = getElement('manipulateOutputName').value || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('remove_start', removeStart);
            formData.append('remove_end', removeEnd);
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/chop`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Chop transform applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply chop transform: ' + error.message);
        }
    }

    addToChain() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const speedSlider = getElement('speedSlider');
        const speedRatio = parseFloat(speedSlider.value) / 100.0;
        const preservePitch = getElement('preservePitch').checked;
        const pitchSemitones = parseInt(getElement('pitchSlider').value);
        const reverbMs = parseInt(getElement('reverbSlider').value);
        const noisePercent = parseInt(getElement('noiseSlider').value);
        const eqDb = parseInt(getElement('eqSlider').value);
        const codec = getElement('codecSelect').value;
        const bitrate = getElement('bitrateSelect').value;
        const overlayGain = parseInt(getElement('overlayGainSlider').value);

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

        this.transformChain.push(transform);
        this.updateChainDisplay();
        addSystemLog(`Added transform to chain: ${transform.description}`, 'info');
    }

    clearChain() {
        this.transformChain = [];
        this.updateChainDisplay();
        addSystemLog('Transform chain cleared', 'info');
    }

    updateChainDisplay() {
        const chainTextarea = getElement('chainList');
        if (!chainTextarea) return;

        if (this.transformChain.length === 0) {
            chainTextarea.value = 'No transforms in chain yet.';
            return;
        }

        let chainText = '';
        this.transformChain.forEach((t, i) => {
            chainText += `${i + 1}. ${t.description || t.type} (${JSON.stringify(t.params)})\n`;
        });

        chainTextarea.value = chainText;
    }

    removeFromChain(index) {
        this.transformChain.splice(index, 1);
        this.updateChainDisplay();
    }

    async applyChainTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        if (this.transformChain.length === 0) {
            showError('Please add transforms to the chain first');
            return;
        }

        const outputDirEl = getElement('manipulateOutputDir');
        const outputDir = (outputDirEl && outputDirEl.value) || 'data/manipulated';
        const outputNameEl = getElement('manipulateOutputName');
        const outputName = (outputNameEl && outputNameEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('transforms', JSON.stringify(this.transformChain));
            formData.append('output_dir', outputDir);
            if (outputName) formData.append('output_name', outputName);

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/chain`, {
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
                await this.loadManipulateAudioFiles();
                this.clearChain();
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    const originalDisplay = getElement('originalTestDisplay');
                    const existingOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim()) || this.selectedAudioFile || null;
                    this.updateTestDisplays(existingOriginal, result.output_path);
                    this.updateTransformedPlayer(result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply chain transform: ' + error.message);
        }
    }

    async loadTestFileSelects() {
        await this.loadManipulateAudioFiles();
    }

    async testFingerprintRobustness() {
        const originalDisplay = getElement('originalTestDisplay');
        const transformedDisplay = getElement('transformedTestDisplay');
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

        const resultDiv = getElement('testResults');
        const detailsDiv = getElement('testResultsContent');
        const testBtn = getElement('testBtn');

        resultDiv.style.display = 'block';
        resultDiv.className = 'test-results';
        testBtn.disabled = true;
        detailsDiv.innerHTML = '<p>🔄 Testing fingerprint match... This may take a moment.</p>';

        try {
            const formData = new FormData();
            formData.append('original_path', originalFile);
            formData.append('manipulated_path', manipulatedFile);

            const response = await fetch(`${API_CONFIG.BASE_URL}/test/fingerprint`, {
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
                const matchClass = result.matched ? 'success' : 'error';
                const similarityPercent = (result.similarity * 100).toFixed(1);

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
                        <h4 style="color: ${result.matched ? '#10b981' : '#f87171'}; margin: 0 0 10px 0;"></h4>
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

                addSystemLog(`Fingerprint test: (${similarityPercent}% similarity)`, result.matched ? 'success' : 'warning');
                
                // Update content-area height since test results are now shown
                this.updateManipulateContentHeight();
            } else {
                resultDiv.className = 'test-results error';
                detailsDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">Error: ${result.message || 'Test failed'}</pre>`;
                
                // Update content-area height since test results (error) are shown
                this.updateManipulateContentHeight();
            }
        } catch (error) {
            testBtn.disabled = false;
            resultDiv.className = 'test-results error';
            detailsDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">Error testing fingerprint: ${error.message}\n\nPlease ensure:\n1. Fingerprint model is properly configured\n2. Audio files are valid and accessible\n3. Required dependencies are installed</pre>`;
            
            // Update content-area height since test results (error) are shown
            this.updateManipulateContentHeight();
        }
    }

    updateManipulateContentHeight() {
        // Only update if we're currently on the manipulate section
        const manipulateSection = getElement('manipulate');
        if (!manipulateSection || !manipulateSection.classList.contains('active')) {
            return;
        }

        // Use window.navigationManager if available (set in app.js)
        if (window.navigationManager && typeof window.navigationManager.updateManipulateContentHeight === 'function') {
            const contentArea = document.querySelector('.content-area');
            if (contentArea) {
                window.navigationManager.updateManipulateContentHeight(contentArea);
            }
        } else {
            // Fallback: try dynamic import
            import('./navigation.js').then(({ navigationManager }) => {
                const contentArea = document.querySelector('.content-area');
                if (contentArea && typeof navigationManager.updateManipulateContentHeight === 'function') {
                    navigationManager.updateManipulateContentHeight(contentArea);
                }
            }).catch(() => {
                console.warn('Could not update manipulate content height');
            });
        }
    }

    async applyTransform(type) {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        switch (type) {
            case 'speed':
                await this.applySpeedTransform();
                break;
            case 'pitch':
                await this.applyPitchTransform();
                break;
            case 'reverb':
                await this.applyReverbTransform();
                break;
            case 'noise':
                await this.applyNoiseReductionTransform();
                break;
            case 'eq':
                await this.applyEQTransform();
                break;
            case 'compression':
                await this.applyCompressionTransform();
                break;
            case 'overlay':
                await this.applyOverlayTransform();
                break;
            case 'highpass':
                await this.applyHighpassTransform();
                break;
            case 'lowpass':
                await this.applyLowpassTransform();
                break;
            case 'boostHighs':
                await this.applyBoostHighsTransform();
                break;
            case 'boostLows':
                await this.applyBoostLowsTransform();
                break;
            case 'telephone':
                await this.applyTelephoneTransform();
                break;
            case 'limiting':
                await this.applyLimitingTransform();
                break;
            case 'multiband':
                await this.applyMultibandTransform();
                break;
            case 'addNoise':
                await this.applyAddNoiseTransform();
                break;
            case 'crop':
                await this.applyCropTransform();
                break;
            case 'embeddedSample':
                await this.applyEmbeddedSampleTransform();
                break;
            case 'songAInSongB':
                await this.applySongAInSongBTransform();
                break;
            default:
                showError(`Unknown transform type: ${type}`);
        }
    }

    updateSliderDisplay(type, value) {
        let displayElement;

        switch (type) {
            case 'highpass':
                displayElement = getElement('highpassDisplay');
                if (displayElement) displayElement.textContent = value + ' Hz';
                break;
            case 'lowpass':
                displayElement = getElement('lowpassDisplay');
                if (displayElement) displayElement.textContent = value + ' Hz';
                break;
            case 'boostHighs':
                displayElement = getElement('boostHighsDisplay');
                if (displayElement) displayElement.textContent = value + ' dB';
                break;
            case 'boostLows':
                displayElement = getElement('boostLowsDisplay');
                if (displayElement) displayElement.textContent = value + ' dB';
                break;
            case 'limiting':
                displayElement = getElement('limitingDisplay');
                if (displayElement) displayElement.textContent = value + ' dB';
                break;
            case 'noiseSNR':
                displayElement = getElement('noiseSNRDisplay');
                if (displayElement) displayElement.textContent = value + ' dB';
                break;
            default:
                displayElement = getElement(`${type}Display`);
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

    async applyHighpassTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const highpassSlider = getElement('highpassSlider');
        const freqHz = parseFloat((highpassSlider && highpassSlider.value) || 150);

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('freq_hz', freqHz);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/eq/highpass`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`High-pass filter applied: ${result.output_path}`, 'success');
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply high-pass filter: ' + error.message);
        }
    }

    async applyLowpassTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const lowpassSlider = getElement('lowpassSlider');
        const freqHz = parseFloat((lowpassSlider && lowpassSlider.value) || 6000);

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('freq_hz', freqHz);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/eq/lowpass`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Low-pass filter applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply low-pass filter: ' + error.message);
        }
    }

    async applyBoostHighsTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const boostHighsSlider = getElement('boostHighsSlider');
        const gainDb = parseFloat((boostHighsSlider && boostHighsSlider.value) || 6);

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('gain_db', gainDb);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/eq/boost-highs`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Boost highs applied: ${result.output_path}`, 'success');
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply boost highs: ' + error.message);
        }
    }

    async applyBoostLowsTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const boostLowsSlider = getElement('boostLowsSlider');
        const gainDb = parseFloat((boostLowsSlider && boostLowsSlider.value) || 6);

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('gain_db', gainDb);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/eq/boost-lows`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Boost lows applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply boost lows: ' + error.message);
        }
    }

    async applyTelephoneTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/eq/telephone`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Telephone filter applied: ${result.output_path}`, 'success');
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply telephone filter: ' + error.message);
        }
    }

    async applyLimitingTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const limitingSlider = getElement('limitingSlider');
        const ceilingDb = parseFloat((limitingSlider && limitingSlider.value) || -1);

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('ceiling_db', ceilingDb);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/dynamics/limiting`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Limiting applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply limiting: ' + error.message);
        }
    }

    async applyMultibandTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/dynamics/multiband`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Multiband compression applied: ${result.output_path}`, 'success');
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply multiband compression: ' + error.message);
        }
    }

    async applyAddNoiseTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const noiseTypeSelect = getElement('noiseTypeSelect');
        const noiseType = (noiseTypeSelect && noiseTypeSelect.value) || 'white';
        const noiseSNRSlider = getElement('noiseSNRSlider');
        const snrDb = parseFloat((noiseSNRSlider && noiseSNRSlider.value) || 20);

        try {
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('noise_type', noiseType);
            formData.append('snr_db', snrDb);
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/noise`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Noise added (${noiseType}): ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to add noise: ' + error.message);
        }
    }

    async applyCropTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select an audio file first');
            return;
        }

        const cropTypeSelect = getElement('cropTypeSelect');
        const cropType = (cropTypeSelect && cropTypeSelect.value) || '10s';

        try {
            let endpoint = '';
            const formData = new FormData();
            formData.append('input_path', this.selectedAudioFile);
            formData.append('output_dir', 'data/manipulated');

            switch (cropType) {
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

            const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Crop applied (${cropType}): ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                this.updateTransformedPlayer(result.output_path);
                this.updateTestDisplays(this.selectedAudioFile, result.output_path);
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply crop: ' + error.message);
        }
    }

    async applyEmbeddedSampleTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select a sample audio file first');
            return;
        }

        const embeddedBackgroundFileEl = getElement('embeddedBackgroundFile');
        const backgroundFile = embeddedBackgroundFileEl && embeddedBackgroundFileEl.value;
        if (!backgroundFile) {
            showError('Please select a background audio file');
            return;
        }

        const embeddedPositionEl = getElement('embeddedPosition');
        const position = (embeddedPositionEl && embeddedPositionEl.value) || 'start';
        const embeddedSampleDurationEl = getElement('embeddedSampleDuration');
        const sampleDuration = parseFloat((embeddedSampleDurationEl && embeddedSampleDurationEl.value) || '1.5');
        const embeddedVolumeDbEl = getElement('embeddedVolumeDb');
        const volumeDb = parseFloat((embeddedVolumeDbEl && embeddedVolumeDbEl.value) || '0.0');
        const embeddedApplyTransformEl = getElement('embeddedApplyTransform');
        const applyTransform = (embeddedApplyTransformEl && embeddedApplyTransformEl.value) || 'None';
        const embeddedTransformParamsEl = getElement('embeddedTransformParams');
        const transformParams = (embeddedTransformParamsEl && embeddedTransformParamsEl.value) || null;

        try {
            const formData = new FormData();
            formData.append('sample_path', this.selectedAudioFile);
            formData.append('background_path', backgroundFile);
            formData.append('position', position);
            formData.append('sample_duration', sampleDuration.toString());
            formData.append('volume_db', volumeDb.toString());
            formData.append('apply_transform', applyTransform);
            if (transformParams) {
                formData.append('transform_params', transformParams);
            }
            formData.append('output_dir', 'data/manipulated');

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/embedded-sample`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Embedded sample applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    this.updateTransformedPlayer(result.output_path);
                    this.updateTestDisplays(this.selectedAudioFile, result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply embedded sample: ' + error.message);
        }
    }

    async applySongAInSongBTransform() {
        if (!this.selectedAudioFile) {
            showError('Please select Song A audio file first');
            return;
        }

        const songBBaseFileEl = getElement('songBBaseFile');
        const songBBaseFile = (songBBaseFileEl && songBBaseFileEl.value) || null;
        const songASampleStartTimeEl = getElement('songASampleStartTime');
        const sampleStartTime = parseFloat((songASampleStartTimeEl && songASampleStartTimeEl.value) || '0.0');
        const songASampleDurationEl = getElement('songASampleDuration');
        const sampleDuration = parseFloat((songASampleDurationEl && songASampleDurationEl.value) || '1.5');
        const songBDurationEl = getElement('songBDuration');
        const songBDuration = parseFloat((songBDurationEl && songBDurationEl.value) || '30.0');
        const songAApplyTransformEl = getElement('songAApplyTransform');
        const applyTransform = (songAApplyTransformEl && songAApplyTransformEl.value) || 'None';
        const songATransformParamsEl = getElement('songATransformParams');
        const transformParams = (songATransformParamsEl && songATransformParamsEl.value) || null;
        const songAMixVolumeDbEl = getElement('songAMixVolumeDb');
        const mixVolumeDb = parseFloat((songAMixVolumeDbEl && songAMixVolumeDbEl.value) || '0.0');

        try {
            const formData = new FormData();
            formData.append('song_a_path', this.selectedAudioFile);
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

            const response = await fetch(`${API_CONFIG.BASE_URL}/manipulate/song-a-in-song-b`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showCompletionAlert(result.message);
                addSystemLog(`Song A in Song B applied: ${result.output_path}`, 'success');
                await this.loadManipulateAudioFiles();
                if (window.loadTestFileSelects) await window.loadTestFileSelects();
                if (result.output_path) {
                    this.updateTransformedPlayer(result.output_path);
                    this.updateTestDisplays(this.selectedAudioFile, result.output_path);
                }
            } else {
                showError(result.message || 'Transform failed');
            }
        } catch (error) {
            showError('Failed to apply Song A in Song B: ' + error.message);
        }
    }

    updateTestDisplays(originalPath, transformedPath) {
        const originalDisplay = getElement('testOriginalPath') || getElement('originalTestDisplay');
        const transformedDisplay = getElement('testTransformedPath') || getElement('transformedTestDisplay');
        const originalStatus = getElement('originalTestStatus');
        const transformedStatus = getElement('transformedTestStatus');
        const testBtn = getElement('testFingerprintBtn') || getElement('testBtn');

        if (originalDisplay) {
            if (originalPath) {
                originalDisplay.value = originalPath;
                originalDisplay.style.color = '#4ade80';
            } else {
                originalDisplay.value = '';
                originalDisplay.style.color = '#9ca3af';
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
            } else {
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

        if (testBtn) {
            const hasOriginal = (originalDisplay && originalDisplay.value && originalDisplay.value.trim() !== '') || (originalStatus && originalStatus.textContent !== 'No original audio selected.');
            const hasTransformed = (transformedDisplay && transformedDisplay.value && transformedDisplay.value.trim() !== '') || (transformedStatus && transformedStatus.textContent !== 'No transformed audio available. Apply transforms first.');
            testBtn.disabled = !(hasOriginal && hasTransformed);
        }
    }
}

// Export singleton instance and individual functions
export const audioManipulationManager = new AudioManipulationManager();

// Export all public methods as individual functions for backward compatibility
export const loadManipulateAudioFiles = () => audioManipulationManager.loadManipulateAudioFiles();
export const loadAudioInfo = () => audioManipulationManager.loadAudioInfo();
export const clearAudioSelection = () => audioManipulationManager.clearAudioSelection();
export const updateOverlayFileName = () => audioManipulationManager.updateOverlayFileName();
export const updateDeliverablesOverlayFileName = () => audioManipulationManager.updateDeliverablesOverlayFileName();
export const updateOriginalPlayer = (filePath) => audioManipulationManager.updateOriginalPlayer(filePath);
export const updateTransformedPlayer = (filePath) => audioManipulationManager.updateTransformedPlayer(filePath);
export const toggleOriginalPlayback = () => audioManipulationManager.toggleOriginalPlayback();
export const toggleTransformedPlayback = () => audioManipulationManager.toggleTransformedPlayback();
export const updateOriginalTime = () => audioManipulationManager.updateOriginalTime();
export const updateTransformedTime = () => audioManipulationManager.updateTransformedTime();
export const updateOriginalDuration = () => audioManipulationManager.updateOriginalDuration();
export const updateTransformedDuration = () => audioManipulationManager.updateTransformedDuration();
export const handleManipulateDrop = (event) => audioManipulationManager.handleManipulateDrop(event);
export const handleManipulateFileSelect = (event) => audioManipulationManager.handleManipulateFileSelect(event);
export const handleManipulateFileUpload = (file) => audioManipulationManager.handleManipulateFileUpload(file);
export const applySpeedTransform = () => audioManipulationManager.applySpeedTransform();
export const applyPitchTransform = () => audioManipulationManager.applyPitchTransform();
export const applyReverbTransform = () => audioManipulationManager.applyReverbTransform();
export const applyNoiseReductionTransform = () => audioManipulationManager.applyNoiseReductionTransform();
export const applyEQTransform = () => audioManipulationManager.applyEQTransform();
export const applyCompressionTransform = () => audioManipulationManager.applyCompressionTransform();
export const applyOverlayTransform = () => audioManipulationManager.applyOverlayTransform();
export const applyNoiseTransform = () => audioManipulationManager.applyNoiseTransform();
export const applyEncodeTransform = () => audioManipulationManager.applyEncodeTransform();
export const applyChopTransform = () => audioManipulationManager.applyChopTransform();
export const addToChain = () => audioManipulationManager.addToChain();
export const clearChain = () => audioManipulationManager.clearChain();
export const updateChainDisplay = () => audioManipulationManager.updateChainDisplay();
export const removeFromChain = (index) => audioManipulationManager.removeFromChain(index);
export const applyChainTransform = () => audioManipulationManager.applyChainTransform();
export const loadTestFileSelects = () => audioManipulationManager.loadTestFileSelects();
export const testFingerprintRobustness = () => audioManipulationManager.testFingerprintRobustness();
export const applyTransform = (type) => audioManipulationManager.applyTransform(type);
export const updateSliderDisplay = (type, value) => audioManipulationManager.updateSliderDisplay(type, value);
export const applyHighpassTransform = () => audioManipulationManager.applyHighpassTransform();
export const applyLowpassTransform = () => audioManipulationManager.applyLowpassTransform();
export const applyBoostHighsTransform = () => audioManipulationManager.applyBoostHighsTransform();
export const applyBoostLowsTransform = () => audioManipulationManager.applyBoostLowsTransform();
export const applyTelephoneTransform = () => audioManipulationManager.applyTelephoneTransform();
export const applyLimitingTransform = () => audioManipulationManager.applyLimitingTransform();
export const applyMultibandTransform = () => audioManipulationManager.applyMultibandTransform();
export const applyAddNoiseTransform = () => audioManipulationManager.applyAddNoiseTransform();
export const applyCropTransform = () => audioManipulationManager.applyCropTransform();
export const applyEmbeddedSampleTransform = () => audioManipulationManager.applyEmbeddedSampleTransform();
export const applySongAInSongBTransform = () => audioManipulationManager.applySongAInSongBTransform();
export const updateTestDisplays = (originalPath, transformedPath) => audioManipulationManager.updateTestDisplays(originalPath, transformedPath);