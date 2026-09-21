"""S4 verification: spectrometer adapter abstraction layer.

Tests the device-driver contract (base interface), the adapter registry and
the concrete adapters (DIY matchbox, ESP32-S3 MQTT payload parsing per
HANDHELD/mqtt/topic-spec.md, SparkFun Triad Qwiic multispectral sensor).
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
from devices.sparkfun_triad import SparkFunTriadAdapter, TRIAD_WAVELENGTHS

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


# T1: adapter contract - both adapters implement the abstract interface
abstract_methods = {'get_capabilities', 'connect', 'disconnect', 'get_calibration',
                    'get_device_status', 'acquire_measurement'}
for cls in (DIYMatchboxAdapter, ESP32S3CameraAdapter, SparkFunTriadAdapter):
    missing = abstract_methods - set(cls.__dict__.keys())
    inherited_ok = all(callable(getattr(cls, m)) for m in abstract_methods)
    check(f'T1 contract {cls.__name__}',
          issubclass(cls, SpectrometerAdapter) and inherited_ok and not missing,
          f'missing={missing or "none"}')

# T2: registry registration + lookup
reg = get_registry()
check('T2a registry contains all adapters',
      reg.is_registered('diy_matchbox') and reg.is_registered('esp32_s3_camera')
      and reg.is_registered('sparkfun_triad'),
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

# T9: SparkFun Triad adapter - registry, capabilities and lifecycle
triad = reg.create('sparkfun_triad', config={'serial_number': 'TRIAD-042',
                                            'calibration': {'valid': True}})
check('T9a registry create sparkfun_triad',
      triad is not None and triad.serial_number == 'TRIAD-042')
check('T9b triad connect', triad.connect() is True and triad.get_device_status() == DeviceStatus.CONNECTED)
tcaps = triad.get_capabilities()
check('T9c triad capabilities (18 channels, 410-940 nm, qwiic_i2c)',
      tcaps.interface_type == 'qwiic_i2c'
      and tcaps.wavelength_range_nm == (410.0, 940.0)
      and tcaps.metadata['num_channels'] == 18
      and len(TRIAD_WAVELENGTHS) == 18
      and tcaps.detector_type == 'as7262+as7263+ml8511')
check('T9d triad calibration from config', triad.get_calibration().valid is True)
triad.disconnect()
check('T9e triad disconnect', triad.get_device_status() == DeviceStatus.DISCONNECTED)

# T10: Triad channel payload in lab-data style (A_410 .. L_940) -> unified schema
triad2 = SparkFunTriadAdapter()
assert triad2.connect() is True
lab_channels = {
    'A_410': 630.23, 'B_435': 1111.21, 'C_460': 6754.32, 'D_485': 501.53,
    'E_510': 1657.19, 'F_535': 7516.47, 'G_560': 881.94, 'H_585': 1525.95,
    'R_610': 20729.77, 'I_645': 2837.55, 'S_680': 3678.37, 'J_705': 1581.28,
    'T_730': 2219.16, 'U_760': 1080.64, 'V_810': 2860.49, 'W_860': 3099.48,
    'K_900': 2717.21, 'L_940': 1095.82,
}
t_result = triad2.acquire_measurement({'channel_payload': {
    'channels': dict(lab_channels),
    'sample_id': 'tomato-1000',
    'integration_time_ms': 100,
    'gain': '64x',
    'metadata': {'temperature_c': 22.0},
}})
ok = (t_result is not None
      and t_result['metadata']['device'] == 'sparkfun_triad'
      and t_result['metadata']['sample_id'] == 'tomato-1000'
      and t_result['metadata']['integration_time_ms'] == 100
      and t_result['metadata']['temperature_c'] == 22.0
      and t_result['format'] == 'triad_channels'
      and t_result['wavelength_column'] == 'wavelength'
      and len(t_result['data']) == 18
      and list(t_result['data']['wavelength']) == TRIAD_WAVELENGTHS
      and t_result['data']['intensity'].iloc[0] == 630.23
      and t_result['data']['intensity'].iloc[17] == 1095.82)
check('T10 triad lab-style channels -> unified schema', ok)

# T11: Triad alternative payload styles (nm keys, intensities list)
nm_result = SparkFunTriadAdapter.parse_channel_payload(
    {'channels': {f'{wl:g}': float(i) for wl, i in zip(TRIAD_WAVELENGTHS, range(18))}},
    TRIAD_WAVELENGTHS)
list_result = SparkFunTriadAdapter.parse_channel_payload(
    {'intensities': [float(i) for i in range(18)]}, TRIAD_WAVELENGTHS)
check('T11 triad nm-key and intensities-list payload styles',
      nm_result is not None and list_result is not None
      and nm_result['data']['intensity'].iloc[9] == 9.0
      and list_result['data']['intensity'].iloc[17] == 17.0)

# T12: Triad invalid payloads and disconnected refusal
bad_a = SparkFunTriadAdapter()
assert bad_a.connect() is True
bad = bad_a.acquire_measurement({'channel_payload': {'channels': {'A_410': 1.0}}})
check('T12a incomplete channel payload -> None + error status',
      bad is None and bad_a.last_error is not None
      and bad_a.get_device_status() == DeviceStatus.ERROR)
bad_b = SparkFunTriadAdapter()
refused = bad_b.acquire_measurement({'channel_payload': {'intensities': [1.0] * 18}})
check('T12b disconnected -> refuse measurement',
      refused is None and bad_b.last_error is not None)
wrong_len = SparkFunTriadAdapter.parse_channel_payload(
    {'intensities': [1.0, 2.0]}, TRIAD_WAVELENGTHS)
check('T12c wrong intensities length -> None', wrong_len is None)

failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
sys.exit(1 if failed else 0)
