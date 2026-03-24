sensorStop
flushCfg
dfeDataOutputMode 1
channelCfg 15 7 0
adcCfg 2 1
adcbufCfg -1 0 1 1 1

profileCfg 0 60 216 7 200 0 0 20 1 384 2000 0 0 158
chirpCfg 0 0 0 0 0 0 0 1
chirpCfg 1 1 0 0 0 0 0 2
chirpCfg 2 2 0 0 0 0 0 4
frameCfg 0 2 16 0 100 1 0
lowPower 0 0

guiMonitor -1 1 1 0 0 0 1

cfarCfg -1 0 2 8 4 3 0 20 1
cfarCfg -1 1 0 4 2 3 1 18 1

multiObjBeamForming -1 1 0.55

% Para persona quieta probar 0; para walking test dejar 1
clutterRemoval -1 0

calibDcRangeSig -1 1 -5 8 256

extendedMaxVelocity -1 0
lvdsStreamCfg -1 0 0 0
compRangeBiasAndRxChanPhase 0.0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0 1 0 -1 0
measureRangeBiasAndRxChanPhase 0 1.5 0.2
CQRxSatMonitor 0 3 19 125 0
CQSigImgMonitor 0 127 6
analogMonitor 0 0

aoaFovCfg -1 -20 20 -10 15
cfarFovCfg -1 0 0.50 3.00
cfarFovCfg -1 1 -1 1.00

calibData 1 0 0x1F0000
sensorStart
