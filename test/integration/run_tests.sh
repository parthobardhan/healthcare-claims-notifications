#!/bin/bash
# Script to run integration tests
# Sets up the proper Python path and virtual environment

# Activate virtual environment
source ../../backend/venv/bin/activate

# Set Python path to backend directory
export PYTHONPATH=../../backend

# Run pytest with all arguments passed to this script
python -m pytest "$@"
