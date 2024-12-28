# youtube_analyzer/main.py
import sys
import os
import importlib

def check_and_install_requirements():
    try:
        importlib.import_module("selenium")
        importlib.import_module("pandas")
        importlib.import_module("requests")
        importlib.import_module("tkinter")
        # Add more libraries if needed
        print("All requirements are already installed.")
    except ImportError:
        # If any import fails, run the installer
        print("Some requirements are missing. Installing now...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        installer_path = os.path.join(current_dir, "requirements_installer", "install_requirements.py")
        if os.path.isfile(installer_path):
            import subprocess
            subprocess.check_call([sys.executable, installer_path])
        else:
            print("Installer script not found. Please install dependencies manually.")
        # Reload the script to ensure we can now import the modules
        os.execv(sys.executable, [sys.executable] + sys.argv)

def main():
    check_and_install_requirements()

    # Adjust sys.path to include the local 'requirements_installer' folder
    # so Python can find and use the installed packages there.
    local_requirements_dir = os.path.join(os.path.dirname(__file__), "requirements_installer")
    if local_requirements_dir not in sys.path:
        sys.path.append(local_requirements_dir)
    
    # Now we can import our GUI and run it
    from src.gui import start_gui
    start_gui()

if __name__ == "__main__":
    main()
