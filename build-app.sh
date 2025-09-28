#!/bin/bash

# GMaps Lead Generator - Build Script
echo "🔨 Building GMaps Lead Generator..."

# Build the Tauri app
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    # Copy to project root for easy access
    echo "📦 Copying app to project root..."
    cp -r "src-tauri/target/release/bundle/macos/GMaps Lead Generator.app" ./
    
    echo "🎉 App is ready! You can:"
    echo "   • Double-click 'GMaps Lead Generator.app' to launch"
    echo "   • Or run './launch-app.sh' from terminal"
    echo "   • Or run 'open \"GMaps Lead Generator.app\"' from terminal"
else
    echo "❌ Build failed!"
    exit 1
fi