import os
import json
import winreg
import sys

class SettingsManager:
    def __init__(self, settings_file="settings.json"):
        # Put settings file in the outer root client dir
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.settings_file = os.path.join(base_dir, settings_file)
        self.default_settings = {
            "start_with_windows": False, 
            "start_minimized": False,
            "mute_notifications": False,
            "bandwidth_limit_kbps": 0.0,
            "debounce_time": 3.0, 
            "theme": "Dark"
        }

    def load(self):
        if not os.path.exists(self.settings_file):
            return self.default_settings.copy()
        
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
                settings = self.default_settings.copy()
                settings.update(data)
                return settings
        except Exception:
            return self.default_settings.copy()

    def save(self, settings):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"[SettingsManager] Failed to save settings: {e}")

    def toggle_startup(self, enable: bool):
        KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME = "CloudSaveClient"

        if getattr(sys, 'frozen', False):
            # PyInstaller exe
            cmd = f'"{sys.executable}"'
        else:
            # Python script
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
            cmd = f'"{sys.executable}" "{script_path}"'
        
        try:
            # Open key for setting/deleting values
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY_PATH, 0, winreg.KEY_SET_VALUE)
        except Exception as e:
            print(f"[SettingsManager] Failed to open registry key: {e}")
            return

        try:
            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                print("[SettingsManager] Enabled startup with Windows.")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("[SettingsManager] Disabled startup with Windows.")
                except FileNotFoundError:
                    # Key doesn't exist, which is fine
                    pass
        except Exception as e:
            print(f"[SettingsManager] Failed to toggle startup: {e}")
        finally:
            winreg.CloseKey(key)
