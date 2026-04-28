"""
Simple utility to list available serial ports.

Use this to verify your radar is detected before running capture.

Usage:
    python list_ports.py
    python list_ports.py --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from layer1_radar import SerialManager


def main():
    parser = argparse.ArgumentParser(description="List serial ports and detect radar ports")
    parser.add_argument('--cli-port', type=str, default=None,
                        help='Explicit CLI/config port (e.g. /dev/ttyUSB0 or COM3)')
    parser.add_argument('--data-port', type=str, default=None,
                        help='Explicit data port (e.g. /dev/ttyUSB1 or COM4)')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("Serial Port Scanner")
    print("="*60)
    
    ports = SerialManager.list_all_ports()
    
    if not ports:
        print("\nNo serial ports found!")
        print("\nMake sure:")
        print("  - Radar is connected via USB")
        print("  - USB drivers are installed")
        return
    
    print(f"\nFound {len(ports)} serial port(s):\n")
    
    for port in ports:
        print(f"  Device: {port['device']}")
        print(f"    Description: {port['description']}")
        if port['manufacturer']:
            print(f"    Manufacturer: {port['manufacturer']}")
        if port['vid'] and port['pid']:
            print(f"    VID:PID: {port['vid']:04X}:{port['pid']:04X}")
        print()
    
    # Try to identify radar
    print("-"*60)
    print("Attempting to identify IWR6843 radar...")
    
    mgr = SerialManager()
    try:
        radar_ports = mgr.find_radar_ports(
            verbose=False,
            config_port=args.cli_port,
            data_port=args.data_port,
        )
        print(f"\n✓ Radar found!")
        print(f"  Config port: {radar_ports.config_port}")
        print(f"  Data port: {radar_ports.data_port}")
    except RuntimeError as e:
        print(f"\n✗ Radar not detected")
        print(f"  {e}")


if __name__ == '__main__':
    main()
