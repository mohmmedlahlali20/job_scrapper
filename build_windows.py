import os
import subprocess
import os
import shutil
import sys

def build():
    print("Starting OptimaCV Windows Build Process...")

    # Name of the final executable
    EXE_NAME = "OptimaCV"
    MAIN_SCRIPT = "desktop.py"

    # Files and folders to include
    # Format: (path_on_disk, destination_in_exe)
    add_data = [
        ("app.py", "."),
        ("config.py", "."),
        ("db.py", "."),
        ("engine.py", "."),
        ("models.py", "."),
        ("run.py", "."),
        ("assets", "assets"),
        ("scrapers", "scrapers"),
        ("filters", "filters"),
        (".streamlit", ".streamlit"), # Include streamlit config if it exists
    ]

    # Clean up previous builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            shutil.rmtree(folder)

    # Base PyInstaller command
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed", # No console window
        f"--name={EXE_NAME}",
        f"--icon=assets/icon.ico" if os.path.exists("assets/icon.ico") else "",
    ]

    # Add data files
    for src, dst in add_data:
        if os.path.exists(src):
            cmd.append(f"--add-data={src}{os.pathsep}{dst}")

    # Streamlit specific flags
    # We need to collect all streamlit metadata and static files
    cmd.extend([
        "--collect-all", "streamlit",
        "--collect-all", "scrapling",
        "--copy-metadata", "streamlit",
        "--copy-metadata", "scrapling",
    ])

    # Hidden imports that might be missed
    hidden_imports = [
        "streamlit.runtime.scriptrunner.magic_funcs",
        "pymysql",
    ]
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")

    # Entry point
    cmd.append(MAIN_SCRIPT)

    # Filter out empty strings
    cmd = [c for c in cmd if c]

    print(f"Executing: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print(f"\nBuild Complete! Your executable is in the 'dist' folder.")
        print(f"Location: {os.path.abspath('dist/' + EXE_NAME + '.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild Failed with exit code {e.returncode}")
        print("Make sure you have pyinstaller installed: pip install pyinstaller")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Error: PyInstaller is not installed. Run: pip install pyinstaller")
        sys.exit(1)
        
    build()
