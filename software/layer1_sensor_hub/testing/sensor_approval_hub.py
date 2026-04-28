#!/usr/bin/env python3
"""Approve sensor connectivity for mmWave, thermal, and Infineon."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub.infeneon import IfxCdcTransport, IfxLtr11PresenceProvider
from software.layer1_sensor_hub.mmwave import SerialManager


def test_mmwave(cli_port: str | None, data_port: str | None) -> tuple[bool, str]:
    mgr = SerialManager()
    try:
        ports = mgr.find_radar_ports(verbose=False, config_port=cli_port, data_port=data_port)
        # Try both directions because some bridges label ports inconsistently.
        candidates = [(ports.config_port, ports.data_port), (ports.data_port, ports.config_port)]
        errors: list[str] = []

        for cli, data in candidates:
            try:
                mgr.connect(cli, data)
                text = mgr.send_cli_command("version", timeout_s=2.0).strip()
                if not text:
                    text = mgr.send_cli_command("sensorStop", timeout_s=1.5).strip()
                if text:
                    return True, f"CLI={cli} DATA={data} response_ok"
                errors.append(f"CLI={cli} DATA={data}: empty response")
            except Exception as exc:
                errors.append(f"CLI={cli} DATA={data}: {exc}")
            finally:
                mgr.disconnect()
        return False, " | ".join(errors)
    except Exception as exc:
        return False, str(exc)
    finally:
        mgr.disconnect()


def test_thermal(device: int) -> tuple[bool, str]:
    from software.layer1_sensor_hub.thermal import ThermalCameraSource

    try:
        src = ThermalCameraSource(device=device, width=640, height=480, fps=30)
        try:
            frame = src.read_raw()
            if frame is None:
                return False, f"/dev/video{device}: read failed"
            return True, f"/dev/video{device}: frame shape={getattr(frame, 'shape', None)}"
        finally:
            src.close()
    except Exception as exc:
        return False, str(exc)


def _cdc_candidates() -> list[str]:
    out: list[str] = []
    by_id = Path("/dev/serial/by-id")
    if by_id.is_dir():
        for p in sorted(by_id.glob("usb-*")):
            name = p.name.lower()
            if "infineon" in name or "ifx" in name:
                try:
                    out.append(str(p.resolve()))
                except OSError:
                    out.append(str(p))
    for acm in sorted(Path("/dev").glob("ttyACM*")):
        out.append(str(acm))
    dedup: list[str] = []
    for d in out:
        if d not in dedup:
            dedup.append(d)
    return dedup


def test_infineon(uuid: str | None) -> tuple[bool, str]:
    sdk_error: str | None = None
    try:
        provider = IfxLtr11PresenceProvider(uuid=uuid)
        try:
            p_raw, motion_raw, _ = provider.read_sample()
            return True, f"SDK ok: presence_raw={float(p_raw):.6f} motion_raw={float(motion_raw):.1f}"
        finally:
            provider.close()
    except Exception as exc:
        sdk_error = str(exc)

    for port in _cdc_candidates():
        try:
            t = IfxCdcTransport(port, baudrate=115200, timeout_s=0.4)
            try:
                rep = t.request_cmd4(0x00)
                if len(rep.payload) >= 1:
                    return True, f"CDC ok on {port} (reply_len={len(rep.payload)}, crc_ok={rep.crc_ok}); sdk={sdk_error}"
            finally:
                t.close()
        except Exception:
            continue
    return False, f"SDK failed: {sdk_error}; CDC probe failed"


def main() -> int:
    p = argparse.ArgumentParser(description="Approve connectivity for all layer1_sensor_hub sensors")
    p.add_argument("--cli-port", default=None)
    p.add_argument("--data-port", default=None)
    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument("--ifx-uuid", default=None)
    p.add_argument("--skip-mmwave", action="store_true")
    p.add_argument("--skip-thermal", action="store_true")
    p.add_argument("--skip-infineon", action="store_true")
    args = p.parse_args()

    checks: list[tuple[str, bool, str]] = []
    t0 = time.time()

    if args.skip_mmwave:
        checks.append(("mmWave", True, "skipped"))
    else:
        checks.append(("mmWave", *test_mmwave(args.cli_port, args.data_port)))

    if args.skip_thermal:
        checks.append(("Thermal", True, "skipped"))
    else:
        checks.append(("Thermal", *test_thermal(args.thermal_device)))

    if args.skip_infineon:
        checks.append(("Infineon", True, "skipped"))
    else:
        checks.append(("Infineon", *test_infineon(args.ifx_uuid)))

    all_ok = True
    print("\nSensor approval results")
    print("=" * 60)
    for name, ok, detail in checks:
        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {name}: {detail}")
        all_ok = all_ok and ok

    print("=" * 60)
    print(f"Elapsed: {time.time() - t0:.2f}s")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
