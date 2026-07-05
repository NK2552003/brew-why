#!/bin/bash
set -e

echo "Setting up Python virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing project in editable mode..."
pip install -e .

echo "Setup complete! You can now run 'source .venv/bin/activate' and use 'brew-why'."
