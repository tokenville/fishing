#!/bin/bash

echo "🎣 Starting Fishing WebApp in Development Mode"
echo "=============================================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if mock images exist
if [ ! -d "mock/images" ] || [ -z "$(ls -A mock/images 2>/dev/null)" ]; then
    echo "🎨 Generating mock images..."
    cd mock
    python3 generate_mock_images.py
    cd ..
    echo ""
fi

echo "🚀 Starting development server..."
echo ""
echo "The webapp will open in your browser at:"
echo "👉 http://localhost:3001/webapp"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the development server
npm run dev