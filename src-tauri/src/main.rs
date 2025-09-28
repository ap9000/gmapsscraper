// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::HashMap;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager, State};
use tokio::time::{sleep, Duration};
use log::{info, error, warn};

// Python backend manager
pub struct PythonBackend {
    process: Arc<Mutex<Option<Child>>>,
    is_running: Arc<Mutex<bool>>,
}

impl PythonBackend {
    pub fn new() -> Self {
        Self {
            process: Arc::new(Mutex::new(None)),
            is_running: Arc::new(Mutex::new(false)),
        }
    }

    pub async fn start(&self, app_handle: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
        // Check if already running
        {
            let is_running = self.is_running.lock().unwrap();
            if *is_running {
                info!("Python backend already running");
                return Ok(());
            }
        }

        // Get app data directory
        let app_data_dir = app_handle.path().app_data_dir()
            .map_err(|e| format!("Failed to get app data directory: {}", e))?;
        
        // For development/testing, use a hardcoded path to the project directory
        // In production, you might want to bundle the backend or use a different approach
        let project_root = std::path::PathBuf::from("/Users/alexpelletier/Documents/gmapsscraper");
        
        let backend_dir = project_root.join("backend");
        let config_path = project_root.join("config").join("config.yaml");
        let data_path = project_root.join("data");

        info!("Starting Python backend");
        info!("Project root: {:?}", project_root);
        info!("Backend directory: {:?}", backend_dir);
        info!("Config path: {:?}", config_path);
        info!("Data path: {:?}", data_path);

        // Verify paths exist
        if !backend_dir.exists() {
            return Err(format!("Backend directory not found: {:?}", backend_dir).into());
        }
        if !config_path.exists() {
            return Err(format!("Config file not found: {:?}", config_path).into());
        }
        if !data_path.exists() {
            return Err(format!("Data directory not found: {:?}", data_path).into());
        }

        // Set up environment variables
        let mut env_vars = HashMap::new();
        env_vars.insert("GMAPS_CONFIG_PATH".to_string(), config_path.to_string_lossy().to_string());
        env_vars.insert("GMAPS_DATA_PATH".to_string(), data_path.to_string_lossy().to_string());

        // Start Python backend process
        let mut cmd = Command::new("python3");
        cmd.current_dir(&backend_dir)
            .args(&["-m", "uvicorn", "api.server:app", "--host", "127.0.0.1", "--port", "8000"])
            .envs(&env_vars);

        match cmd.spawn() {
            Ok(child) => {
                info!("Python backend started successfully with PID: {}", child.id());
                
                // Store the process and update status
                {
                    let mut process = self.process.lock().unwrap();
                    *process = Some(child);
                }
                {
                    let mut is_running = self.is_running.lock().unwrap();
                    *is_running = true;
                }
                
                // Wait a moment for backend to initialize
                sleep(Duration::from_secs(2)).await;
                
                Ok(())
            }
            Err(e) => {
                error!("Failed to start Python backend: {}", e);
                Err(Box::new(e))
            }
        }
    }

    pub fn stop(&self) {
        let mut process = self.process.lock().unwrap();
        let mut is_running = self.is_running.lock().unwrap();
        
        if let Some(mut child) = process.take() {
            info!("Stopping Python backend");
            if let Err(e) = child.kill() {
                warn!("Failed to kill Python backend process: {}", e);
            }
            if let Err(e) = child.wait() {
                warn!("Failed to wait for Python backend process: {}", e);
            }
        }
        
        *is_running = false;
    }

    pub fn is_running(&self) -> bool {
        *self.is_running.lock().unwrap()
    }
}

// Tauri commands
#[tauri::command]
async fn get_backend_status(backend: State<'_, PythonBackend>) -> Result<bool, String> {
    Ok(backend.is_running())
}

#[tauri::command]
async fn restart_backend(
    backend: State<'_, PythonBackend>,
    app_handle: AppHandle,
) -> Result<(), String> {
    info!("Restarting Python backend");
    backend.stop();
    
    sleep(Duration::from_secs(1)).await;
    
    backend.start(&app_handle).await
        .map_err(|e| format!("Failed to restart backend: {}", e))?;
    
    Ok(())
}

#[tauri::command]
async fn get_app_version() -> Result<String, String> {
    Ok("2.0.0".to_string())
}

#[tauri::command]
async fn open_external_url(url: String) -> Result<(), String> {
    if let Err(e) = open::that(&url) {
        return Err(format!("Failed to open URL: {}", e));
    }
    Ok(())
}

fn main() {
    env_logger::init();
    
    // Create Python backend manager
    let python_backend = PythonBackend::new();

    tauri::Builder::default()
        .manage(python_backend)
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            get_backend_status,
            restart_backend,
            get_app_version,
            open_external_url
        ])
        .setup(|app| {
            let app_handle = app.handle().clone();
            
            // Start Python backend on app startup
            tauri::async_runtime::spawn(async move {
                let backend: State<PythonBackend> = app_handle.state();
                
                if let Err(e) = backend.start(&app_handle).await {
                    error!("Failed to start Python backend on startup: {}", e);
                    
                    // Log error - we'll skip the dialog for now as it requires more complex setup
                    eprintln!("Backend startup error: {}", e);
                }
            });
            
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Stop Python backend when app is closing
                let backend: State<PythonBackend> = window.state();
                backend.stop();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}