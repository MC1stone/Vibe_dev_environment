"""S4 verification: spectrometer adapter abstraction layer.

Tests the device-driver contract (base interface), the adapter registry and
both concrete adapters (DIY matchbox, ESP32-S3 MQTT payload parsing per
HANDHELD/mqtt/topic-spec.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from devices import (
    DeviceStatus,
    SpectrometerAdapter,
    get_registry,
)
from devices.diy_matchbox import DIYMatchboxAdapter
from devices.esp32_s3_camera import ESP32S3CameraAdapter

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


# T1: adapter contract - both adapters implement the abstract interface
abstract_methods = {'get_capabilities', 'connect', 'disconnect', 'get_calibration',
                    'get_device_status', 'acquire_measurement'}
for cls in (DIYMatchboxAdapter, ESP32S3CameraAdapter):
    missing = abstract_methods - set(cls.__dict__.keys())
    inherited_ok = all(callable(getattr(cls, m)) for m in abstract_methods)
    check(f'T1 contract {cls.__name__}',
          issubclass(cls, SpectrometerAdapter) and inherited_ok and not missing,
          f'missing={missing or "none"}')

# T2: registry registration + lookup
reg = get_registry()
check('T2a registry contains both adapters',
      reg.is_registered('diy_matchbox') and reg.is_registered('esp32_s3_camera'),
      f'models={reg.list_models()}')
check('T2b unknown model -> None', reg.get('nonexistent_model') is None)
instance = reg.create('esp32_s3_camera', config={'mqtt_host': 'broker.local', 'mqtt_port': 1884})
check('T2c registry create with config',
      instance is not None and instance.mqtt_host == 'broker.local' and instance.mqtt_port == 1884)

# T3: ESP32-S3 capture payload parsing (topic spectral/raw/capture)
adapter = ESP32S3CameraAdapter(config={'mqtt_host': 'localhost'})
assert adapter.connect() is True
capture = {
    'session_id': 1,
    'sample_id': 'sample-01',
    'exposure_ms': 250,
    'file_path': '/data/frames/frame_001.png',
    'metadata': {'temperature_c': 22.5},
    'spectral': {'wavelength': [400, 500, 600], 'intensity': [0.1, 0.5, 0.9]},
    'raw_payload': {'width': 2048, 'height': 1536, 'mode': 'grayscale'},
}
result = adapter.acquire_measurement({'capture_payload': capture})
ok = (result is not None
      and result['metadata']['device'] == 'esp32_s3_camera'
      and result['metadata']['session_id'] == 1
      and result['metadata']['exposure_ms'] == 250
      and result['metadata']['temperature_c'] == 22.5
      and result['data']['wavelength'] == [400, 500, 600]
      and result['wavelength_column'] == 'wavelength'
      and adapter.get_device_status() == DeviceStatus.CONNECTED)
check('T3 ESP32 capture -> unified schema', ok)

# T4: invalid capture payload rejected gracefully
bad = adapter.acquire_measurement({'capture_payload': {'session_id': 2}})
check('T4 invalid payload -> None + error status', bad is None and adapter.last_error is not None)
assert adapter.connect() is True

# T5: measurement refused when disconnected
disconnected = ESP32S3CameraAdapter()
refused = disconnected.acquire_measurement({'capture_payload': capture})
check('T5 disconnected -> refuse measurement', refused is None and disconnected.last_error is not None)

# T6: register payload parsing (topic spectral/sensor/register)
reg_payload = {
    'name': 'DIY Matchbox Spectrometer',
    'interface_type': 'usb_camera',
    'device_path': '/dev/video0',
    'serial_number': 'MBS-001',
    'connection_settings': {'resolution': '1920x1080'},
    'metadata': {'location': 'lab-a'},
}
parsed = ESP32S3CameraAdapter.parse_register_payload(reg_payload)
check('T6 register payload parsing',
      parsed['serial_number'] == 'MBS-001' and parsed['interface_type'] == 'usb_camera'
      and parsed['metadata'] == {'location': 'lab-a'})

# T7: DIY matchbox adapter lifecycle + capabilities
mb = DIYMatchboxAdapter(config={'device_path': '/dev/video1', 'serial_number': 'MBS-042',
                                'calibration': {'valid': True, 'wavelength': {'a': 1}}})
check('T7a matchbox connect', mb.connect() is True and mb.get_device_status() == DeviceStatus.CONNECTED)
caps = mb.get_capabilities()
check('T7b capabilities', caps.detector_type == 'usb_camera' and caps.interface_type == 'usb_camera'
      and caps.wavelength_range_nm == (380.0, 780.0))
cal = mb.get_calibration()
check('T7c calibration from config', cal.valid is True and cal.wavelength_calibration == {'a': 1})
mb_result = mb.acquire_measurement({'capture_payload': dict(capture)})
check('T7d matchbox capture -> unified schema',
      mb_result is not None and mb_result['metadata']['device'] == 'diy_matchbox'
      and mb_result['metadata']['serial_number'] == 'MBS-042')
mb.disconnect()
check('T7e disconnect', mb.get_device_status() == DeviceStatus.DISCONNECTED)

# T8: registry rejects adapters without MODEL_ID
class BadAdapter(SpectrometerAdapter):
    MODEL_ID = 'unknown'
    def get_capabilities(self): pass
    def connect(self): pass
    def disconnect(self): pass
    def get_calibration(self): pass
    def get_device_status(self): pass
    def acquire_measurement(self, options=None): pass

try:
    reg.register(BadAdapter)
    check('T8 registry rejects MODEL_ID "unknown"', False)
except ValueError:
    check('T8 registry rejects MODEL_ID "unknown"', True)

failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
sys.exit(1 if failed else 0)
