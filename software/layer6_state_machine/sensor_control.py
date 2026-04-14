"""Sensor and radar control plane for Layer 6."""

from __future__ import annotations

import importlib
import importlib.util
import time
from pathlib import Path
from typing import Any, Iterable

from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager

from .models import ControlResult, RadarRuntimeSpec, SensorStatus


class _NoopKillSwitch:
    """Fallback when optional kill-switch script is not present in this checkout."""

    @staticmethod
    def try_soft_uart_reset(_config_port: str, _data_port: str) -> None:
        return None

    @staticmethod
    def pids_holding_device(_device: str) -> list[int]:
        return []

    @staticmethod
    def terminate_pids(_pids: list[int], *, force: bool = False) -> None:
        _ = force
        return None

    @staticmethod
    def usb_reset_by_port(_port: str) -> None:
        return None


class SensorControlManager:
    """Runtime manager for radar status/config/reset and manual destructive controls."""

    def __init__(
        self,
        *,
        radars: Iterable[RadarRuntimeSpec] | None = None,
        serial_manager_factory: type[SerialManager] = SerialManager,
        configurator_factory: type[RadarConfigurator] = RadarConfigurator,
        kill_switch_module: Any | None = None,
    ) -> None:
        specs = list(radars or [RadarRuntimeSpec(radar_id="radar_main")])
        self._radars: dict[str, RadarRuntimeSpec] = {spec.radar_id: spec for spec in specs}
        if "radar_main" not in self._radars:
            raise ValueError("radar_main is required")

        self._serial_manager_factory = serial_manager_factory
        self._configurator_factory = configurator_factory
        self._kill_switch = (
            kill_switch_module
            if kill_switch_module is not None
            else self._load_kill_switch_module()
        )

        self._runtime_status: dict[str, SensorStatus] = {
            radar_id: SensorStatus(
                radar_id=radar_id,
                connected=False,
                configured=False,
                streaming=False,
                fault_code=None,
                last_seen_ms=None,
                config_port=spec.config_port,
                data_port=spec.data_port,
            )
            for radar_id, spec in self._radars.items()
        }

    @staticmethod
    def _load_kill_switch_module() -> Any:
        """Load radar_kill_switch without importing optional cv2-heavy packages."""
        try:
            return importlib.import_module("software.layer1_sensor_hub.examples.radar_kill_switch")
        except Exception:
            pass

        path = (
            Path(__file__).resolve().parents[1]
            / "layer1_sensor_hub"
            / "examples"
            / "radar_kill_switch.py"
        )
        spec = importlib.util.spec_from_file_location("layer1_radar_kill_switch", path)
        if spec is None or spec.loader is None:
            return _NoopKillSwitch()
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            return module
        except FileNotFoundError:
            return _NoopKillSwitch()

    def list_radar_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._radars.keys()))

    def _require(self, radar_id: str) -> RadarRuntimeSpec:
        if radar_id not in self._radars:
            raise KeyError(f"Unknown radar_id '{radar_id}'. Known: {sorted(self._radars)}")
        return self._radars[radar_id]

    @staticmethod
    def _now_ms() -> float:
        return time.time() * 1000.0

    def _status_update(self, radar_id: str, **kwargs: object) -> None:
        old = self._runtime_status[radar_id]
        self._runtime_status[radar_id] = SensorStatus(
            radar_id=radar_id,
            connected=bool(kwargs.get("connected", old.connected)),
            configured=bool(kwargs.get("configured", old.configured)),
            streaming=bool(kwargs.get("streaming", old.streaming)),
            fault_code=kwargs.get("fault_code", old.fault_code),
            last_seen_ms=float(kwargs.get("last_seen_ms", old.last_seen_ms or self._now_ms())),
            config_port=str(kwargs.get("config_port", old.config_port)) if kwargs.get("config_port", old.config_port) else None,
            data_port=str(kwargs.get("data_port", old.data_port)) if kwargs.get("data_port", old.data_port) else None,
        )

    def _resolve_ports(self, radar_id: str, *, allow_discovery: bool = True) -> tuple[str, str]:
        spec = self._require(radar_id)

        if spec.config_port and spec.data_port:
            return (spec.config_port, spec.data_port)

        if not allow_discovery:
            raise RuntimeError(f"Ports missing for {radar_id}")

        mgr = self._serial_manager_factory()
        ports = mgr.find_radar_ports(verbose=False, config_port=spec.config_port, data_port=spec.data_port)
        self._radars[radar_id] = RadarRuntimeSpec(
            radar_id=spec.radar_id,
            config_port=ports.config_port,
            data_port=ports.data_port,
            default_config_path=spec.default_config_path,
        )
        return (ports.config_port, ports.data_port)

    def get_status(self, radar_id: str) -> SensorStatus:
        spec = self._require(radar_id)

        connected = False
        try:
            config_port, data_port = self._resolve_ports(radar_id, allow_discovery=True)
            connected = bool(config_port and data_port)
            self._status_update(
                radar_id,
                connected=connected,
                config_port=config_port,
                data_port=data_port,
                last_seen_ms=self._now_ms(),
            )
        except Exception as exc:
            self._status_update(radar_id, connected=False, fault_code=f"status_probe_failed:{exc}")

        status = self._runtime_status[radar_id]
        # Keep values from runtime status while refreshing static metadata.
        return SensorStatus(
            radar_id=radar_id,
            connected=connected if connected else status.connected,
            configured=status.configured,
            streaming=status.streaming,
            fault_code=status.fault_code,
            last_seen_ms=status.last_seen_ms,
            config_port=spec.config_port,
            data_port=spec.data_port,
        )

    def apply_config(
        self,
        radar_id: str,
        *,
        config_path: str | None = None,
        config_text: str | None = None,
    ) -> ControlResult:
        spec = self._require(radar_id)
        mgr = self._serial_manager_factory()

        try:
            config_port, data_port = self._resolve_ports(radar_id, allow_discovery=True)
            mgr.connect(config_port, data_port)
            configurator = self._configurator_factory(mgr)

            if config_text is not None:
                result = configurator.configure(config_text)
                source = "config_text"
            elif config_path is not None:
                result = configurator.configure_from_file(Path(config_path))
                source = str(config_path)
            elif spec.default_config_path:
                result = configurator.configure_from_file(Path(spec.default_config_path))
                source = str(spec.default_config_path)
            else:
                result = configurator.configure(None)
                source = "default_config"

            ok = bool(result.success)
            self._status_update(
                radar_id,
                connected=True,
                configured=ok,
                streaming=ok,
                fault_code=None if ok else "config_failed",
                config_port=config_port,
                data_port=data_port,
                last_seen_ms=self._now_ms(),
            )

            return ControlResult(
                radar_id=radar_id,
                action="apply_config",
                success=ok,
                message="Radar configured" if ok else "Radar configuration failed",
                details={
                    "source": source,
                    "commands_sent": int(result.commands_sent),
                    "errors": list(result.errors),
                },
            )
        except Exception as exc:
            self._status_update(radar_id, connected=False, configured=False, streaming=False, fault_code=str(exc))
            return ControlResult(
                radar_id=radar_id,
                action="apply_config",
                success=False,
                message=f"Configuration error: {exc}",
            )
        finally:
            try:
                mgr.disconnect()
            except Exception:
                pass

    def reset_soft(self, radar_id: str) -> ControlResult:
        """Best-effort stop + flush on CLI/DATA UART."""
        try:
            config_port, data_port = self._resolve_ports(radar_id, allow_discovery=True)
            self._kill_switch.try_soft_uart_reset(config_port, data_port)
            self._status_update(
                radar_id,
                connected=True,
                streaming=False,
                fault_code=None,
                config_port=config_port,
                data_port=data_port,
                last_seen_ms=self._now_ms(),
            )
            return ControlResult(
                radar_id=radar_id,
                action="reset_soft",
                success=True,
                message="Soft reset executed",
                details={"config_port": config_port, "data_port": data_port},
            )
        except Exception as exc:
            self._status_update(radar_id, fault_code=f"reset_soft_failed:{exc}")
            return ControlResult(
                radar_id=radar_id,
                action="reset_soft",
                success=False,
                message=f"Soft reset failed: {exc}",
            )

    def kill_holders(self, radar_id: str, *, force: bool = False, manual_confirm: bool = False) -> ControlResult:
        if not manual_confirm:
            return ControlResult(
                radar_id=radar_id,
                action="kill_holders",
                success=False,
                message="manual_confirm=True is required for destructive actions",
                details={"manual_required": True},
            )

        try:
            config_port, data_port = self._resolve_ports(radar_id, allow_discovery=True)
            devices = [config_port, data_port]
            pids: set[int] = set()
            for dev in devices:
                pids.update(self._kill_switch.pids_holding_device(dev))

            self._kill_switch.terminate_pids(sorted(pids), force=bool(force))
            self._status_update(radar_id, streaming=False, last_seen_ms=self._now_ms())
            return ControlResult(
                radar_id=radar_id,
                action="kill_holders",
                success=True,
                message="Holder processes terminated",
                details={"pid_count": len(pids), "force": bool(force)},
            )
        except Exception as exc:
            self._status_update(radar_id, fault_code=f"kill_failed:{exc}")
            return ControlResult(
                radar_id=radar_id,
                action="kill_holders",
                success=False,
                message=f"kill_holders failed: {exc}",
            )

    def usb_reset(self, radar_id: str, *, manual_confirm: bool = False) -> ControlResult:
        if not manual_confirm:
            return ControlResult(
                radar_id=radar_id,
                action="usb_reset",
                success=False,
                message="manual_confirm=True is required for destructive actions",
                details={"manual_required": True},
            )

        try:
            config_port, data_port = self._resolve_ports(radar_id, allow_discovery=True)
            self._kill_switch.usb_reset_by_port(config_port)
            self._kill_switch.usb_reset_by_port(data_port)
            self._status_update(radar_id, connected=False, streaming=False, last_seen_ms=self._now_ms())
            return ControlResult(
                radar_id=radar_id,
                action="usb_reset",
                success=True,
                message="USB reset requested",
                details={"ports": [config_port, data_port]},
            )
        except Exception as exc:
            self._status_update(radar_id, fault_code=f"usb_reset_failed:{exc}")
            return ControlResult(
                radar_id=radar_id,
                action="usb_reset",
                success=False,
                message=f"usb_reset failed: {exc}",
            )
