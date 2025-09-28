#!/bin/bash

echo "🚀 Starting GMaps Lead Generator v2.0 Development Environment"
echo "============================================================"

# Check if backend dependencies are installed
echo "📦 Checking backend dependencies..."
if ! ./venv/bin/python -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "❌ Backend dependencies missing. Installing..."
    cd backend && ../venv/bin/pip install -r requirements.txt && cd ..
else
    echo "✅ Backend dependencies OK"
fi

# Check if frontend dependencies are installed
echo "📦 Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend dependencies missing. Installing..."
    cd frontend && npm install && cd ..
else
    echo "✅ Frontend dependencies OK"
fi

# Check if root dependencies are installed
echo "📦 Checking Electron dependencies..."
if [ ! -d "node_modules" ]; then
    echo "❌ Electron dependencies missing. Installing..."
    npm install
else
    echo "✅ Electron dependencies OK"
fi

echo ""
echo "🎯 All dependencies checked!"
echo ""
echo "You can now start the development environment with:"
echo ""
echo "Option 1 - All services at once:"
echo "   npm run dev"
echo ""
echo "Option 2 - Individual services:"
echo "   Terminal 1: npm run backend:dev"
echo "   Terminal 2: npm run frontend:dev  "
echo "   Terminal 3: npm run electron:dev"
echo ""
echo "Option 3 - Web-only development:"
echo "   Terminal 1: npm run backend:dev"
echo "   Terminal 2: npm run frontend:dev"
echo "   Browser: http://localhost:5173"
echo ""
echo "📋 Services will run on:"
echo "   🔧 Backend API: http://localhost:8000"
echo "   📱 Frontend: http://localhost:5173"
echo "   🖥️  Electron: Desktop app window"
echo "   📊 API Docs: http://localhost:8000/docs"
echo ""
echo "Ready to develop! 🎉"