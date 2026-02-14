import sys
import os
from typing import Optional

try:
    import winreg
except ImportError:
    winreg = None


def set_windows_autostart(app_name: str, enable: bool, script_path: Optional[str] = None) -> None:
    if winreg is None:
        return
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    if script_path is None:
        # If running as exe (PyInstaller), sys.executable is the path
        if getattr(sys, 'frozen', False):
            script_path = sys.executable
        else:
            # Running as script
            script_path = os.path.abspath(sys.argv[0])
            
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{script_path}"')
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"Failed to set autostart: {e}")
