"""
Example: Capture and parse radar frames.

This script demonstrates the complete Layer 1 pipeline:
1. Find and connect to radar
2. Send configuration
3. Capture frames
4. Parse TLV data
5. Display results

Usage:
    python capture_frames.py [--frames N] [--output FILE]
"""

import argparse
import logging
import json
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from layer1_radar import (
    SerialManager,
    RadarConfigurator,
    UARTSource,
    TLVParser,
    DEFAULT_CONFIG,
)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    parser = argparse.ArgumentParser(description='Capture radar frames')
    parser.add_argument('--frames', '-n', type=int, default=100,
                        help='Number of frames to capture (default: 100)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file for captured data (JSON)')
    parser.add_argument('--config', '-c', type=str, default=None,
                        help='Path to radar config file')
    parser.add_argument('--cli-port', type=str, default=None,
                        help='Explicit CLI/config port (e.g. /dev/ttyUSB0 or COM3)')
    parser.add_argument('--data-port', type=str, default=None,
                        help='Explicit data port (e.g. /dev/ttyUSB1 or COM4)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--list-ports', action='store_true',
                        help='List available serial ports and exit')
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # List ports mode
    if args.list_ports:
        print("\nAvailable serial ports:")
        for port in SerialManager.list_all_ports():
            print(f"  {port['device']}: {port['description']}")
        return
    
    # Main capture flow
    serial_mgr = SerialManager()
    
    try:
        # 1. Find radar ports
        print("\n" + "="*60)
        print("LAYER 1: Radar Control & Data Acquisition")
        print("="*60)
        
        print("\n[1/5] Searching for radar...")
        try:
            ports = serial_mgr.find_radar_ports(
                config_port=args.cli_port,
                data_port=args.data_port,
            )
            print(f"      Found: {ports.description}")
            print(f"      Config port: {ports.config_port}")
            print(f"      Data port: {ports.data_port}")
        except RuntimeError as e:
            print(f"\nERROR: {e}")
            print("\nTroubleshooting:")
            print("  1. Make sure the radar is connected via USB")
            print("  2. Install TI XDS110 drivers if on Windows")
            print("  3. Check USB cable is data-capable")
            print("  4. If using a UART bridge, pass --cli-port and --data-port")
            print("\nAvailable ports:")
            for port in SerialManager.list_all_ports():
                print(f"    {port['device']}: {port['description']}")
            return
        
        # 2. Connect to ports
        print("\n[2/5] Connecting to serial ports...")
        serial_mgr.connect(ports.config_port, ports.data_port)
        print("      Connected!")
        
        # 3. Configure radar
        
        # 3a. Configure minimal first-start commands
        print("\n[3/5] Configuring radar (first start)...")
        result = configurator.configure(first_start_config)
        if not result.success:
            print(f"\nConfiguration FAILED with {len(result.errors)} errors:")
            for error in result.errors:
                print(f"  - {error}")
            return

        # 3b. Apply optional post-start commands
        print("\n      Applying post-start configuration...")
        result = configurator.configure(post_start_config)
        if not result.success:
            print(f"\nPost-start configuration had {len(result.errors)} errors:")
            for error in result.errors:
                print(f"  - {error}")
        
        if args.config:
            print(f"      Loading config from: {args.config}")
            result = configurator.configure_from_file(Path(args.config))
        else:
            print("      Using default configuration")
            result = configurator.configure()
        
        if not result.success:
            print(f"\nConfiguration FAILED with {len(result.errors)} errors:")
            for error in result.errors:
                print(f"  - {error}")
            return
        
        print(f"      Sent {result.commands_sent} commands")
        print("      Radar configured and running!")
        
        # 4. Capture frames
        print(f"\n[4/5] Capturing {args.frames} frames...")
        print("      Press Ctrl+C to stop early\n")
        
        uart_source = UARTSource(serial_mgr)
        tlv_parser = TLVParser()
        
        # Clear any stale data
        serial_mgr.flush_data_port()
        uart_source.clear_buffer()
        
        frames_data = []
        start_time = time.time()
        
        try:
            for i, raw_frame in enumerate(uart_source.stream_frames(max_frames=args.frames)):
                # Parse frame
                parsed = tlv_parser.parse(raw_frame)
                
                # Display progress
                elapsed = time.time() - start_time
                fps = (i + 1) / elapsed if elapsed > 0 else 0
                
                print(f"\r      Frame {i+1:4d}/{args.frames}: "
                      f"{len(parsed.points):2d} objects, "
                      f"{len(raw_frame):5d} bytes, "
                      f"{fps:.1f} FPS", end='')
                
                # Store frame data if output requested
                if args.output:
                    frame_dict = {
                        'frame_number': parsed.frame_number,
                        'timestamp': parsed.timestamp_cycles,
                        'num_points': len(parsed.points),
                        'points': [p.to_dict() for p in parsed.points],
                        'has_range_profile': parsed.range_profile is not None,
                    }
                    if parsed.range_profile is not None:
                        frame_dict['range_profile'] = parsed.range_profile.tolist()
                    frames_data.append(frame_dict)
        
        except KeyboardInterrupt:
            print("\n\n      Capture interrupted by user")
        
        # Stats
        elapsed = time.time() - start_time
        source_stats = uart_source.get_stats()
        parser_stats = tlv_parser.get_stats()
        
        print(f"\n\n      Capture complete!")
        print(f"      Total frames: {source_stats['frames_read']}")
        print(f"      Total bytes: {source_stats['bytes_read']:,}")
        print(f"      Duration: {elapsed:.1f}s")
        print(f"      Average FPS: {source_stats['frames_read']/elapsed:.1f}")
        
        # 5. Save output
        if args.output and frames_data:
            print(f"\n[5/5] Saving data to {args.output}...")
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump({
                    'capture_info': {
                        'frames': len(frames_data),
                        'duration_seconds': elapsed,
                        'fps': len(frames_data) / elapsed,
                    },
                    'frames': frames_data
                }, f, indent=2)
            
            print(f"      Saved {len(frames_data)} frames")
        
        # Stop radar
        print("\n[Done] Stopping radar...")
        configurator.stop()
        
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\nERROR: {e}")
        
    finally:
        serial_mgr.disconnect()
        print("\nSerial ports closed.")


if __name__ == '__main__':
    main()
