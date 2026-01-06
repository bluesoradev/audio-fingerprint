/**
 * Workflow Component
 * Handles workflow operations: test audio creation, manifest, ingest, transforms, experiments
 */

import {
    API_CONFIG
} from '../config/api.js';
import {
    apiClient
} from '../api/client.js';
import {
    getElement
} from '../utils/helpers.js';
import {
    showError,
    showCompletionAlert
} from './notifications.js';

class WorkflowManager {
    constructor() {
        this.apiBase = API_CONFIG.BASE_URL;
    }

    /**
     * Create test audio files
     */
    async createTestAudio() {
        const numFiles = getElement('numFiles') ? .value;
        const duration = getElement('duration') ? .value;
        const outputDir = getElement('audioOutputDir') ? .value;

        if (!numFiles || !duration || !outputDir) {
            showError('Please fill in all fields');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('num_files', numFiles);
            formData.append('duration', duration);
            formData.append('output_dir', outputDir);

            const result = await apiClient.post(API_CONFIG.ENDPOINTS.PROCESS.CREATE_TEST_AUDIO, formData);

            if (result.command_id) {
                if (typeof startProcessMonitoring === 'function') {
                    startProcessMonitoring(result.command_id, 'Creating test audio files...', 'Create Test Audio');
                }
            } else {
                showError('No command ID returned from server');
            }
        } catch (error) {
            console.error('Create test audio error:', error);
            showError('Failed to start process: ' + (error.message || 'Unknown error'));
        }
    }

    /**
     * Create manifest file
     */
    async createManifest() {
        const audioDir = getElement('audioDir') ? .value;
        const output = getElement('manifestOutput') ? .value;

        try {
            const formData = new FormData();
            formData.append('audio_dir', audioDir);
            formData.append('output', output);

            const result = await apiClient.post(API_CONFIG.ENDPOINTS.PROCESS.CREATE_MANIFEST, formData);

            if (result.command_id && typeof startProcessMonitoring === 'function') {
                startProcessMonitoring(result.command_id, 'Creating manifest...', 'Create Manifest');
            }
        } catch (error) {
            showError('Failed to start process: ' + error.message);
        }
    }

    /**
     * Ingest files
     */
    async ingestFiles() {
        const manifestPath = getElement('ingestManifest') ? .value;
        const sampleRate = getElement('sampleRate') ? .value;

        if (!manifestPath) {
            showError('Please select a manifest file');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('manifest_path', manifestPath);
            formData.append('output_dir', 'data');
            formData.append('sample_rate', sampleRate);

            const result = await apiClient.post(API_CONFIG.ENDPOINTS.PROCESS.INGEST, formData);

            if (result.command_id && typeof startProcessMonitoring === 'function') {
                startProcessMonitoring(result.command_id, 'Ingesting files...', 'Ingest Files');
            }
        } catch (error) {
            showError('Failed to start process: ' + error.message);
        }
    }

    /**
     * Generate transforms
     */
    async generateTransforms() {
        const manifestPath = getElement('transformManifest') ? .value;

        if (!manifestPath) {
            showError('Please select a manifest file');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('manifest_path', manifestPath);
            formData.append('test_matrix_path', 'config/test_matrix.yaml');
            formData.append('output_dir', 'data');

            const result = await apiClient.post(API_CONFIG.ENDPOINTS.PROCESS.GENERATE_TRANSFORMS, formData);

            if (result.command_id && typeof startProcessMonitoring === 'function') {
                startProcessMonitoring(result.command_id, 'Generating transforms...', 'Generate Transforms');
            }
        } catch (error) {
            showError('Failed to start process: ' + error.message);
        }
    }

    /**
     * Run full experiment
     */
    async runExperiment() {
        const manifestPath = getElement('experimentManifest') ? .value;

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

            const result = await apiClient.post(API_CONFIG.ENDPOINTS.PROCESS.RUN_EXPERIMENT, formData);

            if (result.command_id && typeof startProcessMonitoring === 'function') {
                startProcessMonitoring(result.command_id, 'Running full experiment...', 'Run Experiment');
            }
        } catch (error) {
            showError('Failed to start process: ' + error.message);
        }
    }
}

export const workflowManager = new WorkflowManager();
export const createTestAudio = () => workflowManager.createTestAudio();
export const createManifest = () => workflowManager.createManifest();
export const ingestFiles = () => workflowManager.ingestFiles();
export const generateTransforms = () => workflowManager.generateTransforms();
export const runExperiment = () => workflowManager.runExperiment();