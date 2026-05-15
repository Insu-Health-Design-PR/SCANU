#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALLER="${MODULE_DIR}/mmwave_studio_02_01_01_00_win32.exe"
EXTRACT_DIR="${SCRIPT_DIR}/mmwave_studio_extract"

if [[ ! -f "${INSTALLER}" ]]; then
  echo "ERROR: installer not found:"
  echo "  ${INSTALLER}"
  exit 1
fi

if ! command -v 7z >/dev/null 2>&1; then
  echo "Installing p7zip-full because 7z is required to extract TI's Windows installer."
  sudo apt update
  sudo apt install -y p7zip-full
fi

mkdir -p "${EXTRACT_DIR}"
7z x "${INSTALLER}" "-o${EXTRACT_DIR}"

echo
echo "Searching for DCA1000 CLI files..."
find "${EXTRACT_DIR}" \
  \( -iname 'DCA1000EVM_CLI_Control*' -o -iname 'DCA1000EVM_CLI_Record*' -o -iname '*DCA1000*' \) \
  -print

echo
echo "If DCA1000EVM_CLI_Control is present, copy it into:"
echo "  ${SCRIPT_DIR}"
echo
echo "If only SourceCode appears, compile TI's DCA1000 SourceCode on the Jetson,"
echo "then copy the built DCA1000EVM_CLI_Control binary into ${SCRIPT_DIR}."
