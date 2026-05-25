#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOFTWARE_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

CLI_PORT="${CLI_PORT:-/dev/ttyACM0}"
ETH_DEV="${ETH_DEV:-eth0}"
JETSON_IP="${JETSON_IP:-192.168.33.30}"
DCA_IP="${DCA_IP:-192.168.33.180}"
RADAR_CFG="${RADAR_CFG:-${SOFTWARE_DIR}/layer1_sensor_hub/testing/configs/dca1000_adc_capture.cfg}"
DCA_CFG="${DCA_CFG:-${SCRIPT_DIR}/ti_cli/configFile.json}"
OUTPUT="${OUTPUT:-${SOFTWARE_DIR}/captures/adc_data.bin}"
DURATION_S="${DURATION_S:-5}"

echo "[jetson-capture] software dir : ${SOFTWARE_DIR}"
echo "[jetson-capture] radar cfg    : ${RADAR_CFG}"
echo "[jetson-capture] dca cfg      : ${DCA_CFG}"
echo "[jetson-capture] output       : ${OUTPUT}"
echo "[jetson-capture] ethernet     : ${ETH_DEV} ${JETSON_IP} -> ${DCA_IP}"

if [[ "${CONFIGURE_NET:-0}" == "1" ]]; then
  sudo ip addr flush dev "${ETH_DEV}"
  sudo ip addr add "${JETSON_IP}/24" dev "${ETH_DEV}"
  sudo ip link set "${ETH_DEV}" up
fi

cd "${SOFTWARE_DIR}"
python3 -m layer1_sensor_hub.mmwave_dca.run_dca_capture \
  --cli-port "${CLI_PORT}" \
  --config "${RADAR_CFG}" \
  --dca-config "${DCA_CFG}" \
  --output "${OUTPUT}" \
  --duration-s "${DURATION_S}" \
  --pc-ip "${JETSON_IP}" \
  --dca-ip "${DCA_IP}" \
  --configure-dca \
  --start-dca \
  --stop-dca
