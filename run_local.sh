#!/bin/bash

# Local development startup script for Sticky Note Printer
# This script runs the application without Docker dependencies

echo "🖨️  Starting Sticky Note Printer (Local Development Mode)"
echo "==========================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "📝 Creating config.json from example..."
    cp config.json.example config.json
    echo "✅ Config created. You can edit config.json to customize settings."
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Create missing directories that would normally exist in Docker
echo "📁 Setting up local directories..."
mkdir -p logs

# Export local development environment variables
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo ""
echo "🚀 Starting server..."
echo "📍 Web Interface: http://localhost:8099"
echo "🔧 API Docs: http://localhost:8099/api/status"
echo ""
echo "ℹ️  Note: Auto-discovery uses smart fallback:"
echo "   1. First tries mDNS/Bonjour discovery"
echo "   2. Falls back to network scanning if mDNS fails"
echo "   3. Configure manual IP in config.json if needed"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the application
python3 -m src.main