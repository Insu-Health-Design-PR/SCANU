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
- `testing/`: tests, runners, and sample Layer 1 captures used during development.
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


from software.layer1_radar import SerialManager, RadarConfigurator, UARTSource, TLVParser
from software.layer2_signal_processing import SignalProcessor, FeatureExtractor

serial_mgr = SerialManager()
ports = serial_mgr.find_radar_ports()
print("Ports:", ports)

serial_mgr.connect(ports.config_port, ports.data_port)

configurator = RadarConfigurator(serial_mgr)
result = configurator.configure()
print("Config success:", result.success)

uart = UARTSource(serial_mgr)
parser = TLVParser()
processor = SignalProcessor()
feature_extractor = FeatureExtractor()

raw_frame = uart.read_frame()
print("Got raw frame:", raw_frame is not None, "bytes:", len(raw_frame) if raw_frame else 0)

parsed = parser.parse(raw_frame)
print("Frame number:", parsed.frame_number)
print("Detected points:", len(parsed.points))
print("Has range profile:", parsed.range_profile is not None)
print("Stats:", parsed.stats)

processed = processor.process(parsed)
features = feature_extractor.extract(processed)

print("range_doppler shape:", processed.range_doppler.shape)
print("point_cloud shape:", processed.point_cloud.shape)
print("feature vector:", features.vector)

configurator.stop()
serial_mgr.disconnect()
