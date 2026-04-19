import os
import sys
import win32com.client

def create_shortcut():
    # Paths
    project_dir = os.path.dirname(os.path.abspath(__file__))
    desktop_py_path = os.path.join(project_dir, "desktop.py")
    icon_path = os.path.join(project_dir, "assets", "icon.ico")
    
    # We use pythonw.exe from the current venv to ensure no console window pops up
    pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        # Fallback to python.exe if doing an unusual install
        pythonw_exe = sys.executable

    # Get Desktop path using Windows Shell
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop_folder = shell.SpecialFolders("Desktop")
    programs_folder = shell.SpecialFolders("Programs")
    
    shortcut_name = "OptimaCV.lnk"
    desktop_shortcut_path = os.path.join(desktop_folder, shortcut_name)
    start_menu_shortcut_path = os.path.join(programs_folder, shortcut_name)

    # Create Desktop Shortcut
    print(f"Creating Desktop Shortcut at: {desktop_shortcut_path}")
    shortcut = shell.CreateShortCut(desktop_shortcut_path)
    shortcut.TargetPath = pythonw_exe
    shortcut.Arguments = f'"{desktop_py_path}"'
    shortcut.WorkingDirectory = project_dir
    shortcut.IconLocation = icon_path
    shortcut.Description = "OptimaCV Job Aggregator Desktop App"
    shortcut.WindowStyle = 1 # Normal window
    shortcut.save()

    # Create Start Menu Shortcut
    print(f"Creating Start Menu Shortcut at: {start_menu_shortcut_path}")
    start_shortcut = shell.CreateShortCut(start_menu_shortcut_path)
    start_shortcut.TargetPath = pythonw_exe
    start_shortcut.Arguments = f'"{desktop_py_path}"'
    start_shortcut.WorkingDirectory = project_dir
    start_shortcut.IconLocation = icon_path
    start_shortcut.Description = "OptimaCV Job Aggregator Desktop App"
    start_shortcut.WindowStyle = 1
    start_shortcut.save()

    print("\n✅ Install successful!")
    print(f"You can now double-click 'OptimaCV' on your desktop to launch the app.")

if __name__ == "__main__":
    # Ensure dependencies are available before creating
    try:
        import webview
        import psutil
    except ImportError:
        print("Error: Missing required packages. Please make sure pywebview and psutil are installed.")
        sys.exit(1)
        
    create_shortcut()
