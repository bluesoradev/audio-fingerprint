/**
 * Audio Player Component
 * Handles audio playback, visualization, and waveform editing
 */

import {
    formatTimeWithMs,
    getElement
} from '../utils/helpers.js';
import {
    showNotification
} from './notifications.js';

class AudioPlayerManager {
    constructor() {
        this.audioContext = null;
        this.analyserNode = null;
        this.frequencyData = null;
        this.animationFrameId = null;
        this.transportAudioPlaying = false;
        this.transportLoopEnabled = false;
        this.waveformZoomLevel = 1.0;
        this.waveformStartTime = 0;
        this.waveformData = null;
        this.waveformCanvas = null;
        this.waveformCtx = null;
        this.audioSourceMap = new Map(); // Map audio elements to their MediaElementSourceNodes
    }

    initAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new(window.AudioContext || window.webkitAudioContext)();
        }
        return this.audioContext;
    }

    toggleTransportPlayback() {
        const originalPlayer = getElement('originalAudioPlayer');
        const transformedPlayer = getElement('transformedAudioPlayer');
        const playBtn = getElement('transportPlayBtn');

        if (!playBtn) return;

        const activePlayer = originalPlayer && originalPlayer.src ? originalPlayer : transformedPlayer;

        if (!activePlayer || !activePlayer.src) {
            showNotification('No audio loaded');
            return;
        }

        if (this.transportAudioPlaying) {
            activePlayer.pause();
            playBtn.textContent = '▶';
            this.transportAudioPlaying = false;
            this.stopFrequencyVisualization();
        } else {
            if (originalPlayer !== activePlayer && window.originalAudioPlaying) {
                originalPlayer.pause();
                const origBtn = getElement('originalPlayBtn');
                if (origBtn) origBtn.textContent = '▶';
                if (window.originalAudioPlaying !== undefined) window.originalAudioPlaying = false;
            }
            if (transformedPlayer !== activePlayer && window.transformedAudioPlaying) {
                transformedPlayer.pause();
                const transBtn = getElement('transformedPlayBtn');
                if (transBtn) transBtn.textContent = '▶';
                if (window.transformedAudioPlaying !== undefined) window.transformedAudioPlaying = false;
            }

            activePlayer.play().then(() => {
                playBtn.textContent = '⏸';
                this.transportAudioPlaying = true;
                this.startFrequencyVisualization(activePlayer);
            }).catch(err => {
                console.error('Error playing audio:', err);
                showNotification('Error playing audio: ' + err.message);
            });
        }
    }

    transportHopOff() {
        showNotification('Hop Off activated');
    }

    transportCheck() {
        showNotification('Check activated');
    }

    toggleTransportLoop() {
        const loopBtn = getElement('transportLoopBtn');
        if (!loopBtn) return;

        this.transportLoopEnabled = !this.transportLoopEnabled;
        loopBtn.classList.toggle('active', this.transportLoopEnabled);

        const originalPlayer = getElement('originalAudioPlayer');
        const transformedPlayer = getElement('transformedAudioPlayer');
        const activePlayer = originalPlayer && originalPlayer.src ? originalPlayer : transformedPlayer;

        if (activePlayer) {
            activePlayer.loop = this.transportLoopEnabled;
        }
    }

    updateTransportVolume(value) {
        const volumeDisplay = getElement('transportVolumeValue');
        if (volumeDisplay) {
            volumeDisplay.textContent = value + '%';
        }

        const originalPlayer = getElement('originalAudioPlayer');
        const transformedPlayer = getElement('transformedAudioPlayer');
        const volume = value / 100;

        if (originalPlayer) originalPlayer.volume = volume;
        if (transformedPlayer) transformedPlayer.volume = volume;
    }

    updateTransportTempo(value) {
        console.log('Tempo changed to:', value, 'BPM');
    }

    startFrequencyVisualization(audioElement) {
        if (!audioElement) return;

        try {
            const ctx = this.initAudioContext();

            // Check if this audio element already has a source
            let audioSource = this.audioSourceMap.get(audioElement);
            
            if (!audioSource) {
                // Create new source only if it doesn't exist
                try {
                    audioSource = ctx.createMediaElementSource(audioElement);
                    this.audioSourceMap.set(audioElement, audioSource);
                } catch (error) {
                    // If creation fails, the element is already connected to another source
                    // This happens when the same audio element is reused or page is refreshed
                    console.warn('Audio element already connected to MediaElementSource. Frequency visualization will be limited.');
                    
                    // Still try to load waveform
                    if (!this.waveformData) {
                        this.loadWaveformData(audioElement);
                    }
                    
                    // Create analyser if needed (won't have frequency data but won't crash)
                    if (!this.analyserNode) {
                        this.analyserNode = ctx.createAnalyser();
                        this.analyserNode.fftSize = 2048;
                        this.frequencyData = new Uint8Array(this.analyserNode.frequencyBinCount);
                    }
                    
                    // Start animation loop (will show empty/static spectrum but won't error)
                    if (!this.animationFrameId) {
                        this.animateFrequency();
                    }
                    return;
                }
            }

            if (!this.analyserNode) {
                this.analyserNode = ctx.createAnalyser();
                this.analyserNode.fftSize = 2048; // Higher resolution for better visualization
                this.frequencyData = new Uint8Array(this.analyserNode.frequencyBinCount);
            }

            // Connect source to analyser (disconnect first to avoid connection errors)
            try {
                // Disconnect from any previous connections to avoid "already connected" errors
                try {
                    audioSource.disconnect();
                } catch (e) {
                    // Not connected, that's fine - continue
                }
                try {
                    this.analyserNode.disconnect();
                } catch (e) {
                    // Not connected, that's fine - continue
                }
                
                // Now connect fresh
                audioSource.connect(this.analyserNode);
                this.analyserNode.connect(ctx.destination);
            } catch (e) {
                // Connection issue - log but continue
                console.warn('Connection issue during frequency visualization setup:', e);
            }

            // Load and draw waveform if not already loaded
            if (!this.waveformData) {
                this.loadWaveformData(audioElement);
            }
            
            // Start frequency visualization
            this.animateFrequency();
        } catch (error) {
            // If it's the "already connected" error, that's expected - handle gracefully
            if (error.message && error.message.includes('already connected')) {
                console.log('Audio element already connected - skipping frequency visualization setup');
                // Still try to load waveform
                if (!this.waveformData && audioElement) {
                    this.loadWaveformData(audioElement);
                }
                // Don't log as error, just return
                return;
            }
            console.error('Error initializing frequency visualization:', error);
            // Try to continue anyway - start animation even if setup failed
            if (this.analyserNode && !this.animationFrameId) {
                this.animateFrequency();
            }
        }
    }

    stopFrequencyVisualization() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    animateFrequency() {
        if (!this.analyserNode) return;

        this.analyserNode.getByteFrequencyData(this.frequencyData);

        const canvas = getElement('frequencySpectrumCanvas');
        if (canvas) {
            this.drawFrequencySpectrum(canvas, this.frequencyData);
        }

        const originalCanvas = getElement('originalFrequencyCanvas');
        const transformedCanvas = getElement('transformedFrequencyCanvas');

        if (window.originalAudioPlaying && originalCanvas) {
            this.drawFrequencySpectrum(originalCanvas, this.frequencyData);
        }
        if (window.transformedAudioPlaying && transformedCanvas) {
            this.drawFrequencySpectrum(transformedCanvas, this.frequencyData);
        }

        if (this.transportAudioPlaying || window.originalAudioPlaying || window.transformedAudioPlaying) {
            this.animationFrameId = requestAnimationFrame(() => this.animateFrequency());
        }
    }

    drawFrequencySpectrum(canvas, data) {
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Get container dimensions
        const container = canvas.parentElement;
        const width = container ? container.offsetWidth : 800;
        const height = container ? container.offsetHeight : 150;

        // Set canvas size with proper pixel ratio
        const dpr = window.devicePixelRatio || 1;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';

        // Scale context for device pixel ratio
        ctx.scale(dpr, dpr);

        // Clear canvas
        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, width, height);

        if (!data || data.length === 0) {
            // Draw placeholder
            ctx.fillStyle = '#3d3d3d';
            ctx.font = '12px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No frequency data', width / 2, height / 2);
            return;
        }

        // Draw frequency bars
        const barWidth = (width / data.length) * 2.5;
        let x = 0;

        for (let i = 0; i < data.length; i++) {
            const barHeight = (data[i] / 255) * height;
            
            if (barHeight > 0) {
                // Create gradient for each bar
                const gradient = ctx.createLinearGradient(x, height - barHeight, x, height);
                const hue = (i / data.length) * 240; // Blue to purple range
                gradient.addColorStop(0, `hsl(${hue}, 100%, 60%)`);
                gradient.addColorStop(1, `hsl(${hue}, 100%, 30%)`);
                
                ctx.fillStyle = gradient;
                ctx.fillRect(x, height - barHeight, Math.max(1, barWidth - 1), barHeight);
            }
            
            x += barWidth;
        }
    }

    waveformZoomIn() {
        this.waveformZoomLevel = Math.min(this.waveformZoomLevel * 1.5, 10);
        this.updateWaveformDisplay();
    }

    waveformZoomOut() {
        this.waveformZoomLevel = Math.max(this.waveformZoomLevel / 1.5, 0.1);
        this.updateWaveformDisplay();
    }

    async loadWaveformData(audioElement) {
        if (!audioElement || !audioElement.src) return;

        try {
            const ctx = this.initAudioContext();
            const response = await fetch(audioElement.src);
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

            // Extract waveform data
            const channelData = audioBuffer.getChannelData(0); // Use first channel
            const samples = 2000; // Number of samples to display
            const blockSize = Math.floor(channelData.length / samples);
            this.waveformData = [];

            for (let i = 0; i < samples; i++) {
                let sum = 0;
                for (let j = 0; j < blockSize; j++) {
                    sum += Math.abs(channelData[i * blockSize + j]);
                }
                this.waveformData.push(sum / blockSize);
            }

            // Draw waveform
            this.drawWaveform();
            
            // Update track label
            const trackLabel = getElement('track1Label');
            if (trackLabel) {
                const fileName = audioElement.src.split('/').pop() || 'Audio Track';
                trackLabel.textContent = fileName;
            }
        } catch (error) {
            console.error('Error loading waveform data:', error);
        }
    }

    drawWaveform() {
        const canvas = getElement('waveformCanvas');
        if (!canvas || !this.waveformData || this.waveformData.length === 0) {
            // Draw placeholder if no data
            if (canvas) {
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    const container = canvas.parentElement;
                    const width = container ? container.offsetWidth : 800;
                    const height = container ? container.offsetHeight : 100;
                    canvas.width = width;
                    canvas.height = height;
                    ctx.fillStyle = '#1e1e1e';
                    ctx.fillRect(0, 0, width, height);
                    ctx.fillStyle = '#3d3d3d';
                    ctx.font = '12px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.fillText('No waveform data', width / 2, height / 2);
                }
            }
            return;
        }

        const container = canvas.parentElement;
        if (!container) return;

        // Set canvas size with proper pixel ratio for crisp rendering
        const dpr = window.devicePixelRatio || 1;
        const width = container.offsetWidth || 800;
        const height = container.offsetHeight || 100;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Scale context for device pixel ratio
        ctx.scale(dpr, dpr);

        // Clear canvas
        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, width, height);

        // Draw waveform
        const centerY = height / 2;
        const maxAmplitude = Math.max(...this.waveformData);
        const scale = maxAmplitude > 0 ? (height * 0.4) / maxAmplitude : 1;

        // Draw waveform as filled shape
        ctx.fillStyle = '#22D2E6';
        ctx.strokeStyle = '#22D2E6';
        ctx.lineWidth = 1;
        ctx.beginPath();

        // Draw top half
        for (let i = 0; i < this.waveformData.length; i++) {
            const x = (i / this.waveformData.length) * width;
            const amplitude = this.waveformData[i] * scale;
            const y = centerY - amplitude;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }

        // Draw bottom half (mirrored)
        for (let i = this.waveformData.length - 1; i >= 0; i--) {
            const x = (i / this.waveformData.length) * width;
            const amplitude = this.waveformData[i] * scale;
            const y = centerY + amplitude;
            ctx.lineTo(x, y);
        }

        ctx.closePath();
        ctx.fill();
        ctx.stroke();
    }

    updateWaveformDisplay() {
        const timeRangeDisplay = getElement('waveformTimeRange');
        if (timeRangeDisplay) {
            const originalPlayer = getElement('originalAudioPlayer');
            const transformedPlayer = getElement('transformedAudioPlayer');
            const activePlayer = (originalPlayer && originalPlayer.src) ? originalPlayer : transformedPlayer;
            
            const duration = activePlayer && activePlayer.duration ? activePlayer.duration : 5.123;
            const visibleDuration = duration / this.waveformZoomLevel;
            timeRangeDisplay.textContent = `00:00:00.000 - ${formatTimeWithMs(visibleDuration)}`;
        }
        
        // Redraw waveform with zoom
        if (this.waveformData) {
            this.drawWaveform();
        }
    }

    setupWaveformScrubbing() {
        const waveformAreas = document.querySelectorAll('.track-waveform-area, .audio-player-waveform');
        waveformAreas.forEach(area => {
            area.addEventListener('click', (e) => {
                const rect = area.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const percentage = clickX / rect.width;

                const originalPlayer = getElement('originalAudioPlayer');
                const transformedPlayer = getElement('transformedAudioPlayer');

                let targetPlayer = null;
                if (area.closest('.audio-player-panel')) {
                    const panel = area.closest('.audio-player-panel');
                    if (panel.querySelector('#originalAudioPlayer')) {
                        targetPlayer = originalPlayer;
                    } else if (panel.querySelector('#transformedAudioPlayer')) {
                        targetPlayer = transformedPlayer;
                    }
                } else {
                    targetPlayer = originalPlayer && originalPlayer.src ? originalPlayer : transformedPlayer;
                }

                if (targetPlayer && targetPlayer.duration) {
                    const seekTime = percentage * targetPlayer.duration;
                    targetPlayer.currentTime = seekTime;
                    if (window.updatePlayheadPosition) window.updatePlayheadPosition(percentage);
                }
            });
        });
    }

    updatePlayheadPosition(percentage) {
        const playhead = getElement('waveformPlayhead');
        if (playhead) {
            playhead.style.left = (percentage * 100) + '%';
        }
        
        // Update waveform display with playhead
        if (this.waveformData) {
            this.drawWaveformWithPlayhead(percentage);
        }
    }

    drawWaveformWithPlayhead(playheadPosition) {
        const canvas = getElement('waveformCanvas');
        if (!canvas || !this.waveformData || this.waveformData.length === 0) return;

        const container = canvas.parentElement;
        if (!container) return;

        const width = container.offsetWidth || 800;
        const height = container.offsetHeight || 100;
        const dpr = window.devicePixelRatio || 1;

        // Redraw base waveform (this sets up the canvas and scales context)
        this.drawWaveform();
        
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Context is already scaled by drawWaveform, use logical coordinates
        const x = playheadPosition * width;
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setupWaveformScrubbing();
                this.initializeCanvases();
            });
        } else {
            this.setupWaveformScrubbing();
            this.initializeCanvases();
        }
    }

    initializeCanvases() {
        // Initialize frequency spectrum canvas
        const freqCanvas = getElement('frequencySpectrumCanvas');
        if (freqCanvas) {
            const container = freqCanvas.parentElement;
            if (container) {
                freqCanvas.width = container.offsetWidth || 800;
                freqCanvas.height = container.offsetHeight || 150;
            }
        }

        // Initialize waveform canvas
        const waveformCanvas = getElement('waveformCanvas');
        if (waveformCanvas) {
            const container = waveformCanvas.parentElement;
            if (container) {
                waveformCanvas.width = container.offsetWidth || 800;
                waveformCanvas.height = container.offsetHeight || 100;
            }
        }
    }
}

// Export singleton instance and individual functions
export const audioPlayerManager = new AudioPlayerManager();

export const initAudioContext = () => audioPlayerManager.initAudioContext();
export const toggleTransportPlayback = () => audioPlayerManager.toggleTransportPlayback();
export const transportHopOff = () => audioPlayerManager.transportHopOff();
export const transportCheck = () => audioPlayerManager.transportCheck();
export const toggleTransportLoop = () => audioPlayerManager.toggleTransportLoop();
export const updateTransportVolume = (value) => audioPlayerManager.updateTransportVolume(value);
export const updateTransportTempo = (value) => audioPlayerManager.updateTransportTempo(value);
export const startFrequencyVisualization = (audioElement) => audioPlayerManager.startFrequencyVisualization(audioElement);
export const stopFrequencyVisualization = () => audioPlayerManager.stopFrequencyVisualization();
export const animateFrequency = () => audioPlayerManager.animateFrequency();
export const drawFrequencySpectrum = (canvas, data) => audioPlayerManager.drawFrequencySpectrum(canvas, data);
export const waveformZoomIn = () => audioPlayerManager.waveformZoomIn();
export const waveformZoomOut = () => audioPlayerManager.waveformZoomOut();
export const updateWaveformDisplay = () => audioPlayerManager.updateWaveformDisplay();
export const setupWaveformScrubbing = () => audioPlayerManager.setupWaveformScrubbing();
export const updatePlayheadPosition = (percentage) => audioPlayerManager.updatePlayheadPosition(percentage);

// Initialize on load
audioPlayerManager.init();