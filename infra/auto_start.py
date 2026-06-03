import sys
import os
import winreg

APP_NAME = "LinkVault"


def _get_app_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        python_exe = sys.executable
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py')
        return f'"{python_exe}" "{script}"'


def set_auto_start(enabled):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_app_path())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


def is_auto_start_enabled():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False