import os
import json
import sys
import winreg

# APP META & CONFIG
APP_NAME    = "GyroPuppet"
APP_VERSION = "v0.1"
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)
CONFIG_PATH = os.path.join(APPDATA_DIR, "config.json")
BASE_DIR    = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = APP_NAME

# XInput button masks for toggle_hotkey binding
XINPUT_BUTTON_NAMES = {
    0x0001: "UP", 0x0002: "DOWN", 0x0004: "LEFT", 0x0008: "RIGHT",
    0x0010: "START", 0x0020: "BACK", 0x0040: "L3", 0x0080: "R3",
    0x0100: "LB", 0x0200: "RB", 0x0400: "GUIDE",
    0x1000: "A", 0x2000: "B", 0x4000: "X", 0x8000: "Y",
}

config = {
    "server_ip": "127.0.0.1", "server_port": 26760,
    "mode": "None",
    "enable_dsu": True,
    "axis_acc_x": "x:1.0", "axis_acc_y": "y:1.0", "axis_acc_z": "z:1.0",
    "inv_acc_x": False, "inv_acc_y": False, "inv_acc_z": False,
    "axis_gyro_pitch": "x:1.0", "axis_gyro_yaw": "y:1.0", "axis_gyro_roll": "z:1.0",
    "inv_gyro_pitch": False, "inv_gyro_yaw": False, "inv_gyro_roll": False,
    "gyro_sensitivity": 1.0, "gyro_deadzone": 0.05, "enable_accel": True,
    "gyro_offset_x": 0.0, "gyro_offset_y": 0.0, "gyro_offset_z": 0.0,
    "run_at_startup": False,
    "toggle_hotkey": 192,  # Default L3+R3 (0x0040 | 0x0080 = 0x00C0 = 192)
}

def _get_exe_path():
    """Return the path to register for startup.
    - Frozen .exe (PyInstaller): use sys.executable directly (the .exe itself).
    - Dev / script mode: use 'python <script>' so it still works during development.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    else:
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        return f'"{sys.executable}" "{script}" --minimized'

def _set_startup_registry(enable: bool):
    """Add or remove the app from the Windows startup registry."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        )
        if enable:
            winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ, _get_exe_path())
        else:
            try:
                winreg.DeleteValue(key, STARTUP_REG_NAME)
            except FileNotFoundError:
                pass  # Already absent, nothing to do
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Failed to update startup registry: {e}")

def load_config():
    global config
    os.makedirs(APPDATA_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f: 
                config.update(json.load(f))
        except Exception: 
            pass

def save_config():
    os.makedirs(APPDATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f: 
        json.dump(config, f, indent=4)
    # Sync the Windows startup registry entry with the saved preference
    _set_startup_registry(config.get("run_at_startup", False))
