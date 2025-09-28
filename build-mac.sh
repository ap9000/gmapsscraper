#!/bin/bash

echo "🏗️  Building GMaps Lead Generator v2.0 for macOS"
echo "================================================"

# Build frontend first
echo "📦 Building React frontend..."
cd frontend
npm run build
if [ $? -eq 0 ]; then
    echo "✅ Frontend build successful"
else
    echo "❌ Frontend build failed"
    exit 1
fi
cd ..

# Build Electron app
echo "🖥️  Building Electron desktop app..."
npm run build:mac
if [ $? -eq 0 ]; then
    echo "✅ Electron build successful"
    echo ""
    echo "🎉 Build Complete!"
    echo ""
    echo "📦 Build outputs:"
    echo "   📁 Frontend: frontend/dist/"
    echo "   🖥️  Mac App: dist/"
    echo ""
    if [ -f "dist/GMaps Lead Generator-2.0.0.dmg" ]; then
        echo "✅ Mac installer created: dist/GMaps Lead Generator-2.0.0.dmg"
        echo "📋 File size: $(du -h 'dist/GMaps Lead Generator-2.0.0.dmg' | cut -f1)"
    else
        echo "📄 Check dist/ folder for build outputs"
    fi
else
    echo "❌ Electron build failed"
    exit 1
fi