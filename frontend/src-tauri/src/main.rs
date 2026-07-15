#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::api::process::{Command, CommandEvent, CommandChild};
use tauri::Manager;
use std::sync::Mutex;

struct SidecarState {
    child: Mutex<Option<CommandChild>>,
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            // Launch the FastAPI sidecar
            let (mut rx, child) = Command::new_sidecar("nebula-backend")
                .expect("failed to create `nebula-backend` binary command")
                .spawn()
                .expect("Failed to spawn sidecar");

            app.manage(SidecarState {
                child: Mutex::new(Some(child)),
            });

            tauri::async_runtime::spawn(async move {
                // Read events such as stdout
                while let Some(event) = rx.recv().await {
                    if let CommandEvent::Stdout(line) = event {
                        println!("backend: {}", line);
                    }
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            let state = app_handle.state::<SidecarState>();
            if let Ok(mut child_lock) = state.child.lock() {
                if let Some(child) = child_lock.take() {
                    let _ = child.kill();
                }
            }
        }
    });
}
