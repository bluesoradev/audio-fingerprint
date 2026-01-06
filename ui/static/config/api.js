/**
 * API Configuration
 * Centralized API endpoint configuration
 */

export const API_CONFIG = {
    BASE_URL: 'http://148.251.88.48:8080/api',
    TIMEOUT: 3000,
    ENDPOINTS: {
        STATUS: '/status',
        RUNS: '/runs',
        PROCESS: {
            CREATE_TEST_AUDIO: '/process/create-test-audio',
            CREATE_MANIFEST: '/process/create-manifest',
            INGEST: '/process/ingest',
            GENERATE_TRANSFORMS: '/process/generate-transforms',
            RUN_EXPERIMENT: '/process/run-experiment',
            GENERATE_DELIVERABLES: '/process/generate-deliverables',
            LOGS: (id) => `/process/${id}/logs`,
            STATUS: (id) => `/process/${id}/status`,
            CANCEL: (id) => `/process/${id}/cancel`
        },
        FILES: {
            MANIFESTS: '/files/manifests',
            AUDIO: '/files/audio',
            AUDIO_FILE: '/files/audio-file',
            REPORT: '/files/report',
            PLOTS: '/files/plots'
        },
        UPLOAD: {
            AUDIO: '/upload/audio'
        },
        MANIPULATE: {
            SPEED: '/manipulate/speed',
            PITCH: '/manipulate/pitch',
            REVERB: '/manipulate/reverb',
            NOISE_REDUCTION: '/manipulate/noise-reduction',
            EQ: '/manipulate/eq',
            ENCODE: '/manipulate/encode',
            OVERLAY: '/manipulate/overlay',
            NOISE: '/manipulate/noise',
            CHOP: '/manipulate/chop',
            CHAIN: '/manipulate/chain',
            DELIVERABLES_BATCH: '/manipulate/deliverables-batch',
            EQ_HIGHPASS: '/manipulate/eq/highpass',
            EQ_LOWPASS: '/manipulate/eq/lowpass',
            EQ_BOOST_HIGHS: '/manipulate/eq/boost-highs',
            EQ_BOOST_LOWS: '/manipulate/eq/boost-lows',
            EQ_TELEPHONE: '/manipulate/eq/telephone',
            DYNAMICS_LIMITING: '/manipulate/dynamics/limiting',
            DYNAMICS_MULTIBAND: '/manipulate/dynamics/multiband',
            CROP_10S: '/manipulate/crop/10s',
            CROP_5S: '/manipulate/crop/5s',
            CROP_MIDDLE: '/manipulate/crop/middle',
            CROP_END: '/manipulate/crop/end',
            EMBEDDED_SAMPLE: '/manipulate/embedded-sample',
            SONG_A_IN_SONG_B: '/manipulate/song-a-in-song-b'
        },
        TEST: {
            FINGERPRINT: '/test/fingerprint'
        },
        CONFIG: {
            TEST_MATRIX: '/config/test-matrix'
        },
        DAW: {
            FILES: '/daw/files',
            UPLOAD: '/daw/upload',
            PARSE: '/daw/parse',
            METADATA: '/daw/metadata'
        }
    }
};