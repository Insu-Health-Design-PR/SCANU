# Layer 2: Signal Processing

## Objective
Transform Layer 1 radar outputs into calibrated spectral outputs and heatmap-ready features.

## Inputs
- Raw `bytes` directly from `layer1_radar.UARTSource.read_frame()`.
- Parsed `ParsedFrame` objects from `layer1_radar.TLVParser.parse()`.

## Outputs
- `ProcessedFrame(frame_number, timestamp_ms, range_doppler, point_cloud)`.
- `HeatmapFeatures(frame_number, timestamp_ms, range_heatmap, doppler_heatmap, vector)`.

## Python Files
- `frame_buffer.py`: fixed-size ring buffer for Layer 1-compatible inputs.
- `calibration.py`: exponential moving background subtraction.
- `signal_processor.py`: input normalization plus FFT + CFAR processing and sparse detection point cloud extraction.
- `feature_extractor.py`: range and doppler heatmap projections plus summary vector.
- `test_parser.py`: parser unit tests (Layer 1 parser coverage driven by Layer 2 task scope).
- `__init__.py`: public API exports.

## Recommended Flow
1. Layer 1 emits raw UART frame bytes or parsed radar frames.
2. Optionally cache a temporal window with `FrameBuffer`.
3. `SignalProcessor.process()` chooses the best available signal source:
   `range_profile`, `noise_profile`, or flattened point samples.
4. When raw Layer 1 bytes are provided, `SignalProcessor` first parses the TLV frame and then processes the parsed output.
5. Processor runs calibration, range-doppler FFT, then CFAR thresholding.
6. Processor emits a typed `ProcessedFrame`.
7. `FeatureExtractor.extract()` builds heatmaps and vector features for downstream inference.

## Definition of Done (DoD)
- Typed and documented APIs.
- Deterministic behavior with lightweight numerical operations.


## ~/Desktop/SCANU-dev_adrian/SCANU
## ~/Desktop/SCANU-dev_adrian/SCANU/software/layer2_signal_processing
## cd ~/Desktop/SCANU-dev_adrian/SCANU
python3 -m unittest software.layer2_signal_processing.test_signal_processor -v
python3 -m unittest software.layer2_signal_processing.test_parser -v
##cd ~/Desktop/SCANU-dev_adrian/SCANU
python3





from software.layer1_radar import SerialManager, RadarConfigurator, UARTSource, TLVParser
from software.layer2_signal_processing import SignalProcessor, FeatureExtractor

serial_mgr = SerialManager()
ports = serial_mgr.find_radar_ports()
serial_mgr.connect(ports.config_port, ports.data_port)

configurator = RadarConfigurator(serial_mgr)
configurator.configure()

uart = UARTSource(serial_mgr)
parser = TLVParser()
processor = SignalProcessor()
feature_extractor = FeatureExtractor()

raw_frame = uart.read_frame()
parsed = parser.parse(raw_frame)
processed = processor.process(parsed)
features = feature_extractor.extract(processed)

print("frame:", processed.frame_number)
print("range_doppler shape:", processed.range_doppler.shape)
print("point_cloud shape:", processed.point_cloud.shape)
print("vector:", features.vector)

configurator.stop()
serial_mgr.disconnect()

- Parser unit tests runnable from Layer 2 task context.
- End-to-end compatibility with downstream feature consumers.
