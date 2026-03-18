"""Realtime bridge from Layer 1 radar acquisition into Layer 2 processing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from software.layer1_radar import DEFAULT_CONFIG, RadarConfigurator, SerialManager, UARTSource

from .feature_extractor import FeatureExtractor, HeatmapFeatures
from .signal_processor import ProcessedFrame, SignalProcessor


@dataclass(frozen=True, slots=True)
class RealtimeFrame:
    """One realtime frame after passing from Layer 1 into Layer 2."""

    raw_frame: bytes
    processed: ProcessedFrame
    features: HeatmapFeatures


class Layer1RealtimePipeline:
    """Coordinates live Layer 1 radar IO with Layer 2 processing."""

    def __init__(
        self,
        serial_manager: SerialManager | None = None,
        signal_processor: SignalProcessor | None = None,
        feature_extractor: FeatureExtractor | None = None,
        uart_buffer_size: int = 65536,
    ) -> None:
        self.serial_manager = serial_manager if serial_manager is not None else SerialManager()
        self.signal_processor = signal_processor if signal_processor is not None else SignalProcessor()
        self.feature_extractor = feature_extractor if feature_extractor is not None else FeatureExtractor()
        self.configurator = RadarConfigurator(self.serial_manager)
        self.uart_source = UARTSource(self.serial_manager, buffer_size=uart_buffer_size)

    def connect_and_configure(
        self,
        config_port: str | None = None,
        data_port: str | None = None,
        config_path: str | Path | None = None,
        config_text: str | None = None,
    ) -> None:
        """Connect to radar ports and start the sensor."""

        if config_port is None or data_port is None:
            ports = self.serial_manager.find_radar_ports()
            config_port = ports.config_port
            data_port = ports.data_port

        self.serial_manager.connect(config_port, data_port)

        if config_path is not None:
            result = self.configurator.configure_from_file(Path(config_path))
        else:
            result = self.configurator.configure(config_text or DEFAULT_CONFIG)

        if not result.success:
            joined = "\n".join(result.errors)
            raise RuntimeError(f"Radar configuration failed:\n{joined}")

        self.serial_manager.flush_data_port()
        self.uart_source.clear_buffer()

    def stream(self, max_frames: int = 0) -> Generator[RealtimeFrame, None, None]:
        """Yield realtime Layer 2 outputs from live Layer 1 frames."""

        for raw_frame in self.uart_source.stream_frames(max_frames=max_frames):
            processed = self.signal_processor.process(raw_frame)
            features = self.feature_extractor.extract(processed)
            yield RealtimeFrame(raw_frame=raw_frame, processed=processed, features=features)

    def close(self) -> None:
        """Stop radar and close serial ports."""

        try:
            if self.serial_manager.is_connected:
                self.configurator.stop()
        finally:
            self.serial_manager.disconnect()
