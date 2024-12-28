# youtube_analyzer/requirements_installer/install_requirements.py
import sys
import subprocess
import os

def install_requirements():
    """
    Installs Python packages listed in ../requirements.txt
    into this local environment or a specified location.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_file = os.path.join(os.path.dirname(current_dir), 'requirements.txt')

    if not os.path.isfile(requirements_file):
        print("requirements.txt not found.")
        return

    print("Installing requirements from:", requirements_file)
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'
        ])
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '--target', current_dir, '-r', requirements_file
        ])
        print("All requirements installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
