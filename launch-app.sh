#!/bin/bash

# GMaps Lead Generator - Quick Launch Script
echo "🚀 Launching GMaps Lead Generator..."

# Check if app exists
if [ ! -d "GMaps Lead Generator.app" ]; then
    echo "❌ App not found. Please run 'npm run build' first."
    exit 1
fi

# Launch the app
open "GMaps Lead Generator.app"
echo "✅ App launched successfully!"