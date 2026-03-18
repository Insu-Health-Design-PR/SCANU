"""
Radar configuration via CLI commands.

Sends configuration commands to the IWR6843 over the config UART port.
"""

import time
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from .serial_manager import SerialManager
from .radar_constants import SerialConfig

logger = logging.getLogger(__name__)


# Default configuration for people/object detection
# Optimized for indoor use, ~10m range, 10 FPS
DEFAULT_CONFIG = """
% IWR6843 Configuration for Object Detection
% Range: ~10m, Frame rate: 10 FPS
% Bandwidth: ~4 GHz, Range resolution: ~3.75 cm

sensorStop
flushCfg

% Output mode: 1 = frame based
dfeDataOutputMode 1

% Channel config: RX mask=15 (all 4), TX mask=7 (all 3), cascade=0
channelCfg 15 7 0

% ADC config: 16-bit, complex output
adcCfg 2 1

% ADC buffer config
adcbufCfg -1 0 1 1 1

% Profile config (THE KEY SETTINGS)
% profileId=0, startFreq=60.75GHz, idleTime=7us, adcStartTime=7us
% rampEndTime=57.14us, txPower=0, txPhaseShift=0, freqSlope=70MHz/us
% txStartTime=1us, numAdcSamples=256, sampleRate=5000ksps
% hpfCorner1=0, hpfCorner2=0, rxGain=158
profileCfg 0 60.75 7 7 57.14 0 0 70 1 256 5000 0 0 158

% Chirp configs for 3 TX antennas
chirpCfg 0 0 0 0 0 0 0 1
chirpCfg 1 1 0 0 0 0 0 4
chirpCfg 2 2 0 0 0 0 0 2

% Frame config: chirps 0-2, 16 loops, continuous, 100ms period
frameCfg 0 2 16 0 100 1 0

% Low power mode disabled
lowPower 0 0

% GUI monitor config: enable detected points and range profile
% -1=all subframes, points=1, rangeProfile=1, noiseProfile=0
% azimuthHeatmap=0, dopplerHeatmap=0, stats=1
guiMonitor -1 1 1 0 0 0 1

% CFAR config for range dimension
cfarCfg -1 0 2 8 4 3 0 15.0 0

% CFAR config for doppler dimension
cfarCfg -1 1 0 4 2 3 1 15.0 0

% Multi-object beam forming
multiObjBeamForming -1 1 0.5

% Clutter removal disabled (enable with 1 if static clutter is issue)
clutterRemoval -1 0

% DC range calibration
calibDcRangeSig -1 0 -5 8 256

% Extended max velocity disabled
extendedMaxVelocity -1 0

% Range bias and phase compensation (default/uncalibrated)
compRangeBiasAndRxChanPhase 0.0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0

% Measurement config
measureRangeBiasAndRxChanPhase 0 1.5 0.2

% CQ monitors
CQRxSatMonitor 0 3 5 121 0
CQSigImgMonitor 0 127 4

% Analog monitor disabled
analogMonitor 0 0

% AOA FOV config: full field of view
aoaFovCfg -1 -90 90 -90 90

% CFAR FOV configs
cfarFovCfg -1 0 0.25 9.0
cfarFovCfg -1 1 -1 1.0

sensorStart
""".strip()


# Minimal config for quick testing
MINIMAL_CONFIG = """
sensorStop
flushCfg
dfeDataOutputMode 1
channelCfg 15 7 0
adcCfg 2 1
adcbufCfg -1 0 1 1 1
profileCfg 0 60.75 7 7 57.14 0 0 70 1 256 5000 0 0 158
chirpCfg 0 0 0 0 0 0 0 1
chirpCfg 1 1 0 0 0 0 0 4
chirpCfg 2 2 0 0 0 0 0 2
frameCfg 0 2 16 0 100 1 0
lowPower 0 0
guiMonitor -1 1 1 0 0 0 1
cfarCfg -1 0 2 8 4 3 0 15.0 0
cfarCfg -1 1 0 4 2 3 1 15.0 0
multiObjBeamForming -1 1 0.5
clutterRemoval -1 0
calibDcRangeSig -1 0 -5 8 256
extendedMaxVelocity -1 0
compRangeBiasAndRxChanPhase 0.0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0
measureRangeBiasAndRxChanPhase 0 1.5 0.2
CQRxSatMonitor 0 3 5 121 0
CQSigImgMonitor 0 127 4
analogMonitor 0 0
aoaFovCfg -1 -90 90 -90 90
cfarFovCfg -1 0 0.25 9.0
cfarFovCfg -1 1 -1 1.0
sensorStart
""".strip()


@dataclass
class ConfigResult:
    """Result of configuration attempt."""
    success: bool
    commands_sent: int
    errors: List[str]
    responses: List[str]


class RadarConfigurator:
    """
    Configures the IWR6843 radar via CLI commands.
    
    Usage:
        configurator = RadarConfigurator(serial_manager)
        result = configurator.configure()  # Uses DEFAULT_CONFIG
        # or
        result = configurator.configure_from_file('my_config.cfg')
        
        if result.success:
            print("Radar configured!")
        
        # Later...
        configurator.stop()
    """
    
    def __init__(self, serial_manager: SerialManager):
        """
        Initialize configurator.
        
        Args:
            serial_manager: Connected SerialManager instance
        """
        self.serial = serial_manager
        self._is_running = False
    
    def send_command(
        self,
        command: str,
        delay: float = SerialConfig.COMMAND_DELAY,
        response_timeout: float = 1.5,
    ) -> str:
        """
        Send a single CLI command and read response.
        
        Args:
            command: CLI command string (without newline)
            delay: Time to wait for response (seconds)
            response_timeout: Maximum time to read response (seconds)
            
        Returns:
            Response string from radar
        """
        if not self.serial.config_port or not self.serial.config_port.is_open:
            raise RuntimeError("Config port not connected")
        
        # Clean command
        cmd = command.strip()
        if not cmd or cmd.startswith('%'):
            return ""  # Skip empty lines and comments
        
        # Flush any stale CLI output before sending a new command so responses align.
        try:
            if self.serial.config_port.in_waiting:
                self.serial.config_port.read(self.serial.config_port.in_waiting)
        except Exception:
            # Not fatal; proceed.
            pass

        # Send command with newline
        cmd_bytes = (cmd + '\n').encode('utf-8')
        self.serial.config_port.write(cmd_bytes)
        
        # Wait for processing (minimum inter-command gap)
        if delay > 0:
            time.sleep(delay)

        # Read response. Many mmWave demo firmwares only become ready for the next
        # command once the CLI prompt re-appears (e.g., "mmwDemo:/>").
        response_chunks: List[str] = []
        start = time.time()
        while (time.time() - start) < response_timeout:
            waiting = 0
            try:
                waiting = self.serial.config_port.in_waiting
            except Exception:
                waiting = 0

            if waiting > 0:
                chunk = self.serial.config_port.read(waiting).decode('utf-8', errors='ignore')
                if chunk:
                    response_chunks.append(chunk)
                    combined = "".join(response_chunks)
                    if "mmwDemo:/>" in combined or combined.strip().endswith(">"):
                        break
            else:
                time.sleep(0.01)

        response = "".join(response_chunks)
        
        logger.debug(f"CMD: {cmd}")
        if response.strip():
            logger.debug(f"RSP: {response.strip()}")
        
        return response
    
    def _parse_config_string(self, config: str) -> List[str]:
        """Parse configuration string into list of commands."""
        commands = []
        for line in config.strip().split('\n'):
            line = line.strip()
            # Skip empty lines and comments (% is TI comment style)
            if line and not line.startswith('%') and not line.startswith('#'):
                commands.append(line)
        return commands
    
    def load_config_file(self, config_path: Path) -> List[str]:
        """
        Load configuration commands from a .cfg file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            List of command strings
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r') as f:
            content = f.read()
        
        return self._parse_config_string(content)
    
    def configure(self, config: Optional[str] = None) -> ConfigResult:
        """
        Send configuration to radar.
        
        Args:
            config: Configuration string (newline-separated commands)
                   If None, uses DEFAULT_CONFIG
        
        Returns:
            ConfigResult with success status and details
        """
        if config is None:
            config = DEFAULT_CONFIG
        
        commands = self._parse_config_string(config)
        
        logger.info(f"Sending {len(commands)} configuration commands...")
        
        errors = []
        responses = []
        
        for i, cmd in enumerate(commands):
            response = self.send_command(cmd)
            responses.append(response)
            
            # Check for errors in response
            if 'Error' in response or 'error' in response:
                error_msg = f"Command {i+1} '{cmd}': {response.strip()}"
                errors.append(error_msg)
                logger.error(error_msg)
            
            # Track if sensor is running
            if cmd.lower() == 'sensorstart':
                self._is_running = True
            elif cmd.lower() == 'sensorstop':
                self._is_running = False
        
        success = len(errors) == 0
        
        if success:
            logger.info(f"Configuration complete: {len(commands)} commands sent")
        else:
            logger.error(f"Configuration had {len(errors)} errors")
        
        return ConfigResult(
            success=success,
            commands_sent=len(commands),
            errors=errors,
            responses=responses
        )
    
    def configure_from_file(self, config_path: Path) -> ConfigResult:
        """
        Load and send configuration from a file.
        
        Args:
            config_path: Path to .cfg file
            
        Returns:
            ConfigResult with success status
        """
        commands = self.load_config_file(config_path)
        config_str = '\n'.join(commands)
        return self.configure(config_str)
    
    def stop(self) -> str:
        """Stop the radar sensor."""
        response = self.send_command('sensorStop')
        self._is_running = False
        logger.info("Radar stopped")
        return response
    
    def start(self) -> str:
        """Start the radar sensor (resume after stop)."""
        response = self.send_command('sensorStart')
        self._is_running = True
        logger.info("Radar started")
        return response
    
    @property
    def is_running(self) -> bool:
        """Check if radar is currently running."""
        return self._is_running
    
    def get_version(self) -> str:
        """Query radar firmware version."""
        return self.send_command('version')
