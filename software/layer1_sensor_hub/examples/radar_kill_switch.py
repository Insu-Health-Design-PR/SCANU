#!/usr/bin/env python3
"""Kill switch / reset helper for stuck radar ports.

This script helps recover when the radar gets "stuck" because a previous process
still holds the serial device (e.g. after Ctrl+C).

What it can do:
- Optionally send `sensorStop` over the mmWave CLI port
- Optionally flush/clear UART buffers on CLI+DATA ports
- Detect processes holding given /dev/tty* nodes (via `fuser` or `lsof`)
- Terminate those processes (SIGTERM) and optionally force-kill (SIGKILL)

Examples:
  # Just show which processes hold the ports (safe)
  python3 software/layer1_radar/examples/radar_kill_switch.py --devices /dev/ttyUSB0 /dev/ttyUSB1

  # Try to stop the radar via CLI, then terminate holders
  python3 software/layer1_radar/examples/radar_kill_switch.py --cli-port /dev/ttyUSB0 --devices /dev/ttyUSB0 /dev/ttyUSB1 --kill

  # Force-kill if they don't exit
  python3 software/layer1_radar/examples/radar_kill_switch.py --devices /dev/ttyUSB0 /dev/ttyUSB1 --kill --force
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def _add_paths() -> None:
    repo_root = Path(__file__).resolve().parents[3]  # .../SCANU
    software_root = repo_root / "software"
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(software_root))


def _which(cmd: str) -> bool:
    from shutil import which

    return which(cmd) is not None


def try_sensor_stop(cli_port: str, baud: int = 115200, timeout_s: float = 1.0) -> None:
    """Best-effort `sensorStop` over mmWave CLI port."""

    try:
        import serial  # type: ignore
    except Exception as exc:
        print(f"[warn] pyserial not available, skipping sensorStop: {exc}")
        return

    try:
        ser = serial.Serial(cli_port, baudrate=baud, timeout=timeout_s)
    except Exception as exc:
        print(f"[warn] could not open CLI port {cli_port} for sensorStop: {exc}")
        return

    try:
        # Drain any prompt/noise, then send stop.
        try:
            if ser.in_waiting:
                ser.read(ser.in_waiting)
        except Exception:
            pass

        ser.write(b"sensorStop\r\n")
        time.sleep(0.2)
        try:
            data = ser.read(4096)
            if data:
                txt = data.decode("utf-8", errors="ignore").strip()
                if txt:
                    print(f"[info] CLI response: {txt[:2000]}")
        except Exception:
            pass
        print("[ok] sent sensorStop")
    finally:
        try:
            ser.close()
        except Exception:
            pass


def try_soft_uart_reset(
    cli_port: str,
    data_port: str,
    cli_baud: int = 115200,
    data_baud: int = 921600,
) -> None:
    """
    Best-effort state hygiene:
    - open CLI + DATA ports
    - clear UART input/output buffers
    - send `sensorStop` on CLI
    - flush any pending bytes on DATA

    This cannot fix kernel-level USB EIO, but it helps when the device is simply
    desynced/buffered between runs.
    """
    try:
        import serial  # type: ignore
    except Exception as exc:
        print(f"[warn] pyserial not available, skipping soft UART reset: {exc}")
        return

    try:
        cli = serial.Serial(cli_port, baudrate=cli_baud, timeout=0.5)
        data = serial.Serial(data_port, baudrate=data_baud, timeout=0.2)
    except Exception as exc:
        print(f"[warn] could not open CLI/DATA ports for soft reset: {exc}")
        return

    try:
        # Reset buffers (closest equivalent to clear_buffer + flush_data_port).
        try:
            cli.reset_input_buffer()
            cli.reset_output_buffer()
        except Exception:
            pass
        try:
            data.reset_input_buffer()
            data.reset_output_buffer()
        except Exception:
            pass

        # Wake prompt and stop sensor.
        try:
            cli.write(b"\r\n")
        except Exception:
            pass
        time.sleep(0.15)
        try:
            if cli.in_waiting:
                cli.read(cli.in_waiting)
        except Exception:
            pass

        try:
            cli.write(b"sensorStop\r\n")
            time.sleep(0.25)
            rsp = b""
            try:
                rsp = cli.read(4096)
            except Exception:
                rsp = b""
            if rsp:
                txt = rsp.decode("utf-8", errors="ignore").strip()
                if txt:
                    print(f"[info] sensorStop rsp: {txt[:500]}")
            print("[ok] soft reset: sent sensorStop")
        except Exception as exc:
            print(f"[warn] soft reset: failed sending sensorStop: {exc}")

        # Flush any pending bytes on data port.
        flushed = 0
        try:
            for _ in range(10):
                waiting = getattr(data, "in_waiting", 0) or 0
                if waiting <= 0:
                    break
                flushed += len(data.read(waiting))
                time.sleep(0.01)
        except Exception:
            pass
        if flushed:
            print(f"[ok] soft reset: flushed {flushed} bytes from DATA")
        else:
            print("[ok] soft reset: DATA flush 0 bytes")
    finally:
        try:
            cli.close()
        except Exception:
            pass
        try:
            data.close()
        except Exception:
            pass


def pids_holding_device(dev: str) -> list[int]:
    """Return PIDs that hold/open `dev` (best effort)."""

    dev = str(dev)
    pids: list[int] = []

    if _which("fuser"):
        # `fuser -a dev` prints: "/dev/ttyUSB0:  1234"
        try:
            out = subprocess.check_output(["fuser", "-a", dev], stderr=subprocess.STDOUT, text=True)
            tokens = out.replace(":", " ").split()
            for t in tokens:
                if t.isdigit():
                    pids.append(int(t))
            return sorted(set(pids))
        except subprocess.CalledProcessError as e:
            # fuser returns non-zero if no process is using it; that's fine.
            out = (e.output or "").strip()
            if out and "no process found" not in out.lower():
                print(f"[warn] fuser failed for {dev}: {out}")
        except Exception as exc:
            print(f"[warn] fuser error for {dev}: {exc}")

    if _which("lsof"):
        # `lsof -t dev` prints PIDs line-by-line
        try:
            out = subprocess.check_output(["lsof", "-t", dev], stderr=subprocess.DEVNULL, text=True)
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
            return sorted(set(pids))
        except subprocess.CalledProcessError:
            pass
        except Exception as exc:
            print(f"[warn] lsof error for {dev}: {exc}")

    return []


def terminate_pids(pids: list[int], force: bool) -> None:
    if not pids:
        return

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"[kill] SIGTERM pid={pid}")
        except PermissionError:
            print(f"[warn] no permission to SIGTERM pid={pid} (try sudo)")
        except ProcessLookupError:
            pass
        except Exception as exc:
            print(f"[warn] could not SIGTERM pid={pid}: {exc}")

    if not force:
        return

    time.sleep(0.6)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"[kill] SIGKILL pid={pid}")
        except PermissionError:
            print(f"[warn] no permission to SIGKILL pid={pid} (try sudo)")
        except ProcessLookupError:
            pass
        except Exception as exc:
            print(f"[warn] could not SIGKILL pid={pid}: {exc}")


def usb_reset_by_port(dev_path: str):
    """
    Reset USB device corresponding to /dev/ttyUSB*
    """
    try:
        import subprocess
        import os

        # Resolve sysfs path
        real_path = os.path.realpath(dev_path)
        tty_name = os.path.basename(real_path)

        sys_path = f"/sys/class/tty/{tty_name}/device"

        if not os.path.exists(sys_path):
            print(f"[warn] sysfs path not found for {dev_path}")
            return

        # Walk up to USB device root
        usb_path = os.path.realpath(sys_path)
        while usb_path != "/" and not os.path.exists(os.path.join(usb_path, "authorized")):
            usb_path = os.path.dirname(usb_path)

        if not os.path.exists(os.path.join(usb_path, "authorized")):
            print(f"[warn] could not find USB authorized node for {dev_path}")
            return

        print(f"[info] resetting USB device at {usb_path}")

        subprocess.run(["sudo", "sh", "-c", f"echo 0 > {usb_path}/authorized"])
        time.sleep(1)
        subprocess.run(["sudo", "sh", "-c", f"echo 1 > {usb_path}/authorized"])

        print("[ok] USB reset complete")

    except Exception as e:
        print(f"[error] USB reset failed: {e}")


def main() -> int:
    _add_paths()

    ap = argparse.ArgumentParser(description="Kill switch for stuck radar serial ports")
    ap.add_argument(
        "--devices",
        nargs="*",
        default=["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"],
        help="Device paths to check/kill holders for",
    )
    ap.add_argument("--cli-port", default=None, help="Optional mmWave CLI port to send sensorStop to")
    ap.add_argument("--cli-baud", type=int, default=115200)
    ap.add_argument("--data-port", default=None, help="Optional mmWave DATA port (for --soft-reset)")
    ap.add_argument("--usb-reset", action="store_true", help="Reset USB device (last resort)")
    ap.add_argument("--data-baud", type=int, default=921600)
    ap.add_argument(
        "--soft-reset",
        action="store_true",
        help="Open CLI+DATA, clear buffers, send sensorStop, flush data (best-effort).",
    )
    ap.add_argument("--kill", action="store_true", help="Actually terminate processes (default is dry-run)")
    ap.add_argument("--force", action="store_true", help="Also SIGKILL after SIGTERM")
    args = ap.parse_args()

    if args.soft_reset:
        if not args.cli_port or not args.data_port:
            print("[warn] --soft-reset requires --cli-port and --data-port")
        else:
            try_soft_uart_reset(
                cli_port=str(args.cli_port),
                data_port=str(args.data_port),
                cli_baud=int(args.cli_baud),
                data_baud=int(args.data_baud),
            )

    if args.cli_port:
        try_sensor_stop(args.cli_port, baud=args.cli_baud)

    if args.usb_reset:
        for dev in args.devices:
            if os.path.exists(dev):
                usb_reset_by_port(dev)

    any_found = False
    dev_to_pids: dict[str, list[int]] = {}
    for dev in args.devices:
        pids = pids_holding_device(dev)
        dev_to_pids[dev] = pids
        if pids:
            any_found = True

    for dev, pids in dev_to_pids.items():
        if pids:
            print(f"[hold] {dev}: pids={pids}")
        else:
            print(f"[hold] {dev}: (none)")

    if not any_found:
        print("[ok] no holders found")
        return 0

    if not args.kill:
        print("[dry-run] re-run with --kill (and optionally --force) to terminate holders")
        return 0

    all_pids: list[int] = sorted({pid for pids in dev_to_pids.values() for pid in pids})
    terminate_pids(all_pids, force=bool(args.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

