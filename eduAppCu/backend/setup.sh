#!/bin/bash

# Backend setup script for FastAPI
# Creates virtual environment and installs dependencies

set -e

echo "🚀 Setting up FastAPI backend..."

cd backend

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment and install dependencies
echo "📥 Installing dependencies..."
.venv/bin/python -m pip install -q -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To start the backend, run:"
echo "  npm run backend"
echo ""
echo "Backend will be available at:"
echo "  - API: http://localhost:5001"
echo "  - Docs: http://localhost:5001/docs"
echo "  - ReDoc: http://localhost:5001/redoc"
