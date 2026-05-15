import numpy as np

from software.layer1_sensor_hub.mmwave_dca import AdcCaptureShape, read_adc_data
from software.layer1_sensor_hub.mmwave_dca.adc_reader import range_doppler_map


def test_read_adc_data_ti_iq_order(tmp_path):
    path = tmp_path / "adc_data.bin"
    # TI order for two complex values: I0, I1, Q0, Q1
    np.array([1, 2, 10, 20], dtype=np.int16).tofile(path)

    adc = read_adc_data(path, AdcCaptureShape(frames=1, chirps=1, rx=1, samples=2))

    assert adc.shape == (1, 1, 1, 2)
    assert adc[0, 0, 0, 0] == 1 + 10j
    assert adc[0, 0, 0, 1] == 2 + 20j


def test_range_doppler_map_shape():
    adc_frame = np.ones((4, 2, 8), dtype=np.complex64)

    rd = range_doppler_map(adc_frame)

    assert rd.shape == (4, 8)
