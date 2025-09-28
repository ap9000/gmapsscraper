# GMaps Lead Generator - Tauri Desktop App

A powerful desktop application for Google Maps lead generation with enhanced email discovery, built with Tauri for optimal performance.

## 🚀 Quick Start

### Launch the App
The built app is located in the project root:

1. **Double-click** `GMaps Lead Generator.app` 
2. **Or run from terminal**: `./launch-app.sh`
3. **Or use open command**: `open "GMaps Lead Generator.app"`

### Build from Source
```bash
# Quick build (recommended)
./build-app.sh

# Or manual build
npm run build
```

## 📁 Project Structure

```
gmapsscraper/
├── GMaps Lead Generator.app    # ← Your built desktop app (double-click to run)
├── launch-app.sh              # ← Quick launch script
├── build-app.sh              # ← Build script
├── backend/                  # Python FastAPI backend
├── frontend/                 # React frontend
├── src-tauri/               # Tauri Rust backend manager
└── config/                  # Configuration files
```

## ✨ Features

- **10x Smaller**: ~15MB vs 100MB+ with Electron
- **Better Performance**: Native Rust backend management
- **Enhanced Security**: Tauri's security model
- **Auto Backend Startup**: Python backend starts automatically
- **Health Monitoring**: Real-time connection status
- **Hash Routing**: Works perfectly with desktop environment

## 🔧 Development

### Backend Development
```bash
npm run backend:dev    # Start backend server for development
```

### Frontend Development  
```bash
npm run frontend:dev   # Start frontend dev server
```

### Full Development
```bash
npm run dev           # Start Tauri in dev mode (hot reload)
```

## 📦 Building

### Production Build
```bash
./build-app.sh        # Builds and copies app to root
```

### Manual Build Process
```bash
npm run build         # Full Tauri build
# App will be in src-tauri/target/release/bundle/macos/
```

## 🛠 Technical Details

- **Frontend**: React + Vite + Hash Router
- **Backend Manager**: Rust + Tauri
- **API Server**: Python FastAPI + Uvicorn  
- **Database**: SQLite
- **Email Discovery**: curl_cffi + Scrapling + Hunter.io

## 🚨 Troubleshooting

### App Won't Start
1. Check Console.app for error logs
2. Run from terminal to see output:
   ```bash
   "./GMaps Lead Generator.app/Contents/MacOS/gmaps-lead-generator"
   ```

### Backend Issues
- Ensure Python dependencies are installed
- Check that ports 8000 is available
- Verify config files exist in `config/` directory

### Build Issues
- Ensure Rust is installed: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- Update Tauri CLI: `npm install -g @tauri-apps/cli@latest`

## 📄 Logs

Application logs can be found in:
- **macOS**: `~/Library/Logs/GMaps Lead Generator/`
- **Console**: Use macOS Console.app to view real-time logs
- **Terminal**: Run app directly from terminal for immediate output

---

**Migration Complete**: This app has been successfully migrated from Electron to Tauri for better performance, smaller size, and native desktop integration.