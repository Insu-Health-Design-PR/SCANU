% ***************************************************************
% Aggressive indoor inspection profile (xWR68xx_AOP)
% Goal:
% - Keep person detection usable
% - Increase chance of separating compact object near body
% - Maintain 10 FPS operation
% Notes:
% - More permissive CFAR than stable profile
% - More permissive multi-object split
% - Clutter removal kept enabled for indoor stability
% - Tighter angle and shorter range window
% ***************************************************************
sensorStop
flushCfg
dfeDataOutputMode 1
channelCfg 15 7 0
adcCfg 2 1
adcbufCfg -1 0 1 1 1
% Keep same base waveform timing as your working profiles
profileCfg 0 60 216 7 200 0 0 20 1 384 2000 0 0 158
chirpCfg 0 0 0 0 0 0 0 1
chirpCfg 1 1 0 0 0 0 0 2
chirpCfg 2 2 0 0 0 0 0 4
frameCfg 0 2 16 0 100 1 0
lowPower 0 0
% Output point cloud + range profile + stats
guiMonitor -1 1 1 0 0 0 1
% More permissive CFAR to keep weaker compact reflectors
cfarCfg -1 0 2 8 4 3 0 20 1
cfarCfg -1 1 0 4 2 3 1 18 1
% More permissive multi-object split
multiObjBeamForming -1 1 0.55
% Remove static clutter
clutterRemoval -1 1
% Enable DC range signature calibration
calibDcRangeSig -1 1 -5 8 256
extendedMaxVelocity -1 0
lvdsStreamCfg -1 0 0 0
compRangeBiasAndRxChanPhase 0.0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0
measureRangeBiasAndRxChanPhase 0 1.5 0.2
CQRxSatMonitor 0 3 19 125 0
CQSigImgMonitor 0 127 6
analogMonitor 0 0
% Tighter useful angle window to suppress side clutter
aoaFovCfg -1 -20 20 -10 12
% Shorter useful indoor range for person + carried object
cfarFovCfg -1 0 0.45 3.00
% Keep conservative doppler window
cfarFovCfg -1 1 -1 1.00
calibData 1 0 0x1F0000
sensorStart
