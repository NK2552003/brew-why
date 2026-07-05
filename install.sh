#!/usr/bin/env bash
set -e

echo "Installing brew-why using pipx..."

# Check if pipx is installed, if not, suggest installing it
if ! command -v pipx &> /dev/null; then
    echo "⚠️  pipx is not installed."
    echo "pipx is the recommended way to install Python CLI applications in isolated environments."
    echo "Please install it using: brew install pipx"
    echo "Then run this script again."
    exit 1
fi

# Install the current directory using pipx
pipx install . --force

echo "✅ Installation complete!"
echo "Run 'brew-why --help' to get started."
