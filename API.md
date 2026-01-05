# API Documentation

<div align="center">

**Audio Fingerprint Robustness Lab API**

_Complete API reference for audio file management, processing, manipulation, and analysis_

</div>

---

## Overview

RESTful API for managing audio files, processing experiments, manipulating audio, parsing DAW project files, and generating reports.

| Property         | Value                                                        |
| ---------------- | ------------------------------------------------------------ |
| **Base URL**     | `http://localhost:8080`                                      |
| **Content-Type** | `application/json` (JSON)<br>`multipart/form-data` (Uploads) |

### Quick Start

```bash
# Test server
curl http://localhost:8080/api/status

# Upload audio
curl -X POST http://localhost:8080/api/upload/audio -F "file=@song.wav" -F "directory=originals"
```

---

## Upload Endpoints

### `POST /api/upload/audio`

Upload audio file. Automatically added to manifest CSV.

**Request:** `file` (File, required), `directory` (String, optional, default: `"originals"`)

**Response:**

```json
{
  "status": "success",
  "filename": "song.wav",
  "path": "data/originals/song.wav",
  "size": 1234567,
  "added_to_manifest": true
}
```

**Flow:** Upload → Save to `data/{directory}/` → Add to manifest → Available for processing

---

### `POST /api/daw/upload`

Upload DAW project file (.als, .flp, .logicx).

**Request:** `file` (File, required), `audio_file_id` (String, optional)

**Response:**

```json
{
  "status": "success",
  "file_path": "data/daw_files/project.als",
  "link_info": { "linked": true, "audio_file": "data/originals/song.wav" }
}
```

---

## Process Management Endpoints

All process endpoints return `command_id` for monitoring via `GET /api/process/{command_id}/status` and `GET /api/process/{command_id}/logs`.

### `POST /api/process/create-test-audio`

Generate synthetic test audio files.

**Parameters:** `num_files` (int, default: 2), `duration` (float, default: 5.0), `output_dir` (string, default: "data/test_audio")`

**Response:**

```json
{
  "command_id": "create_audio_20250101_120000",
  "status": "started",
  "message": "Creating test audio files..."
}
```

---

### `POST /api/process/create-manifest`

Create manifest CSV from audio directory.

**Parameters:** `audio_dir` (string, required), `output` (string, default: "data/manifests/test_manifest.csv")`

---

### `POST /api/process/ingest`

Ingest and normalize audio files from manifest.

**Parameters:** `manifest_path` (string, required), `output_dir` (string, default: "data"), `sample_rate` (int, default: 44100)`

---

### `POST /api/process/generate-transforms`

Generate transformed audio files from manifest.

**Parameters:** `manifest_path` (string, required), `test_matrix_path` (string, default: "config/test_matrix.yaml"), `output_dir` (string, default: "data")`

---

### `POST /api/process/run-experiment`

Execute full experiment pipeline.

**Parameters:** `config_path` (string, default: "config/test_matrix.yaml"), `originals_path` (string, required), `skip_steps` (string, optional)`

---

### `POST /api/process/generate-deliverables`

Generate Phase 1 and/or Phase 2 deliverables.

**Parameters:** `manifest_path` (string, default: "data/manifests/files_manifest.csv"), `phase` (string, default: "both": "both", "phase1", or "phase2")`

---

### `GET /api/process/{command_id}/logs`

Get process logs.

**Response:**

```json
{ "logs": [{ "type": "stdout", "message": "Processing file 1/10" }] }
```

---

### `GET /api/process/{command_id}/status`

Get process status.

**Response:**

```json
{ "status": "running", "exit_code": null, "running": true }
```

---

### `POST /api/process/{command_id}/cancel`

Cancel running process.

---

## File Management Endpoints

### `GET /api/files/manifests`

List all manifest files.

### `GET /api/files/audio`

List audio files. **Query:** `directory` (string, default: "originals")

### `GET /api/files/audio-file`

Serve audio file. **Query:** `path` (string, required)

### `GET /api/files/plots/{filename}`

Serve plot images. **Query:** `run_id` (string, optional)

---

## Audio Manipulation Endpoints

All manipulation endpoints return:

```json
{
  "status": "success",
  "output_path": "data/manipulated/song_speed_1.5x.wav",
  "message": "Transform applied"
}
```

**Common Parameters:** `input_path`, `output_dir`, `output_name`

### Core Transformations

- `POST /api/manipulate/speed` - `speed_ratio`, `preserve_pitch`
- `POST /api/manipulate/pitch` - `pitch_semitones`
- `POST /api/manipulate/overlay` - `overlay_path`, `mix_ratio`
- `POST /api/manipulate/reverb` - `reverb_amount`

### Noise Processing

- `POST /api/manipulate/noise-reduction` - `reduction_amount`
- `POST /api/manipulate/noise` - `noise_level`

### Encoding & Formatting

- `POST /api/manipulate/encode` - `codec`, `bitrate`
- `POST /api/manipulate/chop` - `num_segments`

### Equalization

- `POST /api/manipulate/eq` - `eq_settings`
- `POST /api/manipulate/eq/highpass` - `cutoff_freq`
- `POST /api/manipulate/eq/lowpass` - `cutoff_freq`
- `POST /api/manipulate/eq/boost-highs` - `boost_db`
- `POST /api/manipulate/eq/boost-lows` - `boost_db`
- `POST /api/manipulate/eq/telephone`

### Dynamics Processing

- `POST /api/manipulate/dynamics/compression` - `ratio`, `threshold`
- `POST /api/manipulate/dynamics/limiting` - `threshold`
- `POST /api/manipulate/dynamics/multiband` - `settings`

### Cropping Operations

- `POST /api/manipulate/crop/10s`
- `POST /api/manipulate/crop/5s`
- `POST /api/manipulate/crop/middle`
- `POST /api/manipulate/crop/end`

### Advanced Operations

- `POST /api/manipulate/embedded-sample` - `sample_path`, `target_path`
- `POST /api/manipulate/song-a-in-song-b` - `song_a_path`, `song_b_path`
- `POST /api/manipulate/chain` - `transforms`
- `POST /api/manipulate/deliverables-batch` - `transforms`, `generate_reports`, `overlay_file`

---

## DAW Parser Endpoints

### `POST /api/daw/parse`

Parse DAW project file and extract metadata.

**Parameters:** `file_path` (string, required)

**Response:**

```json
{
  "status": "success",
  "metadata": {
    "daw_type": "ableton",
    "version": "11.3",
    "midi_tracks": [...],
    "arrangement": [...],
    "tempo_changes": [...],
    "key_changes": [...],
    "plugin_chains": [...],
    "sample_sources": [...],
    "automation": [...]
  }
}
```

**Supported:** `.als` (Ableton), `.flp` (FL Studio), `.logicx` (Logic Pro)

---

### `GET /api/daw/metadata`

Get DAW metadata. **Query:** `file_id` (string, optional)

---

### `GET /api/daw/files`

List all DAW project files.

---

## Results & Reports Endpoints

### `GET /api/runs`

List all experiment runs.

### `GET /api/runs/{run_id}`

Get detailed run information.

### `GET /api/runs/{run_id}/download`

Download report as ZIP.

### `DELETE /api/runs/{run_id}`

Delete experiment run.

---

## Configuration Endpoints

### `GET /api/config/test-matrix`

Get test matrix configuration.

### `POST /api/config/test-matrix`

Update test matrix configuration. **Body:** JSON object

---

## Status & Monitoring Endpoints

### `GET /api/status`

Get system status.

### `POST /api/test/fingerprint`

Test fingerprinting. **Parameters:** `original_path`, `query_path`, `top_k` (int, default: 10)

---

## Integration Flows

### Upload to Processing

1. `POST /api/upload/audio` → File saved → Added to manifest
2. `POST /api/process/ingest` _(Optional)_ → Normalize audio
3. `POST /api/process/generate-transforms` _(Optional)_ → Generate transforms
4. `POST /api/process/run-experiment` → Run full pipeline
5. `GET /api/runs` → View results

### DAW Upload

1. `POST /api/daw/upload` → Save DAW file → Link to audio (optional)
2. `POST /api/daw/parse` _(Optional)_ → Extract metadata
3. `GET /api/daw/metadata` → Retrieve metadata

### Process Monitoring

1. `POST /api/process/{action}` → Get `command_id`
2. `GET /api/process/{command_id}/status` → Check status
3. `GET /api/process/{command_id}/logs` → Get logs
4. `POST /api/process/{command_id}/cancel` _(Optional)_ → Cancel

---

## Error Handling

**Error Format:**

```json
{
  "status": "error",
  "message": "Error description",
  "error": "Detailed error message"
}
```

**HTTP Status Codes:**

- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

---

## Notes

- All file paths are relative to project root
- Process endpoints return `command_id` for monitoring
- Upload endpoints automatically add files to manifest
- DAW metadata links to audio files when `audio_file_id` provided
- Manifest CSV format: `id,title,file_path`

---

<div align="center">

**API Documentation v1.0** | _50+ Endpoints_

</div>
