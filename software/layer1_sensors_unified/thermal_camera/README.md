% ***************************************************************
% SCAN-U indoor inspection profile v2
% Goal:
% - Keep person tracking stable
% - Slightly improve separation of a compact object near body
% - Avoid aggressive changes that may break parser/demo behavior
% - Keep 10 FPS
% ***************************************************************

sensorStop
flushCfg

dfeDataOutputMode 1
channelCfg 15 7 0
adcCfg 2 1
adcbufCfg -1 0 1 1 1

% Base waveform kept close to working profile
profileCfg 0 60 216 7 200 0 0 20 1 384 2000 0 0 158
chirpCfg 0 0 0 0 0 0 0 1
chirpCfg 1 1 0 0 0 0 0 2
chirpCfg 2 2 0 0 0 0 0 4
frameCfg 0 2 16 0 100 1 0
lowPower 0 0

% Output point cloud + range profile + stats
guiMonitor -1 1 1 0 0 0 1

% Slightly less aggressive than your stable profile
cfarCfg -1 0 2 8 4 3 0 22 1
cfarCfg -1 1 0 4 2 3 1 20 1

% Moderate multi-object separation
multiObjBeamForming -1 1 0.65

% Keep clutter removal on for stability
clutterRemoval -1 1

% Keep DC range signature calibration
calibDcRangeSig -1 1 -5 8 256

extendedMaxVelocity -1 0
lvdsStreamCfg -1 0 0 0

compRangeBiasAndRxChanPhase 0.0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0
measureRangeBiasAndRxChanPhase 0 1.5 0.2

CQRxSatMonitor 0 3 19 125 0
CQSigImgMonitor 0 127 6
analogMonitor 0 0

% Tighter angle window to reduce side clutter
aoaFovCfg -1 -25 25 -15 15

% Useful indoor range for person + carried object
cfarFovCfg -1 0 0.40 4.00

% Conservative doppler window
cfarFovCfg -1 1 -1.00 1.00

calibData 1 0 0x1F0000
sensorStart
