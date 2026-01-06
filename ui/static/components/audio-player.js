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
            if (!this.analyserNode) {
                this.analyserNode = ctx.createAnalyser();
                this.analyserNode.fftSize = 256;
                this.frequencyData = new Uint8Array(this.analyserNode.frequencyBinCount);
            }

            const source = ctx.createMediaElementSource(audioElement);
            source.connect(this.analyserNode);
            this.analyserNode.connect(ctx.destination);

            this.animateFrequency();
        } catch (error) {
            console.error('Error initializing frequency visualization:', error);
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
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const width = canvas.width || canvas.offsetWidth;
        const height = canvas.height || canvas.offsetHeight;

        canvas.width = width;
        canvas.height = height;

        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, width, height);

        const barWidth = width / data.length;
        let x = 0;

        for (let i = 0; i < data.length; i++) {
            const barHeight = (data[i] / 255) * height;
            const hue = (i / data.length) * 360;

            ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
            ctx.fillRect(x, height - barHeight, barWidth, barHeight);
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

    updateWaveformDisplay() {
        const timeRangeDisplay = getElement('waveformTimeRange');
        if (timeRangeDisplay) {
            const duration = 5.123; // This should come from actual audio duration
            const visibleDuration = duration / this.waveformZoomLevel;
            timeRangeDisplay.textContent = `00:00:00.000 - ${formatTimeWithMs(visibleDuration)}`;
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
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setupWaveformScrubbing();
            });
        } else {
            this.setupWaveformScrubbing();
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