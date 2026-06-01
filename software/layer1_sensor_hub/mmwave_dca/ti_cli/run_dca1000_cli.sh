#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
CONFIG="${1:-${SCRIPT_DIR}/configFile.json}"
CLI="${DCA1000_CLI_BIN:-${SCRIPT_DIR}/DCA1000EVM_CLI_Control}"

if [[ ! -x "${CLI}" ]]; then
  echo "ERROR: DCA1000 CLI binary not found or not executable:"
  echo "  ${CLI}"
  echo
  echo "Run setup_ti_cli.sh, then copy/build DCA1000EVM_CLI_Control into:"
  echo "  ${SCRIPT_DIR}"
  exit 1
fi

mkdir -p /home/insu/Desktop/SCANU-dev_adrian/captures

echo "[dca1000] Configure Jetson Ethernet"
sudo ip addr add 192.168.33.30/24 dev eth0 2>/dev/null || true
sudo ip link set eth0 up

echo "[dca1000] FPGA config"
"${CLI}" fpga "${CONFIG}"

echo "[dca1000] Record config"
"${CLI}" record "${CONFIG}"

echo "[dca1000] Start record"
"${CLI}" start_record "${CONFIG}"

echo
echo "DCA1000 is recording now."
echo "In a second terminal, start the radar:"
echo
echo "cd ${PROJECT_DIR}"
echo "source software/.venv/bin/activate"
echo "python3 - <<'PY'"
echo "from pathlib import Path"
echo "from software.layer1_sensor_hub.mmwave_dca.radar_cli import RadarCliConfig, configure_radar_from_file"
echo "configure_radar_from_file(RadarCliConfig(port='/dev/ttyACM0'), Path('software/layer1_sensor_hub/examples/configs/dca1000_adc_capture.cfg'), defer_sensor_start=False)"
echo "PY"
echo
echo "After capture, stop recording with:"
echo "  ${CLI} stop_record ${CONFIG}"
