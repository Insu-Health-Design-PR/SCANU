#!/usr/bin/env python3
"""
DCA1000EVM + mmWave host-side sanity check (Linux).

TI defaults (FPGA registers / typical setup, see SPRUIJ4 DCA1000EVM User's Guide):
  - DCA1000 FPGA IP:  192.168.33.180
  - Host (your PC) IP: 192.168.33.30
  - Raw LVDS data is streamed over Ethernet (UDP); configuration uses DCA1000 tools.

USB on the capture card:
  - J1 "Radar FTDI": routes UART/SPI/I2C toward the xWR EVM through the DCA (used with
    mmWave Studio / RADAR Studio for some setups).
  - J4 "FPGA JTAG": FPGA programming (FTDI).

Important for this SCANU repo:
  - live_capture / capture_frames use the mmWave **Data UART TLV** path (e.g. CP2105
    on modular USB), which is separate from **DCA raw LVDS→Ethernet** capture.
  - If the radar is only cabled LVDS→DCA and you use **J1** to the host, your **CLI
    serial device may be the DCA J1 FTDI port**, not /dev/ttyUSB from the AOP module.

Usage:
  python3 layer1_radar/examples/test/dca_check.py
  python3 layer1_radar/examples/test/dca_check.py --ping
"""

from __future__ import annotations

import argparse
import re
import shutil
import socket
import subprocess
import sys


# TI default register values (unless EEPROM / SW2 overrides)
DCA_FPGA_IP = "192.168.33.180"
HOST_EXPECTED_IP = "192.168.33.30"


def _run(cmd: list[str], timeout: float = 8.0) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()
    except FileNotFoundError:
        return 127, f"(not found: {cmd[0]})"
    except subprocess.TimeoutExpired:
        return 124, "(timeout)"


def check_lsusb() -> None:
    print("\n=== USB (lsusb) — look for FTDI (0403) on DCA J1/J4, CP2105 (10c4) on radar ===\n")
    if not shutil.which("lsusb"):
        print("  lsusb not installed; skip.")
        return
    code, out = _run(["lsusb"])
    if code != 0:
        print(out)
        return
    lines = out.splitlines()
    for line in lines:
        lower = line.lower()
        # Avoid matching "ti" inside "Foundation" etc.
        if re.search(r"\bID\s+0403:", line, re.I):
            print(f"  {line}")
            continue
        if re.search(r"\bID\s+10c4:", line, re.I):
            print(f"  {line}")
            continue
        if re.search(r"\bID\s+0451:", line, re.I):
            print(f"  {line}")
            continue
        if "ftdi" in lower or "silicon labs" in lower or "texas instruments" in lower:
            print(f"  {line}")
    if not lines:
        print("  (no output)")


def check_ipv4_addrs() -> list[tuple[str, str]]:
    """Return [(iface, cidr), ...] for global IPv4 addresses."""
    print("\n=== Host IPv4 (same machine) — need 192.168.33.x for default DCA link ===\n")
    addrs: list[tuple[str, str]] = []
    if shutil.which("ip"):
        code, out = _run(["ip", "-4", "addr", "show", "scope", "global"])
        if code == 0 and out:
            iface = "?"
            for line in out.splitlines():
                m = re.match(r"^\d+:\s+(\S+):", line)
                if m:
                    iface = m.group(1).rstrip(":")
                m2 = re.search(r"inet\s+(\S+)", line)
                if m2:
                    addrs.append((iface, m2.group(1)))
    if not addrs:
        print("  (could not parse; try: ip -4 addr show scope global)")
        return addrs
    on_seg = False
    for iface, cidr in addrs:
        mark = ""
        if cidr.startswith("192.168.33."):
            mark = "  <-- same /24 as default DCA pairing"
            on_seg = True
        print(f"  {iface}: {cidr}{mark}")
    if not on_seg:
        print(
            f"\n  Hint: set a static IP on the NIC that goes to the DCA, e.g. "
            f"{HOST_EXPECTED_IP}/24 (netmask 255.255.255.0), gateway optional."
        )
    return addrs


def ping_ip(ip: str) -> bool:
    ping = shutil.which("ping")
    if not ping:
        print("  ping not found")
        return False
    # -c count, -W deadline seconds (iputils)
    code, out = _run([ping, "-c", "1", "-W", "2", ip], timeout=5.0)
    ok = code == 0
    print(f"  ping {ip}: {'OK' if ok else 'failed'}")
    if out and not ok:
        for line in out.splitlines()[:4]:
            print(f"    {line}")
    return ok


def tcp_probe(ip: str, port: int, timeout: float = 1.0) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
        return True
    except OSError:
        return False


def check_serial_ports() -> None:
    print("\n=== Serial ports (pyserial) — pick CLI/DATA for live_capture ===\n")
    try:
        from serial.tools import list_ports
    except ImportError:
        print("  pyserial not installed.")
        return
    ports = list(list_ports.comports())
    if not ports:
        print("  (none)")
        return
    for p in ports:
        vidpid = ""
        if p.vid is not None and p.pid is not None:
            vidpid = f" VID:PID={p.vid:04x}:{p.pid:04x}"
        print(f"  {p.device}: {p.description}{vidpid}")
        if p.manufacturer:
            print(f"      mfg={p.manufacturer}")


def main() -> int:
    parser = argparse.ArgumentParser(description="DCA1000 / mmWave USB+Ethernet quick check")
    parser.add_argument(
        "--ping",
        action="store_true",
        help=f"Run ping to DCA default FPGA IP {DCA_FPGA_IP}",
    )
    parser.add_argument(
        "--tcp-probe",
        action="store_true",
        help="Try TCP connect to FPGA IP on ports 7 and 80 (often closed; informational)",
    )
    args = parser.parse_args()

    print(
        "DCA1000EVM quick check\n"
        "----------------------\n"
        "Defaults from TI doc: FPGA IP = {}, host IP = {} (/24).\n"
        "Raw ADC path: LVDS (radar↔DCA) → Ethernet UDP to host.\n"
        "This script does not talk the DCA1000 UDP command protocol; use mmWave Studio / "
        "DCA1000 capture tools for that.".format(DCA_FPGA_IP, HOST_EXPECTED_IP)
    )

    check_lsusb()
    check_ipv4_addrs()
    check_serial_ports()

    if args.ping:
        print(f"\n=== Ping DCA FPGA ({DCA_FPGA_IP}) ===\n")
        ping_ip(DCA_FPGA_IP)

    if args.tcp_probe:
        print(f"\n=== TCP probe (usually idle on DCA) ===\n")
        for port in (7, 80, 443):
            open_ = tcp_probe(DCA_FPGA_IP, port, timeout=0.8)
            print(f"  {DCA_FPGA_IP}:{port} -> {'open' if open_ else 'closed/refused'}")

    print(
        "\n=== How this relates to SCANU Python examples ===\n"
        "  • capture_frames / live_capture need mmWave **TLV on the Data UART** "
        "(921600) plus **CLI** (115200).\n"
        "  • That is usually the **dual CP2105** on the radar USB, not the DCA Ethernet stream.\n"
        "  • If you only connect **DCA J1 FTDI** to the PC for radar access, use the **ttyUSB/ttyACM**\n"
        "    device that appears for **J1** in the list above as your CLI (and confirm Data path).\n"
        "  • DCA raw capture requires **mmWave Studio** (or equivalent) + correct Ethernet + LVDS.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
