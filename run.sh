#!/bin/bash

# CallWaiting.ai TTS Service Runner Script

echo "🚀 Starting CallWaiting.ai TTS Service"
echo "======================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
python3 -c "import fastapi, uvicorn, edge_tts" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Create logs directory
mkdir -p logs

# Start the service
echo "🎤 Starting TTS service on http://localhost:8000"
echo "📚 API docs available at: http://localhost:8000/docs"
echo "🔑 Demo API Key: cw_demo_12345"
echo "🔑 Test API Key: test_key_67890"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

python3 main.py