/**
 * Progress Modal Component
 * Handles progress tracking and modal display for long-running processes
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    getElement
} from '../utils/helpers.js';
import {
    showError,
    showCompletionAlert
} from './notifications.js';

const STEP_DEFINITIONS = [{
        text: 'Step 1: Ingesting',
        keywords: ['ingest', 'ingesting'],
        stepIndex: 0,
        stepProgress: 0
    },
    {
        text: 'Step 2: Generating transforms',
        keywords: ['transform', 'generating transforms'],
        stepIndex: 1,
        stepProgress: 0
    },
    {
        text: 'Step 3: Building FAISS index',
        keywords: ['index', 'faiss', 'building'],
        stepIndex: 2,
        stepProgress: 0
    },
    {
        text: 'Step 4: Running queries',
        keywords: ['query', 'queries', 'running queries'],
        stepIndex: 3,
        stepProgress: 0
    },
    {
        text: 'Step 5: Analyzing results',
        keywords: ['analyze', 'analyzing', 'results'],
        stepIndex: 4,
        stepProgress: 0
    },
    {
        text: 'Step 6: Capturing failures',
        keywords: ['failure', 'failures', 'capturing'],
        stepIndex: 5,
        stepProgress: 0
    },
    {
        text: 'Step 7: Generating report',
        keywords: ['report', 'generating report'],
        stepIndex: 6,
        stepProgress: 0
    }
];

class ProgressModalManager {
    constructor() {
        this.state = {
            phase: 'both',
            commandId: null,
            startTime: null,
            overallProgress: 0,
            stepProgress: 0,
            currentStep: 'Initializing...',
            currentStepIndex: 0,
            stepStartTime: null,
            isCancelled: false,
            pollInterval: null,
            timeInterval: null
        };
    }

    showProgressModal(phase) {
        const modal = getElement('progressModal');
        if (!modal) return;

        this.state.phase = phase;
        this.state.startTime = Date.now();
        this.state.stepStartTime = Date.now();
        this.state.overallProgress = 0;
        this.state.stepProgress = 0;
        this.state.currentStep = 'Initializing...';
        this.state.currentStepIndex = 0;
        this.state.isCancelled = false;

        this.updateProgressIndicator('overall', 0, 'Waiting...');
        this.updateProgressIndicator('step', 0, 'Waiting...');
        this.updateCurrentStep('Initializing...');
        this.updateTimeInfo();

        const closeBtn = getElement('progressModalClose');
        if (closeBtn) closeBtn.disabled = false;

        modal.style.display = 'flex';

        if (this.state.timeInterval) {
            clearInterval(this.state.timeInterval);
        }
        this.state.timeInterval = setInterval(() => this.updateTimeInfo(), 1000);
    }

    closeProgressModal() {
        if (this.state.commandId && !this.state.isCancelled) {
            this.cancelProgress();
            return;
        }

        const modal = getElement('progressModal');
        if (!modal) return;

        modal.style.display = 'none';

        if (this.state.pollInterval) {
            clearInterval(this.state.pollInterval);
            this.state.pollInterval = null;
        }
        if (this.state.timeInterval) {
            clearInterval(this.state.timeInterval);
            this.state.timeInterval = null;
        }
    }

    updateProgressIndicator(type, percentage, status) {
        const percentageEl = getElement(`${type}Percentage`);
        const statusEl = getElement(`${type}Status`);
        const circleEl = document.querySelector(`.progress-circle-fill.${type}`);

        const clampedPercentage = Math.max(0, Math.min(100, percentage));

        if (percentageEl) percentageEl.textContent = `${Math.round(clampedPercentage)}%`;
        if (statusEl) {
            const maxStatusLength = 30;
            const displayStatus = status.length > maxStatusLength ?
                status.substring(0, maxStatusLength - 3) + '...' :
                status;
            statusEl.textContent = displayStatus;
            statusEl.title = status;
        }

        if (circleEl) {
            const radius = 54;
            const circumference = 2 * Math.PI * radius;
            const offset = circumference - (clampedPercentage / 100) * circumference;
            circleEl.style.strokeDasharray = `${circumference} ${circumference}`;
            circleEl.style.strokeDashoffset = offset;

            circleEl.classList.remove('pending', 'error');
            if (clampedPercentage === 0) {
                circleEl.classList.add('pending');
            } else if (status.toLowerCase().includes('failed') || status.toLowerCase().includes('error')) {
                circleEl.classList.add('error');
            }
        }

        if (type === 'overall') {
            this.state.overallProgress = clampedPercentage;
        } else if (type === 'step') {
            this.state.stepProgress = clampedPercentage;
        }
    }

    updateCurrentStep(step) {
        const stepEl = getElement('currentStep');
        if (stepEl) {
            stepEl.textContent = `Current Step: ${step}`;
            this.state.currentStep = step;
        }
    }

    updateTimeInfo() {
        if (!this.state.startTime) return;

        const elapsed = Date.now() - this.state.startTime;
        const seconds = Math.floor(elapsed / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        const h = String(hours).padStart(2, '0');
        const m = String(minutes % 60).padStart(2, '0');
        const s = String(seconds % 60).padStart(2, '0');

        const timeEl = getElement('timeInfo');
        if (timeEl) {
            timeEl.textContent = `Time elapsed: ${h}:${m}:${s}`;
        }
    }

    parseLogForProgress(logMessage, currentActivePhase) {
        if (!logMessage) return null;

        const message = logMessage.toLowerCase();
        const originalMessage = logMessage;

        let detectedPhase = null;
        if (message.includes('phase1') || message.includes('phase_1') || message.includes('test_matrix_phase1')) {
            detectedPhase = 'phase1';
        } else if (message.includes('phase2') || message.includes('phase_2') || message.includes('test_matrix_phase2')) {
            detectedPhase = 'phase2';
        } else {
            detectedPhase = currentActivePhase;
        }

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
            const filePattern = /(\d+)\s*(?:of|\/)\s*(\d+)/i;
            const fileMatch = originalMessage.match(filePattern);
            if (fileMatch) {
                const current = parseInt(fileMatch[1]);
                const total = parseInt(fileMatch[2]);
                extractedProgress = Math.round((current / total) * 100);
                progressText = `${current}/${total}`;
            }

            const percentPattern = /(\d+)%/;
            const percentMatch = originalMessage.match(percentPattern);
            if (percentMatch && !extractedProgress) {
                extractedProgress = parseInt(percentMatch[1]);
            }
        }

        let matchedStep = null;
        for (let i = 0; i < STEP_DEFINITIONS.length; i++) {
            const stepDef = STEP_DEFINITIONS[i];
            const stepLower = stepDef.text.toLowerCase();

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

        if (matchedStep) {
            return matchedStep;
        }

        if (extractedProgress !== null) {
            let inferredStep = null;
            if (message.includes('ingest') || message.includes('processing original')) {
                inferredStep = STEP_DEFINITIONS[0];
            } else if (message.includes('transform') || message.includes('generating')) {
                inferredStep = STEP_DEFINITIONS[1];
            } else if (message.includes('index') || message.includes('faiss') || message.includes('building') || message.includes('embedding')) {
                inferredStep = STEP_DEFINITIONS[2];
            } else if (message.includes('query') || message.includes('running queries')) {
                inferredStep = STEP_DEFINITIONS[3];
            } else if (message.includes('analyze') || message.includes('analyzing')) {
                inferredStep = STEP_DEFINITIONS[4];
            } else if (message.includes('failure') || message.includes('capturing')) {
                inferredStep = STEP_DEFINITIONS[5];
            } else if (message.includes('report') || message.includes('generating report')) {
                inferredStep = STEP_DEFINITIONS[6];
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

    calculateOverallProgress(currentPhase, stepIndex, stepProgress) {
        const totalSteps = STEP_DEFINITIONS.length;
        const stepWeight = 100 / totalSteps;

        if (this.state.phase === 'both') {
            if (currentPhase === 'phase1') {
                const baseProgress = (stepIndex / totalSteps) * 50;
                const stepContribution = (stepProgress / 100) * stepWeight * 0.5;
                return Math.min(baseProgress + stepContribution, 50);
            } else if (currentPhase === 'phase2') {
                const baseProgress = 50 + (stepIndex / totalSteps) * 50;
                const stepContribution = (stepProgress / 100) * stepWeight * 0.5;
                return Math.min(baseProgress + stepContribution, 100);
            }
        } else if (this.state.phase === 'phase1') {
            const baseProgress = (stepIndex / totalSteps) * 100;
            const stepContribution = (stepProgress / 100) * stepWeight;
            return Math.min(baseProgress + stepContribution, 100);
        } else if (this.state.phase === 'phase2') {
            const baseProgress = (stepIndex / totalSteps) * 100;
            const stepContribution = (stepProgress / 100) * stepWeight;
            return Math.min(baseProgress + stepContribution, 100);
        }

        return 0;
    }

    async cancelProgress() {
        if (!this.state.commandId) {
            this.closeProgressModal();
            return;
        }

        if (!confirm('Are you sure you want to cancel the report generation?')) {
            return;
        }

        try {
            const resp = await fetch(`${API_CONFIG.BASE_URL}/process/${this.state.commandId}/cancel`, {
                method: 'POST'
            });

            if (resp.ok) {
                this.state.isCancelled = true;
                this.updateCurrentStep('Cancelling...');
                this.updateProgressIndicator('overall', this.state.overallProgress, 'Cancelled');
                this.updateProgressIndicator('step', this.state.stepProgress, 'Cancelled');

                if (this.state.pollInterval) {
                    clearInterval(this.state.pollInterval);
                    this.state.pollInterval = null;
                }

                showCompletionAlert('Report generation cancelled', 'info');
                setTimeout(() => {
                    this.closeProgressModal();
                    if (window.loadDeliverables) window.loadDeliverables();
                    if (window.loadDashboard) window.loadDashboard();
                }, 2000);
            } else {
                showError('Failed to cancel process');
            }
        } catch (error) {
            showError('Error cancelling process: ' + error.message);
        }
    }

    async runPhaseSuite(phase = 'both') {
        try {
            const btnText = {
                both: 'Generating Phase 1 & 2…',
                phase1: 'Generating Phase 1…',
                phase2: 'Generating Phase 2…'
            } [phase] || 'Generating…';

            this.showProgressModal(phase);

            const resp = await fetch(`${API_CONFIG.BASE_URL}/process/generate-deliverables`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
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
                this.closeProgressModal();
                throw new Error(msg);
            }

            const result = await resp.json();
            const commandId = result.command_id;
            this.state.commandId = commandId;

            let lastLogCount = 0;
            let currentActivePhase = phase === 'both' ? 'phase1' : phase;

            const pollLogs = async () => {
                if (this.state.isCancelled) {
                    return;
                }

                try {
                    const logResp = await fetch(`${API_CONFIG.BASE_URL}/process/${commandId}/logs`);
                    if (logResp.ok) {
                        const logData = await logResp.json();
                        if (logData.logs && logData.logs.length > 0) {
                            const newLogs = logData.logs.slice(lastLogCount);
                            if (newLogs.length > 0) {
                                let foundProgressInBatch = false;

                                newLogs.forEach(log => {
                                    if (log.type === 'stdout' || log.type === 'stderr') {
                                        const progressInfo = this.parseLogForProgress(log.message, currentActivePhase);
                                        if (progressInfo) {
                                            foundProgressInBatch = true;
                                            if (progressInfo.error) {
                                                this.updateProgressIndicator('overall', this.state.overallProgress, 'Error');
                                                this.updateProgressIndicator('step', this.state.stepProgress, 'Error');
                                                this.updateCurrentStep('Error occurred');
                                            } else if (progressInfo.stepText) {
                                                const isNewStep = progressInfo.stepIndex !== undefined &&
                                                    progressInfo.stepIndex !== this.state.currentStepIndex;

                                                if (isNewStep) {
                                                    this.state.currentStepIndex = progressInfo.stepIndex;
                                                    this.state.stepProgress = 0;
                                                    this.state.stepStartTime = Date.now();
                                                }

                                                let stepProgress = progressInfo.stepProgress !== undefined ? progressInfo.stepProgress : 0;

                                                if (stepProgress === 0 && this.state.stepStartTime) {
                                                    const stepDurations = {
                                                        0: 60000,
                                                        1: 120000,
                                                        2: 180000,
                                                        3: 150000,
                                                        4: 30000,
                                                        5: 20000,
                                                        6: 15000
                                                    };
                                                    const estimatedStepDuration = stepDurations[this.state.currentStepIndex] || 60000;
                                                    const timeInStep = Date.now() - this.state.stepStartTime;
                                                    stepProgress = Math.min((timeInStep / estimatedStepDuration) * 100, 95);
                                                }

                                                this.state.stepProgress = stepProgress;

                                                const overallProgress = this.calculateOverallProgress(
                                                    progressInfo.phase || currentActivePhase,
                                                    this.state.currentStepIndex,
                                                    stepProgress
                                                );
                                                this.state.overallProgress = overallProgress;

                                                let stepDisplayText = progressInfo.stepText;
                                                if (progressInfo.progressText) {
                                                    stepDisplayText = `${progressInfo.stepText}: ${progressInfo.progressText}`;
                                                } else if (stepProgress > 0) {
                                                    stepDisplayText = `${progressInfo.stepText}: ${Math.round(stepProgress)}%`;
                                                }

                                                this.updateProgressIndicator('overall', overallProgress, progressInfo.completed ? 'Complete' : `${Math.round(overallProgress)}%`);
                                                this.updateProgressIndicator('step', stepProgress, stepDisplayText);
                                                this.updateCurrentStep(stepDisplayText);

                                                if (phase === 'both' && progressInfo.phase === 'phase1' && progressInfo.completed) {
                                                    currentActivePhase = 'phase2';
                                                    this.state.currentStepIndex = 0;
                                                    this.state.stepProgress = 0;
                                                    this.state.stepStartTime = Date.now();
                                                    this.updateProgressIndicator('step', 0, 'Starting Phase 2...');
                                                }

                                                if (progressInfo.completed) {
                                                    this.state.stepProgress = 100;
                                                    this.updateProgressIndicator('step', 100, `${progressInfo.stepText}: Complete`);
                                                }
                                            }
                                        }
                                    }
                                });

                                if (foundProgressInBatch && this.state.currentStepIndex !== undefined) {
                                    const overallProgress = this.calculateOverallProgress(
                                        currentActivePhase,
                                        this.state.currentStepIndex,
                                        this.state.stepProgress
                                    );
                                    this.state.overallProgress = overallProgress;
                                    this.updateProgressIndicator('overall', overallProgress, `${Math.round(overallProgress)}%`);
                                }

                                lastLogCount = logData.logs.length;
                            }

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
                                    const errorMsg = errorLogs.length > 0 ?
                                        errorLogs.map(l => l.message).join('; ') :
                                        `Process exited with code ${exitCodeNum}`;

                                    this.updateProgressIndicator('overall', this.state.overallProgress, 'Failed');
                                    this.updateProgressIndicator('step', this.state.stepProgress, 'Failed');
                                    this.updateCurrentStep('Process failed');

                                    this.state.commandId = null;

                                    if (this.state.pollInterval) {
                                        clearTimeout(this.state.pollInterval);
                                        this.state.pollInterval = null;
                                    }

                                    setTimeout(() => {
                                        this.closeProgressModal();
                                        showError('Failed to run suite: ' + errorMsg);
                                    }, 3000);
                                    return;
                                }

                                this.updateProgressIndicator('overall', 100, 'Complete ✓');
                                this.updateProgressIndicator('step', 100, 'Complete ✓');
                                this.updateCurrentStep('Reports generated successfully!');

                                this.state.commandId = null;

                                if (this.state.pollInterval) {
                                    clearTimeout(this.state.pollInterval);
                                    this.state.pollInterval = null;
                                }

                                setTimeout(() => {
                                    this.closeProgressModal();
                                    showCompletionAlert(`${btnText} completed successfully!`, 'success');
                                    if (window.loadDeliverables) window.loadDeliverables();
                                    if (window.loadDashboard) window.loadDashboard();
                                }, 2000);
                                return;
                            }
                        }
                    }

                    this.state.pollInterval = setTimeout(pollLogs, 1500);
                } catch (error) {
                    if (error.message && error.message.includes('Process failed')) {
                        this.closeProgressModal();
                        showError('Failed to run suite: ' + error.message);
                    } else {
                        console.error('Error polling logs:', error);
                        this.state.pollInterval = setTimeout(pollLogs, 2000);
                    }
                }
            };

            this.state.pollInterval = setTimeout(pollLogs, 1000);

        } catch (e) {
            this.closeProgressModal();
            showError(`Failed to run suite: ${e.message}`);
            console.error('Suite run error:', e);
        }
    }
}

// Export singleton instance and individual functions
export const progressModalManager = new ProgressModalManager();

export const showProgressModal = (phase) => progressModalManager.showProgressModal(phase);
export const closeProgressModal = () => progressModalManager.closeProgressModal();
export const updateProgressIndicator = (type, percentage, status) => progressModalManager.updateProgressIndicator(type, percentage, status);
export const updateCurrentStep = (step) => progressModalManager.updateCurrentStep(step);
export const updateTimeInfo = () => progressModalManager.updateTimeInfo();
export const cancelProgress = () => progressModalManager.cancelProgress();
export const runPhaseSuite = (phase) => progressModalManager.runPhaseSuite(phase);