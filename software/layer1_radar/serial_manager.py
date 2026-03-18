"""
Serial port management for IWR6843 radar.

Handles discovery and connection to the radar's two UART ports:
- Config port: Send CLI commands (115200 baud)
- Data port: Receive TLV frames (921600 baud)
"""

import serial
import serial.tools.list_ports
import logging
from typing import Optional, Tuple, List, Iterable
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
    def _sort_port_devices(devices: Iterable[str]) -> List[str]:
        """
        Sort port device names in a human-friendly way.

        Examples:
        - Linux: /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM0 ...
        - Windows: COM3, COM12 ...
        """
        def key(d: str):
            s = str(d)
            # Windows COM ports
            if s.upper().startswith("COM"):
                try:
                    return (0, int(s[3:]))
                except Exception:
                    return (0, s)
            # Linux ttyUSB / ttyACM
            for prefix in ("/dev/ttyUSB", "/dev/ttyACM"):
                if s.startswith(prefix):
                    try:
                        return (1, prefix, int(s[len(prefix):]))
                    except Exception:
                        return (1, prefix, s)
            return (2, s)

        return sorted([str(d) for d in devices], key=key)

    @staticmethod
    def _pick_standard_enhanced_pair(all_ports: List[serial.tools.list_ports.ListPortInfo]) -> Optional[RadarPorts]:
        """
        Heuristic for USB-UART bridges exposing "Standard" and "Enhanced" ports.

        Common pattern (varies by driver):
        - One port description contains 'standard'
        - The other contains 'enhanced'
        Typically: standard = CLI/config, enhanced = DATA (higher throughput).
        """
        standard = None
        enhanced = None
        for p in all_ports:
            desc = (p.description or "").lower()
            if standard is None and "standard" in desc:
                standard = p
            if enhanced is None and "enhanced" in desc:
                enhanced = p

        if standard and enhanced:
            return RadarPorts(
                config_port=standard.device,
                data_port=enhanced.device,
                description=f"{standard.description} / {enhanced.description}",
            )
        return None
    
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
    
    def find_radar_ports(
        self,
        verbose: bool = True,
        config_port: Optional[str] = None,
        data_port: Optional[str] = None,
    ) -> RadarPorts:
        """
        Auto-discover IWR6843 radar ports.
        
        The radar appears as two consecutive COM ports:
        - First port: Configuration/CLI (User UART)
        - Second port: Data output (Data UART)
        
        Args:
            verbose: Print discovered ports
            config_port: Optional explicit config/CLI port override
            data_port: Optional explicit data port override
            
        Returns:
            RadarPorts with config and data port names
            
        Raises:
            RuntimeError: If radar ports cannot be found
        """
        # Explicit override path: user already knows the two ports.
        if config_port and data_port:
            return RadarPorts(config_port=str(config_port), data_port=str(data_port), description="(manual override)")

        all_ports = list(serial.tools.list_ports.comports())
        
        if verbose:
            logger.info(f"Found {len(all_ports)} serial ports:")
            for p in all_ports:
                logger.info(f"  {p.device}: {p.description}")
        
        # 1) Look for XDS110 debug probe (used by TI EVMs) / mmWave identifiers.
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
        
        # 2) USB-UART bridge "Standard" + "Enhanced" ports.
        if len(radar_ports) < 2:
            pair = self._pick_standard_enhanced_pair(all_ports)
            if pair is not None:
                logger.info(f"Radar bridge found - Config: {pair.config_port}, Data: {pair.data_port}")
                return pair

        # 3) Generic fallback (common on Linux bridges): if we can reasonably choose two ports.
        # - Prefer ttyUSB/ttyACM devices
        # - If user provided only one side, infer the other as "next" device when possible
        devices = [p.device for p in all_ports]
        sorted_devices = self._sort_port_devices(devices)

        if config_port and not data_port:
            cfg = str(config_port)
            if cfg in sorted_devices:
                idx = sorted_devices.index(cfg)
                if idx + 1 < len(sorted_devices):
                    inferred = sorted_devices[idx + 1]
                    logger.info(f"Inferred data port {inferred} from config port {cfg}")
                    return RadarPorts(config_port=cfg, data_port=inferred, description="(inferred data port)")

        if data_port and not config_port:
            dat = str(data_port)
            if dat in sorted_devices:
                idx = sorted_devices.index(dat)
                if idx - 1 >= 0:
                    inferred = sorted_devices[idx - 1]
                    logger.info(f"Inferred config port {inferred} from data port {dat}")
                    return RadarPorts(config_port=inferred, data_port=dat, description="(inferred config port)")

        # If we still have <2 identified ports, use best-effort selection of ttyUSB/ttyACM pairs.
        if len(radar_ports) < 2:
            preferred = [d for d in sorted_devices if str(d).startswith("/dev/ttyUSB") or str(d).startswith("/dev/ttyACM")]
            # If exactly two preferred ports exist, treat them as config/data in order.
            if len(preferred) == 2:
                logger.info(f"Using generic USB-serial pair: {preferred[0]}, {preferred[1]}")
                return RadarPorts(config_port=preferred[0], data_port=preferred[1], description="(generic usb-serial pair)")

        if len(radar_ports) < 2:
            available = [f"{p.device} ({p.description})" for p in all_ports]
            raise RuntimeError(
                "Could not find radar ports. Need 2 ports (CLI/config + data).\n"
                f"Available ports: {available}\n"
                "If you're using a UART bridge, pass the ports explicitly (CLI + DATA)."
            )
        
        # Sort by port name/number to get consistent ordering
        radar_ports.sort(key=lambda p: self._sort_port_devices([p.device])[0])
        
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
