#!/bin/bash
# One-line installer for lazyscan
# Users can run: curl -sSL https://raw.githubusercontent.com/TheLazyIndianTechie/lazyscan/main/install.sh | bash

set -e

echo "🚀 Installing lazyscan..."

# Check if pipx is installed
if command -v pipx &> /dev/null; then
    echo "✅ pipx found, installing with pipx..."
    pipx install git+https://github.com/TheLazyIndianTechie/lazyscan.git
    echo "✅ Installation complete! Run 'lazyscan --help' to get started."
elif command -v pip3 &> /dev/null; then
    echo "📦 pipx not found, installing with pip3..."
    echo "⚠️  Note: pipx is recommended for better isolation"
    pip3 install --user git+https://github.com/TheLazyIndianTechie/lazyscan.git
    echo "✅ Installation complete! Run 'lazyscan --help' to get started."
    echo "💡 Tip: Install pipx with 'brew install pipx' for better Python app management"
else
    echo "❌ Error: Neither pipx nor pip3 found!"
    echo "Please install Python 3 first:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu: sudo apt install python3-pip"
    exit 1
fi
