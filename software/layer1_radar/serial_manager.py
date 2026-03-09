"""
Serial port management for IWR6843 radar.

Handles discovery and connection to the radar's two UART ports:
- Config port: Send CLI commands (115200 baud)
- Data port: Receive TLV frames (921600 baud)
"""

import serial
import serial.tools.list_ports
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

from .radar_constants import SerialConfig

logger = logging.getLogger(__name__)


@dataclass
class RadarPorts:
    """Container for radar port information."""
    config_port: str
    data_port: str
    description: str = ""


class SerialManager:
    """
    Discovers and manages serial connections to IWR6843 radar.
    
    Usage:
        mgr = SerialManager()
        ports = mgr.find_radar_ports()
        mgr.connect(ports.config_port, ports.data_port)
        # ... use mgr.config_port and mgr.data_port ...
        mgr.disconnect()
    """
    
    def __init__(self):
        self.config_port: Optional[serial.Serial] = None
        self.data_port: Optional[serial.Serial] = None
        self._connected = False
    
    @staticmethod
    def list_all_ports() -> List[dict]:
        """List all available serial ports with details."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'vid': port.vid,
                'pid': port.pid,
                'manufacturer': port.manufacturer,
            })
        return ports
    
    def find_radar_ports(self, verbose: bool = True) -> RadarPorts:
        """
        Auto-discover IWR6843 radar ports.
        
        The radar appears as two consecutive COM ports:
        - First port: Configuration/CLI (User UART)
        - Second port: Data output (Data UART)
        
        Args:
            verbose: Print discovered ports
            
        Returns:
            RadarPorts with config and data port names
            
        Raises:
            RuntimeError: If radar ports cannot be found
        """
        all_ports = list(serial.tools.list_ports.comports())
        
        if verbose:
            logger.info(f"Found {len(all_ports)} serial ports:")
            for p in all_ports:
                logger.info(f"  {p.device}: {p.description}")
        
        # Look for XDS110 debug probe (used by TI EVMs)
        # Or direct IWR6843 identification
        radar_ports = []
        for port in all_ports:
            desc_lower = port.description.lower()
            if any(x in desc_lower for x in ['xds110', 'iwr6843', 'mmwave', 'ti']):
                radar_ports.append(port)
        
        # Also check by VID/PID (Texas Instruments)
        # TI VID = 0x0451
        if len(radar_ports) < 2:
            for port in all_ports:
                if port.vid == 0x0451 and port not in radar_ports:
                    radar_ports.append(port)
        
        if len(radar_ports) < 2:
            available = [f"{p.device} ({p.description})" for p in all_ports]
            raise RuntimeError(
                f"Could not find radar ports. Need 2 XDS110/IWR6843 ports.\n"
                f"Available ports: {available}\n"
                f"Make sure the radar is connected via USB."
            )
        
        # Sort by port name/number to get consistent ordering
        radar_ports.sort(key=lambda p: p.device)
        
        # First port is config, second is data
        config_port = radar_ports[0].device
        data_port = radar_ports[1].device
        
        logger.info(f"Radar found - Config: {config_port}, Data: {data_port}")
        
        return RadarPorts(
            config_port=config_port,
            data_port=data_port,
            description=radar_ports[0].description
        )
    
    def connect(
        self, 
        config_port: str, 
        data_port: str,
        config_baud: int = SerialConfig.CONFIG_BAUD,
        data_baud: int = SerialConfig.DATA_BAUD
    ) -> None:
        """
        Open connections to radar ports.
        
        Args:
            config_port: Path to config port (e.g., 'COM3' or '/dev/ttyACM0')
            data_port: Path to data port (e.g., 'COM4' or '/dev/ttyACM1')
            config_baud: Baud rate for config port (default 115200)
            data_baud: Baud rate for data port (default 921600)
        """
        if self._connected:
            logger.warning("Already connected, disconnecting first")
            self.disconnect()
        
        try:
            self.config_port = serial.Serial(
                port=config_port,
                baudrate=config_baud,
                timeout=SerialConfig.CONFIG_TIMEOUT,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            logger.info(f"Config port opened: {config_port} @ {config_baud}")
            
            self.data_port = serial.Serial(
                port=data_port,
                baudrate=data_baud,
                timeout=SerialConfig.DATA_TIMEOUT,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            logger.info(f"Data port opened: {data_port} @ {data_baud}")
            
            self._connected = True
            
        except serial.SerialException as e:
            self.disconnect()
            raise RuntimeError(f"Failed to open serial ports: {e}")
    
    def disconnect(self) -> None:
        """Close all serial connections."""
        if self.config_port and self.config_port.is_open:
            try:
                self.config_port.close()
                logger.info("Config port closed")
            except Exception as e:
                logger.warning(f"Error closing config port: {e}")
        
        if self.data_port and self.data_port.is_open:
            try:
                self.data_port.close()
                logger.info("Data port closed")
            except Exception as e:
                logger.warning(f"Error closing data port: {e}")
        
        self.config_port = None
        self.data_port = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if both ports are connected and open."""
        return (
            self._connected and
            self.config_port is not None and
            self.config_port.is_open and
            self.data_port is not None and
            self.data_port.is_open
        )
    
    def flush_data_port(self) -> int:
        """
        Clear any pending data in the data port buffer.
        
        Returns:
            Number of bytes flushed
        """
        if not self.data_port or not self.data_port.is_open:
            return 0
        
        flushed = 0
        while self.data_port.in_waiting > 0:
            flushed += len(self.data_port.read(self.data_port.in_waiting))
        
        if flushed > 0:
            logger.debug(f"Flushed {flushed} bytes from data port")
        
        return flushed
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.disconnect()
        return False
