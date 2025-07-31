#!/bin/bash
source scripts/methods.sh

# Check OS Type
validate_os_type

# Validate Python (this will also setup venv)
validate_python

# Install requirements (this will ensure venv is active)
install_python_requirements src/workstation_orchestrator/requirements.txt

python src/workstation_orchestrator/main.py $@

# Deactivate virtual environment
deactivate_venv
