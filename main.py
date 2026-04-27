import sys
import time
import threading
from config_manager import load_config
from motion_engine import MotionEngine
from dsu_protocol import DSUServer
from ui_shell import GyroPuppetUI


import ctypes
MOUSEEVENTF_MOVE = 0x0001
_HAS_WIN32 = True

PUL = ctypes.POINTER(ctypes.c_ulong)
class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]
class Input_I(ctypes.Union):
    _fields_ = [("mi", MouseInput)]
class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

def inject_mouse(dx, dy):
    ii_ = Input_I()
    ii_.mi = MouseInput(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
    x = Input(ctypes.c_ulong(0), ii_) # 0 = INPUT_MOUSE
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

# vgamepad for Xbox Right Stick emulation
try:
    import vgamepad as vg
    _HAS_VGAMEPAD = True
except ImportError:
    _HAS_VGAMEPAD = False


def _emulation_loop(app, motion_engine):
    """Unified high-frequency loop (~120 Hz) for Mouse and Xbox Right Stick emulation.

    Runs in a daemon thread. Checks the UI mode selector and the global
    pause state each tick to decide what action to take.
    """
    gamepad = None
    if _HAS_VGAMEPAD:
        try:
            gamepad = vg.VX360Gamepad()
            print("Virtual Xbox 360 controller created.")
        except Exception as e:
            print(f"vgamepad init failed: {e}")
            gamepad = None

    INTERVAL = 1.0 / 120  # ≈8.3 ms → 120 Hz

    while True:
        try:
            mode = app.get_mode()
            paused = getattr(app, 'gyro_paused', False)

            if paused:
                # While paused, zero-out gamepad stick to avoid stuck drift
                if gamepad is not None:
                    try:
                        gamepad.right_joystick(x_value=0, y_value=0)
                        gamepad.update()
                    except Exception:
                        pass
                time.sleep(INTERVAL)
                continue

            if mode == "Mouse Emulation" and _HAS_WIN32:
                dx, dy = motion_engine.get_mouse_delta()
                if dx or dy:
                    inject_mouse(dx, dy)

            elif mode == "Xbox Right Stick" and gamepad is not None:
                rx, ry = motion_engine.get_xbox_delta()
                gamepad.right_joystick(x_value=rx, y_value=ry)
                gamepad.update()

        except Exception:
            pass

        time.sleep(INTERVAL)


def main():
    print("Initializing Configuration...")
    load_config()

    print("Starting Motion Engine...")
    motion_engine = MotionEngine()
    motion_engine.start()

    print("Initializing DSU Server...")
    dsu_server = DSUServer(motion_engine)
    from config_manager import config
    if config.get("enable_dsu", True):
        if dsu_server.start():
            print("DSU Server successfully started.")
        else:
            print("Failed to start DSU Server.")
    else:
        print("DSU Server disabled by config.")

    print("System status:")
    print("  Sensors initialized:", motion_engine.sensors_ready())
    print("  DSU server bound:", dsu_server.is_bound())

    print("Initializing User Interface...")
    app = GyroPuppetUI(motion_engine, dsu_server)

    if "--minimized" in sys.argv:
        app.hide_window()

    # Start unified emulation daemon thread
    emu_thread = threading.Thread(
        target=_emulation_loop,
        args=(app, motion_engine),
        daemon=True,
    )
    emu_thread.start()

    app.mainloop()

    print("\nStopping...")
    dsu_server.stop()
    motion_engine.stop()

if __name__ == "__main__":
    main()
