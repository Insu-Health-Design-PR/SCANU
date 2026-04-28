#!/usr/bin/env python3
"""
Smoke-test all three sensors: TI mmWave (UART), thermal (V4L2), Infineon (SDK + CDC fallback).

Exit code 0 only if every enabled test passes.

Example:
  python3 layer1_radar/examples/test/test_connection.py
  python3 layer1_radar/examples/test/test_connection.py --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1
  python3 layer1_radar/examples/test/test_connection.py --skip-mmwave --thermal-device 0
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Repo root (``.../SCANU``): file is under ``software/layer1_radar/examples/test/``.
_repo_root = Path(__file__).resolve().parents[4]
_software_root = _repo_root / "software"
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_software_root))

from layer1_radar import SerialManager, ThermalCameraSource


def _mmwave_try_cli_pair(mgr: SerialManager, cli: str, data: str, timeout_s: float) -> tuple[bool, str]:
    """Open CLI+DATA, ask for `version`, return (ok, detail). Caller must disconnect after."""
    mgr.connect(cli, data)
    mgr.flush_data_port()
    rsp = mgr.send_cli_command("version", timeout_s=timeout_s)
    text = (rsp or "").strip()
    if not text:
        rsp2 = mgr.send_cli_command("sensorStop", timeout_s=min(timeout_s, 1.5))
        text = (rsp2 or "").strip()
    if not text:
        return False, f"CLI={cli} DATA={data}: no CLI text for `version` (or `sensorStop`)"

    time.sleep(0.2)
    extra = 0
    if mgr.data_port and mgr.data_port.in_waiting:
        extra = len(mgr.data_port.read(mgr.data_port.in_waiting))

    return True, f"CLI={cli} DATA={data}; idle_rx_bytes={extra}"


def test_mmwave(
    cli_port: str | None,
    data_port: str | None,
    verbose: bool,
) -> tuple[bool, str]:
    mgr = SerialManager()
    try:
        ports = mgr.find_radar_ports(
            verbose=verbose,
            config_port=cli_port,
            data_port=data_port,
        )
        a, b = ports.config_port, ports.data_port

        # CP2105 "Standard/Enhanced" labels often disagree with which side is mmwDemo CLI.
        orderings: list[tuple[str, str]] = [(a, b), (b, a)]

        # If user pinned both ports, try their order first, then one swap.
        if cli_port and data_port:
            u_cli, u_data = str(cli_port), str(data_port)
            orderings = [(u_cli, u_data), (u_data, u_cli)]

        errors: list[str] = []
        for cli, data in orderings:
            if cli == data:
                continue
            try:
                ok, detail = _mmwave_try_cli_pair(mgr, cli, data, timeout_s=2.5)
                if ok:
                    return True, detail
                errors.append(detail)
            except Exception as exc:
                errors.append(f"CLI={cli} DATA={data}: {exc}")
            finally:
                mgr.disconnect()

        return (
            False,
            " | ".join(errors)
            + " — close screen/minicom on these ports; if still dead, USB/power-cycle CP2105/radar.",
        )
    except Exception as exc:
        return False, str(exc)
    finally:
        mgr.disconnect()


def test_thermal(device: int) -> tuple[bool, str]:
    try:
        cam = ThermalCameraSource(
            device=device,
            width=640,
            height=480,
            fps=30,
        )
        try:
            frame = cam.read_raw()
            if frame is None:
                return False, f"/dev/video{device}: read() failed"
            shp = getattr(frame, "shape", "?")
            return True, f"/dev/video{device}: frame shape {shp}"
        finally:
            cam.close()
    except Exception as exc:
        return False, str(exc)


def _infineon_cdc_candidates() -> list[str]:
    out: list[str] = []
    by_id = Path("/dev/serial/by-id")
    if by_id.is_dir():
        for p in sorted(by_id.glob("usb-*")):
            name = p.name.lower()
            if "infineon" in name or "_ifx_" in name or "ifx_" in name:
                try:
                    resolved = str(p.resolve())
                except OSError:
                    resolved = str(p)
                if resolved not in out:
                    out.append(resolved)
    for acm in sorted(Path("/dev").glob("ttyACM*")):
        dev = f"/dev/{acm.name}"
        if dev not in out:
            out.append(dev)
    return out


def test_infineon(uuid: str | None) -> tuple[bool, str]:
    sdk_err: str | None = None
    try:
        from software.layer1_radar.infineon import IfxLtr11PresenceProvider

        prov = IfxLtr11PresenceProvider(uuid=uuid)
        try:
            presence_raw, motion_raw, _dist = prov.read_sample()
            meta = getattr(prov, "last_meta", None) or {}
            meta_short = {k: meta.get(k) for k in ("active", "motion", "avg_power") if k in meta}
            return (
                True,
                f"SDK: motion_energy={float(presence_raw):.6f} motion_flag={motion_raw} meta={meta_short}",
            )
        finally:
            prov.close()
    except Exception as exc:
        sdk_err = str(exc)

    from software.layer1_radar.infineon.ifx_cdc_transport import IfxCdcTransport

    for port in _infineon_cdc_candidates():
        try:
            t = IfxCdcTransport(port, baudrate=115200, timeout_s=0.4)
            try:
                rep = t.request_cmd4(0x00)
                if len(rep.payload) >= 1:
                    return (
                        True,
                        f"CDC serial ok on {port} (reply_len={len(rep.payload)}, crc_ok={rep.crc_ok}); "
                        f"SDK failed: {sdk_err}",
                    )
            finally:
                t.close()
        except Exception:
            continue

    return False, f"SDK: {sdk_err} | CDC: no responsive ttyACM / Infineon by-id port found"


def main() -> int:
    p = argparse.ArgumentParser(description="Test mmWave + thermal + Infineon connections")
    p.add_argument("--cli-port", default=None, help="mmWave CLI port (default: auto-detect)")
    p.add_argument("--data-port", default=None, help="mmWave DATA port (default: auto-detect)")
    p.add_argument("--thermal-device", type=int, default=0, help="V4L2 index (default /dev/video0)")
    p.add_argument("--infineon-uuid", default=None, help="Optional Infineon board UUID")
    p.add_argument("--skip-mmwave", action="store_true")
    p.add_argument("--skip-thermal", action="store_true")
    p.add_argument("--skip-infineon", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose mmWave port discovery")
    args = p.parse_args()

    results: list[tuple[str, bool, str]] = []

    print("Sensor connection test")
    print("=" * 60)

    if not args.skip_mmwave:
        ok, msg = test_mmwave(args.cli_port, args.data_port, verbose=args.verbose)
        results.append(("mmWave (TI UART)", ok, msg))
    else:
        results.append(("mmWave (TI UART)", True, "skipped"))

    if not args.skip_thermal:
        ok, msg = test_thermal(args.thermal_device)
        results.append(("thermal (V4L2)", ok, msg))
    else:
        results.append(("thermal (V4L2)", True, "skipped"))

    if not args.skip_infineon:
        ok, msg = test_infineon(args.infineon_uuid)
        results.append(("Infineon (SDK / CDC)", ok, msg))
    else:
        results.append(("Infineon (SDK / CDC)", True, "skipped"))

    all_ok = True
    for name, ok, msg in results:
        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {name}")
        print(f"       {msg}")
        if not ok:
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("All enabled tests passed.")
        return 0
    print("One or more tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
