"""Diagnostic tool for DCA1000EVM connectivity and radar setup.

Run:
    python3 -m layer1_sensor_hub.mmwave_dca.diagnose_dca1000

Or with verbose output:
    python3 -m layer1_sensor_hub.mmwave_dca.diagnose_dca1000 --verbose
"""

from __future__ import annotations

import argparse
import logging
import socket
import struct
import subprocess
import sys
import time

import serial
import serial.tools.list_ports

from .dca1000_control import (
    Dca1000Command,
    Dca1000NativeClient,
    HEADER,
    FOOTER,
    default_fpga_payload,
    load_dca_config,
    network_from_config,
)
from .dca1000_udp import Dca1000NetworkConfig
from .radar_cli import RadarCliConfig, send_cli_commands

# Import _find_cli_port from radar_cli (added there for auto-detection)
try:
    from .radar_cli import _find_cli_port
except ImportError:
    # Fallback: simple port enumeration
    def _find_cli_port() -> str | None:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            port = p.device
            try:
                import serial
                with serial.Serial(port, 115200, timeout=1.0) as ser:
                    ser.reset_input_buffer()
                    ser.write(b"version\r\n")
                    import time
                    time.sleep(0.8)
                    waiting = ser.in_waiting
                    if waiting:
                        resp = ser.read(waiting).decode("utf-8", errors="ignore")
                        if "xWR68" in resp or "IWR68" in resp or "mmWave" in resp or "mmwDemo" in resp:
                            return port
            except Exception:
                continue
        return None

logger = logging.getLogger(__name__)


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "OK" if ok else "FAIL"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


def diagnose(args: argparse.Namespace) -> int:
    errors = 0

    print("=" * 60)
    print("SCAN-U DCA1000 / mmWave Diagnostic")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Python environment
    # ------------------------------------------------------------------
    print("\n--- 1. Python Environment ---")
    _check("Python 3.8+", sys.version_info >= (3, 8), sys.version)

    # ------------------------------------------------------------------
    # 2. Serial ports
    # ------------------------------------------------------------------
    print("\n--- 2. Serial Ports ---")
    ports = list(serial.tools.list_ports.comports())
    _check("Serial ports detected", len(ports) > 0, f"found {len(ports)}")
    for p in ports:
        print(f"       {p.device}: {p.description}")

    # ------------------------------------------------------------------
    # 3. Radar CLI port
    # ------------------------------------------------------------------
    print("\n--- 3. Radar CLI Port ---")
    cli_port = args.cli_port or _find_cli_port()
    ok = _check("CLI port found", bool(cli_port), cli_port)
    if ok:
        try:
            cfg = RadarCliConfig(port=cli_port, timeout_s=2.0)
            resp = send_cli_commands(cfg, ["sensorStop"])
            has_done = any("Done" in r for r in resp)
            _check("Radar responds on CLI", has_done, f"last resp: {resp[-1][:80]!r}")
        except Exception as e:
            _check("Radar CLI communication", False, str(e))
            errors += 1

    # ------------------------------------------------------------------
    # 4. Radar data port
    # ------------------------------------------------------------------
    print("\n--- 4. Radar Data Port ---")
    data_port = args.data_port or "/dev/ttyUSB1"
    try:
        ser = serial.Serial(data_port, 921600, timeout=1.0)
        time.sleep(0.5)
        n = ser.in_waiting
        if n > 0:
            data = ser.read(n)
            magic = bytes([0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x08, 0x07])
            has_magic = magic in data
            _check("Data port has TLV frames", has_magic, f"{n} bytes available")
        else:
            _check("Data port opened", True, "0 bytes waiting (radar may be stopped)")
        ser.close()
    except Exception as e:
        _check("Data port access", False, str(e))
        errors += 1

    # ------------------------------------------------------------------
    # 5. Ethernet interface
    # ------------------------------------------------------------------
    print("\n--- 5. Ethernet (DCA1000 Network) ---")
    pc_ip = args.pc_ip or "192.168.33.30"
    dca_ip = args.dca_ip or "192.168.33.180"
    try:
        import subprocess

        r = subprocess.run(
            ["ip", "-4", "addr", "show", "dev", args.eth_dev or "eth0"],
            capture_output=True, text=True, timeout=5,
        )
        has_ip = pc_ip in r.stdout
        _check(f"Jetson IP {pc_ip} configured", has_ip, r.stdout[:200])
    except Exception as e:
        _check("Ethernet check", False, str(e))
        errors += 1

    # Check ARP for DCA1000
    try:
        import subprocess
        r = subprocess.run(
            ["ip", "neigh", "show", dca_ip],
            capture_output=True, text=True, timeout=5,
        )
        in_arp = dca_ip in r.stdout
        _check(f"DCA1000 ({dca_ip}) in ARP cache", in_arp, r.stdout.strip() or "not found")
    except Exception as e:
        _check("ARP check", False, str(e))

    # ------------------------------------------------------------------
    # 6. DCA1000 UDP control
    # ------------------------------------------------------------------
    print("\n--- 6. DCA1000 UDP Command ---")
    net = Dca1000NetworkConfig(pc_ip=pc_ip, dca_ip=dca_ip)
    client = Dca1000NativeClient(net, timeout_s=args.dca_timeout, retries=args.dca_retries)

    for cmd_name in ["connect", "reset_fpga", "version"]:
        result = client.send_command(cmd_name, retries=0)
        detail = f"resp={result.response_hex or '<none>'}  ({result.elapsed_s:.2f}s)"
        if result.ok:
            _check(f"DCA1000 {cmd_name}", True, detail)
        else:
            _check(f"DCA1000 {cmd_name}", False, detail)
            errors += 1

    # ------------------------------------------------------------------
    # 7. DCA1000 data port listening
    # ------------------------------------------------------------------
    print("\n--- 7. DCA1000 Data Port Listen ---")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(args.listen_s)
            sock.bind((pc_ip, net.data_port))
            print(f"  Listening on {pc_ip}:{net.data_port} for {args.listen_s}s ...")
            try:
                data, addr = sock.recvfrom(4096 + 64)
                _check("DCA1000 data received", True, f"from {addr}, {len(data)} bytes")
            except socket.timeout:
                _check("DCA1000 data received", False, f"timeout after {args.listen_s}s")
                errors += 1
    except Exception as e:
        _check("DCA1000 data port bind", False, str(e))
        errors += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    if errors == 0:
        print("All checks passed. DCA1000 and radar are ready.")
    else:
        print(f"{errors} check(s) FAILED. See details above.")
    print("=" * 60)
    return 0 if errors == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DCA1000 / mmWave radar diagnostic")
    parser.add_argument("--cli-port", default="", help="Radar CLI port (auto-detect if empty)")
    parser.add_argument("--data-port", default="", help="Radar data port")
    parser.add_argument("--pc-ip", default="192.168.33.30")
    parser.add_argument("--dca-ip", default="192.168.33.180")
    parser.add_argument("--eth-dev", default="eth0", help="Ethernet device for DCA1000")
    parser.add_argument("--dca-timeout", type=float, default=2.0)
    parser.add_argument("--dca-retries", type=int, default=2)
    parser.add_argument("--listen-s", type=float, default=5.0, help="Seconds to listen on data port")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    return diagnose(args)


if __name__ == "__main__":
    raise SystemExit(main())
