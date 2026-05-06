# Layer 8 Jetson Runbook



cd ~/Desktop/SCANU-dev_adrian/software
source .venv/bin/activate
pip install requests eval_type_backport

# Ejecutar desde software/ con PYTHONPATH
PYTHONPATH="$HOME/Desktop/SCANU-dev_adrian:$PWD" \
  python3 layer8_ui/scripts/run.py
