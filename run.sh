#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🛡️  Starting DocuVault Secure Document Management System  🛡️"
echo "=========================================================="

# Check Python environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Seed database if not populated
if [ ! -f "docuvault.db" ]; then
    echo "Populating database with Police, Judicial, and Enterprise test scenarios..."
    PYTHONPATH=. python3 scripts/seed_data.py
fi

echo ""
echo "🚀 Server is launching on: http://localhost:8000"
echo "📚 Interactive API Docs:  http://localhost:8000/docs"
echo "=========================================================="

PYTHONPATH=. python3 app/main.py
