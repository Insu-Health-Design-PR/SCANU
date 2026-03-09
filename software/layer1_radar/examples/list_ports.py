"""
Simple utility to list available serial ports.

Use this to verify your radar is detected before running capture.

Usage:
    python list_ports.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from layer1_radar import SerialManager


def main():
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
        radar_ports = mgr.find_radar_ports(verbose=False)
        print(f"\n✓ Radar found!")
        print(f"  Config port: {radar_ports.config_port}")
        print(f"  Data port: {radar_ports.data_port}")
    except RuntimeError as e:
        print(f"\n✗ Radar not detected")
        print(f"  {e}")


if __name__ == '__main__':
    main()
