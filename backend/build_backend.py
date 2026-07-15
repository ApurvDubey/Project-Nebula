import PyInstaller.__main__

def build():
    # Identify the correct name for the sidecar executable based on OS and architecture
    # Tauri expects the sidecar binary to have a specific name format:
    # <name>-<target-triple>.exe
    # For simplicity, we'll just output the binary as "nebula-backend" and let the developer rename it,
    # or we can try to guess the target triple.
    
    PyInstaller.__main__.run([
        'app/main.py',
        '--name=nebula-backend',
        '--onedir', # we use onedir to avoid extraction overhead, but onefile is also an option
        '--noconfirm',
        '--clean',
        '--add-data=app;app', # Include app directory
    ])
    
    print("Build complete. Executable is in the 'dist/nebula-backend' folder.")

if __name__ == "__main__":
    build()
