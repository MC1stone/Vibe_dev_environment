# MQTT topic specification for the acquisition layer

## Topics

### 1. sensor registration
- `spectral/sensor/register`
- Payload example:
  ```json
  {
    "name": "DIY Matchbox Spectrometer",
    "interface_type": "usb_camera",
    "device_path": "/dev/video0",
    "serial_number": "MBS-001",
    "connection_settings": {"resolution": "1920x1080"},
    "metadata": {"location": "lab-a"}
  }
  ```

### 2. acquisition session start
- `spectral/session/create`
- Payload example:
  ```json
  {
    "sensor_id": 1,
    "name": "scan-001",
    "metadata": {"sample": "water"},
    "notes": "initial capture"
  }
  ```

### 3. raw frame capture
- `spectral/raw/capture`
- Payload example:
  ```json
  {
    "session_id": 1,
    "sample_id": "sample-01",
    "exposure_ms": 250,
    "file_path": "/data/frames/frame_001.png",
    "metadata": {"temperature_c": 22.5},
    "raw_payload": {
      "width": 2048,
      "height": 1536,
      "mode": "grayscale"
    }
  }
  ```

### 4. session status updates
- `spectral/session/status`

### 5. system health
- `spectral/system/health`

## Rules

- JSON payloads only.
- Every message should include a UTC timestamp.
- Metadata must be preserved for reproducibility.
- Acquisition sessions remain raw-data only; no processing/calibration is performed in this layer.
