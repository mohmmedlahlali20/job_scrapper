import subprocess
import sys
import os
import time
import socket
import webview
import psutil

# ── Path Resolution for PyInstaller ──────────────────────────────────────────
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

STREAMLIT_PORT = 8501
URL = f"http://localhost:{STREAMLIT_PORT}"

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_tree(pid):
    """Kills a process and all of its children."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass

def start_streamlit():
    """Starts the streamlit server as a background process."""
    env = os.environ.copy()
    
    # Path to app.py in the bundle
    app_path = get_resource_path("app.py")
    
    # If running as an EXE, sys.executable is the exe. 
    # We might need to call streamlit as a module from the bundled python environment.
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", str(STREAMLIT_PORT),
        "--server.headless", "true",
        "--theme.base", "dark",
        "--global.developmentMode", "false"
    ]
    
    # Detach process from console if on Windows
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
        
    process = subprocess.Popen(
        cmd,
        env=env,
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(app_path) # Important: set CWD to where app.py is
    )
    return process

def main():
    print("Initializing system...")
    
    # Clean up any orphan PIDs from previous runs if they exist
    if os.path.exists("scraper.pid"):
        try:
            with open("scraper.pid", "r") as f:
                old_pid = int(f.read().strip())
                if psutil.pid_exists(old_pid):
                    psutil.Process(old_pid).terminate()
            os.remove("scraper.pid")
        except:
            pass

    print("Starting OptimaCV Engine...")
    server_process = start_streamlit()

    # Wait for the Streamlit server to boot up
    retries = 40 # Increased retries for slower bundled startup
    ready = False
    while retries > 0:
        if is_port_in_use(STREAMLIT_PORT):
            ready = True
            break
        time.sleep(1)
        retries -= 1

    if not ready:
        print("Waiting for engine to respond...", file=sys.stderr)
    else:
        print("Engine ready!")

    # Create the native desktop window
    window = webview.create_window(
        "OptimaCV Job Aggregator", 
        URL,
        width=1280,
        height=800,
        min_size=(800, 600)
    )

    # Start the GUI event loop
    try:
        webview.start(private_mode=False)
    finally:
        # User closed the window, shut down the server
        print("Shutting down engine...")
        try:
            kill_process_tree(server_process.pid)
        except:
            pass

if __name__ == "__main__":
    main()
