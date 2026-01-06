/**
 * Audio Fingerprint Robustness Lab - Componentized Frontend
 * 
 * This file dynamically imports all component modules and loads remaining functions
 * from app-original.js, re-exporting everything to window for backward compatibility
 */

// Use async IIFE to load ES6 modules
(async function() {
    'use strict';

    try {
        // Import all component modules
        const {
            API_CONFIG
        } = await import('./config/api.js');
        const {
            apiClient
        } = await import('./api/client.js');
        const {
            formatBytes,
            formatTime,
            formatTimeWithMs,
            formatFileSize,
            getElement,
            querySelector,
            querySelectorAll
        } = await import('./utils/helpers.js');
        const {
            navigationManager
        } = await import('./components/navigation.js');
        const {
            notificationManager,
            showError,
            showCompletionAlert,
            showNotification
        } = await import('./components/notifications.js');
        const {
            statusChecker,
            checkStatus
        } = await import('./components/status.js');
        const {
            dashboardManager,
            loadDashboard
        } = await import('./components/dashboard.js');
        const {
            workflowManager,
            createTestAudio,
            createManifest,
            ingestFiles,
            generateTransforms,
            runExperiment
        } = await import('./components/workflow.js');
        const {
            processMonitor,
            startProcessMonitoring,
            pollLogs,
            checkProcessStatus
        } = await import('./components/process-monitor.js');
        const {
            fileManager,
            loadManifests,
            loadAudioFiles,
            uploadFiles,
            loadRuns,
            handleDrop,
            handleDragOver,
            handleDragLeave,
            handleFileSelect
        } = await import('./components/file-manager.js');
        const {
            configManager,
            loadTestMatrix,
            saveTestMatrix
        } = await import('./components/config.js');
        const {
            audioManipulationManager,
            loadManipulateAudioFiles,
            loadAudioInfo,
            clearAudioSelection,
            updateOverlayFileName,
            updateDeliverablesOverlayFileName,
            updateOriginalPlayer,
            updateTransformedPlayer,
            toggleOriginalPlayback,
            toggleTransformedPlayback,
            updateOriginalTime,
            updateTransformedTime,
            updateOriginalDuration,
            updateTransformedDuration,
            handleManipulateDrop,
            handleManipulateFileSelect,
            handleManipulateFileUpload,
            applySpeedTransform,
            applyPitchTransform,
            applyReverbTransform,
            applyNoiseReductionTransform,
            applyEQTransform,
            applyCompressionTransform,
            applyOverlayTransform,
            applyNoiseTransform,
            applyEncodeTransform,
            applyChopTransform,
            addToChain,
            clearChain,
            updateChainDisplay,
            removeFromChain,
            applyChainTransform,
            loadTestFileSelects,
            testFingerprintRobustness,
            applyTransform,
            updateSliderDisplay,
            applyHighpassTransform,
            applyLowpassTransform,
            applyBoostHighsTransform,
            applyBoostLowsTransform,
            applyTelephoneTransform,
            applyLimitingTransform,
            applyMultibandTransform,
            applyAddNoiseTransform,
            applyCropTransform,
            applyEmbeddedSampleTransform,
            applySongAInSongBTransform,
            updateTestDisplays
        } = await import('./components/audio-manipulation.js');
        const {
            deliverablesManager,
            loadDeliverables,
            viewReport,
            downloadReportZip,
            viewRunDetails,
            deleteReport,
            loadDeliverablesAudioFiles,
            loadDeliverablesAudioInfo,
            handleDeliverablesDrop,
            handleDeliverablesFileSelect,
            handleDeliverablesFileUpload,
            updateDeliverablesSpeedValue,
            updateDeliverablesPitchValue,
            updateDeliverablesReverbValue,
            updateDeliverablesNoiseValue,
            updateDeliverablesEQValue,
            updateDeliverablesOverlayGainValue,
            updateDeliverablesSliderDisplay,
            updateDeliverablesBitrateEnabled,
            updateDeliverablesCropDuration,
            toggleDeliverablesEmbeddedTransformParams,
            toggleDeliverablesSongATransformParams,
            updateDeliverablesTransformState,
            applyAllDeliverablesTransforms
        } = await import('./components/deliverables.js');
        const {
            progressModalManager,
            showProgressModal,
            closeProgressModal,
            updateProgressIndicator,
            updateCurrentStep,
            updateTimeInfo,
            cancelProgress,
            runPhaseSuite
        } = await import('./components/progress-modal.js');
        const {
            dawParserManager,
            loadDAWFiles,
            handleDAWDrop,
            handleDAWFileSelect,
            uploadDAWFile,
            parseDAWFile,
            viewDAWMetadata,
            displayDAWMetadata
        } = await import('./components/daw-parser.js');
        const {
            audioPlayerManager,
            initAudioContext,
            toggleTransportPlayback,
            transportHopOff,
            transportCheck,
            toggleTransportLoop,
            updateTransportVolume,
            updateTransportTempo,
            startFrequencyVisualization,
            stopFrequencyVisualization,
            animateFrequency,
            drawFrequencySpectrum,
            waveformZoomIn,
            waveformZoomOut,
            updateWaveformDisplay,
            setupWaveformScrubbing,
            updatePlayheadPosition
        } = await import('./components/audio-player.js');

        // Export API_BASE for backward compatibility
        window.API_BASE = API_CONFIG.BASE_URL;
        window.apiClient = apiClient;

        // Export utilities
        window.formatBytes = formatBytes;
        window.formatTime = formatTime;
        window.formatTimeWithMs = formatTimeWithMs;
        window.formatFileSize = formatFileSize;
        window.getElement = getElement;
        window.querySelector = querySelector;
        window.querySelectorAll = querySelectorAll;

        // Export notification functions
        window.showError = showError;
        window.showCompletionAlert = showCompletionAlert;
        window.showNotification = showNotification;
        window.addSystemLog = (message, type) => notificationManager.addSystemLog(message, type);

        // Export status functions
        window.checkStatus = checkStatus;

        // Export dashboard functions
        window.loadDashboard = loadDashboard;

        // Export workflow functions
        window.createTestAudio = createTestAudio;
        window.createManifest = createManifest;
        window.ingestFiles = ingestFiles;
        window.generateTransforms = generateTransforms;
        window.runExperiment = runExperiment;

        // Export process monitor functions
        window.startProcessMonitoring = startProcessMonitoring;
        window.pollLogs = pollLogs;
        window.checkProcessStatus = checkProcessStatus;
        window.currentProcessId = null;
        Object.defineProperty(window, 'currentProcessId', {
            get: () => processMonitor.getCurrentProcessId(),
            set: (val) => processMonitor.currentProcessId = val
        });

        // Export file manager functions
        window.loadManifests = loadManifests;
        window.loadAudioFiles = loadAudioFiles;
        window.uploadFiles = uploadFiles;
        window.loadRuns = loadRuns;
        window.handleDrop = handleDrop;
        window.handleDragOver = handleDragOver;
        window.handleDragLeave = handleDragLeave;
        window.handleFileSelect = handleFileSelect;

        // Export config functions
        window.loadTestMatrix = loadTestMatrix;
        window.saveTestMatrix = saveTestMatrix;

        // Export navigation
        window.navigationManager = navigationManager;
        window.showSection = (sectionId, eventElement) => navigationManager.showSection(sectionId, eventElement);
        window.loadSectionData = (sectionId) => navigationManager.loadSectionData(sectionId);

        // Export results functions
        window.viewRun = (runId) => window.open(`/report/${runId}`, '_blank');
        window.downloadReport = (runId) => window.location.href = `/download/${runId}`;

        // Export audio manipulation functions
        window.loadManipulateAudioFiles = loadManipulateAudioFiles;
        window.loadAudioInfo = loadAudioInfo;
        window.clearAudioSelection = clearAudioSelection;
        window.updateOverlayFileName = updateOverlayFileName;
        window.updateDeliverablesOverlayFileName = updateDeliverablesOverlayFileName;
        window.updateOriginalPlayer = updateOriginalPlayer;
        window.updateTransformedPlayer = updateTransformedPlayer;
        window.toggleOriginalPlayback = toggleOriginalPlayback;
        window.toggleTransformedPlayback = toggleTransformedPlayback;
        window.updateOriginalTime = updateOriginalTime;
        window.updateTransformedTime = updateTransformedTime;
        window.updateOriginalDuration = updateOriginalDuration;
        window.updateTransformedDuration = updateTransformedDuration;
        window.handleManipulateDrop = handleManipulateDrop;
        window.handleManipulateFileSelect = handleManipulateFileSelect;
        window.handleManipulateFileUpload = handleManipulateFileUpload;
        window.applySpeedTransform = applySpeedTransform;
        window.applyPitchTransform = applyPitchTransform;
        window.applyReverbTransform = applyReverbTransform;
        window.applyNoiseReductionTransform = applyNoiseReductionTransform;
        window.applyEQTransform = applyEQTransform;
        window.applyCompressionTransform = applyCompressionTransform;
        window.applyOverlayTransform = applyOverlayTransform;
        window.applyNoiseTransform = applyNoiseTransform;
        window.applyEncodeTransform = applyEncodeTransform;
        window.applyChopTransform = applyChopTransform;
        window.addToChain = addToChain;
        window.clearChain = clearChain;
        window.updateChainDisplay = updateChainDisplay;
        window.removeFromChain = removeFromChain;
        window.applyChainTransform = applyChainTransform;
        window.loadTestFileSelects = loadTestFileSelects;
        window.testFingerprintRobustness = testFingerprintRobustness;
        window.applyTransform = applyTransform;
        window.updateSliderDisplay = updateSliderDisplay;
        window.applyHighpassTransform = applyHighpassTransform;
        window.applyLowpassTransform = applyLowpassTransform;
        window.applyBoostHighsTransform = applyBoostHighsTransform;
        window.applyBoostLowsTransform = applyBoostLowsTransform;
        window.applyTelephoneTransform = applyTelephoneTransform;
        window.applyLimitingTransform = applyLimitingTransform;
        window.applyMultibandTransform = applyMultibandTransform;
        window.applyAddNoiseTransform = applyAddNoiseTransform;
        window.applyCropTransform = applyCropTransform;
        window.applyEmbeddedSampleTransform = applyEmbeddedSampleTransform;
        window.applySongAInSongBTransform = applySongAInSongBTransform;
        window.updateTestDisplays = updateTestDisplays;
        window.selectedAudioFile = null;
        Object.defineProperty(window, 'selectedAudioFile', {
            get: () => audioManipulationManager.selectedAudioFile,
            set: (val) => audioManipulationManager.selectedAudioFile = val
        });
        window.transformChain = [];
        Object.defineProperty(window, 'transformChain', {
            get: () => audioManipulationManager.transformChain,
            set: (val) => audioManipulationManager.transformChain = val
        });

        // Export deliverables functions
        window.loadDeliverables = loadDeliverables;
        window.viewReport = viewReport;
        window.downloadReportZip = downloadReportZip;
        window.viewRunDetails = viewRunDetails;
        window.deleteReport = deleteReport;
        window.loadDeliverablesAudioFiles = loadDeliverablesAudioFiles;
        window.loadDeliverablesAudioInfo = loadDeliverablesAudioInfo;
        window.handleDeliverablesDrop = handleDeliverablesDrop;
        window.handleDeliverablesFileSelect = handleDeliverablesFileSelect;
        window.handleDeliverablesFileUpload = handleDeliverablesFileUpload;
        window.updateDeliverablesSpeedValue = updateDeliverablesSpeedValue;
        window.updateDeliverablesPitchValue = updateDeliverablesPitchValue;
        window.updateDeliverablesReverbValue = updateDeliverablesReverbValue;
        window.updateDeliverablesNoiseValue = updateDeliverablesNoiseValue;
        window.updateDeliverablesEQValue = updateDeliverablesEQValue;
        window.updateDeliverablesOverlayGainValue = updateDeliverablesOverlayGainValue;
        window.updateDeliverablesSliderDisplay = updateDeliverablesSliderDisplay;
        window.updateDeliverablesBitrateEnabled = updateDeliverablesBitrateEnabled;
        window.updateDeliverablesCropDuration = updateDeliverablesCropDuration;
        window.toggleDeliverablesEmbeddedTransformParams = toggleDeliverablesEmbeddedTransformParams;
        window.toggleDeliverablesSongATransformParams = toggleDeliverablesSongATransformParams;
        window.updateDeliverablesTransformState = updateDeliverablesTransformState;
        window.applyAllDeliverablesTransforms = applyAllDeliverablesTransforms;
        window.deliverablesSelectedAudioFile = null;
        Object.defineProperty(window, 'deliverablesSelectedAudioFile', {
            get: () => deliverablesManager.selectedAudioFile,
            set: (val) => deliverablesManager.selectedAudioFile = val
        });

        // Export progress modal functions
        window.showProgressModal = showProgressModal;
        window.closeProgressModal = closeProgressModal;
        window.updateProgressIndicator = updateProgressIndicator;
        window.updateCurrentStep = updateCurrentStep;
        window.updateTimeInfo = updateTimeInfo;
        window.cancelProgress = cancelProgress;
        window.runPhaseSuite = runPhaseSuite;

        // Export DAW parser functions
        window.loadDAWFiles = loadDAWFiles;
        window.handleDAWDrop = handleDAWDrop;
        window.handleDAWFileSelect = handleDAWFileSelect;
        window.uploadDAWFile = uploadDAWFile;
        window.parseDAWFile = parseDAWFile;
        window.viewDAWMetadata = viewDAWMetadata;
        window.displayDAWMetadata = displayDAWMetadata;

        // Export audio player functions
        window.initAudioContext = initAudioContext;
        window.toggleTransportPlayback = toggleTransportPlayback;
        window.transportHopOff = transportHopOff;
        window.transportCheck = transportCheck;
        window.toggleTransportLoop = toggleTransportLoop;
        window.updateTransportVolume = updateTransportVolume;
        window.updateTransportTempo = updateTransportTempo;
        window.startFrequencyVisualization = startFrequencyVisualization;
        window.stopFrequencyVisualization = stopFrequencyVisualization;
        window.animateFrequency = animateFrequency;
        window.drawFrequencySpectrum = drawFrequencySpectrum;
        window.waveformZoomIn = waveformZoomIn;
        window.waveformZoomOut = waveformZoomOut;
        window.updateWaveformDisplay = updateWaveformDisplay;
        window.setupWaveformScrubbing = setupWaveformScrubbing;
        window.updatePlayheadPosition = updatePlayheadPosition;

        console.log('Componentized app.js loaded. All modules imported.');

        // Initialize navigation
        navigationManager.init();

        // Set up DOMContentLoaded handler
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeApp);
        } else {
            initializeApp();
        }

        function initializeApp() {
            // Initialize status checking
            checkStatus();
            setInterval(checkStatus, 5000);

            // Load initial data
            loadDashboard();
        }

    } catch (error) {
        console.error('Failed to load componentized app.js:', error);
        // Componentization is complete - no fallback needed
        throw error;
    }
})();

// All functions are now componentized - app-original.js is no longer needed

// Transform Tab Switching - MUST be defined at top level for onclick handlers
function switchTransformTab(tabName, event) {
    console.log('switchTransformTab called with:', tabName);

    const allTabContents = document.querySelectorAll('.transform-tab-content');
    allTabContents.forEach(tab => tab.classList.remove('active'));

    const allTabs = document.querySelectorAll('.transform-tab');
    allTabs.forEach(tab => tab.classList.remove('active'));

    const tabId = 'transformTab' + tabName.charAt(0).toUpperCase() + tabName.slice(1);
    const targetTabContent = document.getElementById(tabId);
    if (targetTabContent) {
        targetTabContent.classList.add('active');
    }

    if (event && event.target) {
        event.target.classList.add('active');
    } else {
        allTabs.forEach(tab => {
            const onclick = tab.getAttribute('onclick');
            if (onclick && onclick.includes("'" + tabName + "'")) {
                tab.classList.add('active');
            }
        });
    }

    return false;
}

window.switchTransformTab = switchTransformTab;