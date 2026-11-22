#!/bin/bash
# ==============================================================================
# DocuVault - Native Desktop Application Launcher
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "🛡️  DocuVault Secure Document Management System (Desktop) "
echo "=========================================================="

# 1. Check Python virtual environment
if [ -d "venv" ]; then
    PYTHON_EXEC="venv/bin/python3"
else
    PYTHON_EXEC="python3"
fi

# 2. Check database presence
if [ ! -f "docuvault.db" ]; then
    echo "📦 Initializing DocuVault seed database..."
    PYTHONPATH=. "$PYTHON_EXEC" scripts/seed_data.py
fi

# 3. Check desktop dependencies
if [ ! -d "desktop/node_modules/electron" ]; then
    echo "📥 Installing desktop Electron dependencies..."
    cd desktop && npm install && cd ..
fi

echo "🚀 Launching DocuVault Desktop Application..."
cd desktop
npm start
