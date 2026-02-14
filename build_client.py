import os
import subprocess
import sys

def install_pyinstaller():
    try:
        import PyInstaller
        print("PyInstaller already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build():
    print("Starting build process...")
    
    # Clean previous builds
    if os.path.exists("dist"):
        import shutil
        shutil.rmtree("dist")
    if os.path.exists("build"):
        import shutil
        shutil.rmtree("build")

    # Build command
    # --noconfirm: overwrite output directory
    # --onefile: package as single exe
    # --windowed: no console window
    # --name: executable name
    # --hidden-import: ensure imports are found (usually auto-detected but good to be safe)
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "mtr加速器",
        "--hidden-import", "PySide6",
        "--hidden-import", "requests",
        "main.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    
    print("\nBuild completed successfully!")
    print(f"Executable is located at: {os.path.abspath('dist/mtr加速器.exe')}")

if __name__ == "__main__":
    install_pyinstaller()
    build()
