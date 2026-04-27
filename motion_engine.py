from winrt.windows.devices.sensors import Gyrometer, Accelerometer
from config_manager import config

class MotionEngine:
    # XInput full-deflection reference: ±250 °/s maps to ±32767
    XBOX_MAX_DPS = 250.0
    XBOX_STICK_MAX = 32767
    # Exponential Moving Average smoothing factor (0 = no smoothing, 1 = instant)
    SMOOTH_ALPHA = 0.3

    def __init__(self):
        self.gyrometer = None
        self.accelerometer = None
        self._sensors_ready = False
        # EMA state for Xbox stick smoothing
        self._smooth_yaw = 0.0
        self._smooth_pitch = 0.0
        # Fractional accumulators for precise mouse movement
        self._mouse_residue_x = 0.0
        self._mouse_residue_y = 0.0

    def start(self):
        self.gyrometer = Gyrometer.get_default()
        self.accelerometer = Accelerometer.get_default()
        self._sensors_ready = bool(self.gyrometer and self.accelerometer)

    def sensors_ready(self):
        return bool(self.gyrometer and self.accelerometer)

    def stop(self):
        self.gyrometer = None
        self.accelerometer = None

    def calibrate(self):
        import time
        import threading
        from config_manager import save_config
        
        def _cal_worker():
            if not self.gyrometer: return
            x_s, y_s, z_s = [], [], []
            for _ in range(50):
                r = self.gyrometer.get_current_reading()
                if r:
                    x_s.append(r.angular_velocity_x)
                    y_s.append(r.angular_velocity_y)
                    z_s.append(r.angular_velocity_z)
                time.sleep(0.02)
                
            if x_s:
                config["gyro_offset_x"] = sum(x_s) / len(x_s)
                config["gyro_offset_y"] = sum(y_s) / len(y_s)
                config["gyro_offset_z"] = sum(z_s) / len(z_s)
                save_config()
                
        threading.Thread(target=_cal_worker, daemon=True).start()

    def reset_calibration(self):
        from config_manager import save_config
        config["gyro_offset_x"] = 0.0
        config["gyro_offset_y"] = 0.0
        config["gyro_offset_z"] = 0.0
        save_config()

    def _gv(self, r, ms, is_g, inv):
        try:
            ax, m = ms.split(":")
            m = float(m) * (-1 if inv else 1)
            v = getattr(r, f"{'angular_velocity' if is_g else 'acceleration'}_{ax.lower()}")
            if is_g:
                v -= config.get(f"gyro_offset_{ax.lower()}", 0.0)
                if abs(v) < config["gyro_deadzone"]: 
                    v = 0.0
                m *= config["gyro_sensitivity"]
            return v * m
        except Exception: 
            return 0.0

    def get_mouse_delta(self):
        """Convert raw gyro angular velocity into pixel-shift deltas for mouse emulation.

        Returns (dx, dy) as integers.  Yaw → horizontal, Pitch → vertical.
        Deadzone and sensitivity from config are applied before conversion.
        """
        gr = self.gyrometer.get_current_reading() if self.gyrometer else None
        if gr is None:
            return 0, 0

        deadzone = config.get("gyro_deadzone", 0.05)
        sensitivity = config.get("gyro_sensitivity", 1.0)

        # Raw angular velocity (degrees/s) — use the mapped axes & inversion
        yaw   = self._gv(gr, config["axis_gyro_yaw"],   True, config["inv_gyro_yaw"])
        pitch = self._gv(gr, config["axis_gyro_pitch"], True, config["inv_gyro_pitch"])

        # Base scaling factor to balance 120Hz polling rate and 3D engine raw input translation
        base_scale = 2.0
        
        # Accumulate fractional movements
        self._mouse_residue_x += (yaw * base_scale)
        self._mouse_residue_y += (-pitch * base_scale)  # pitch up → cursor up (negative Y)
        
        # Extract integer delta
        dx = int(self._mouse_residue_x)
        dy = int(self._mouse_residue_y)
        
        # Keep the exact fraction left over for the next tick
        self._mouse_residue_x -= dx
        self._mouse_residue_y -= dy

        return dx, dy

    def get_xbox_delta(self):
        """Convert gyro angular velocity into XInput right-stick axes.

        Returns (rx, ry) as integers in the range -32768..32767.
        Yaw → Right Stick X, Pitch → Right Stick Y.
        A light EMA (Exponential Moving Average) is applied to reduce jitter.
        """
        gr = self.gyrometer.get_current_reading() if self.gyrometer else None
        if gr is None:
            self._smooth_yaw = 0.0
            self._smooth_pitch = 0.0
            return 0, 0

        yaw   = self._gv(gr, config["axis_gyro_yaw"],   True, config["inv_gyro_yaw"])
        pitch = self._gv(gr, config["axis_gyro_pitch"], True, config["inv_gyro_pitch"])

        # EMA smoothing to eliminate jitter
        self._smooth_yaw   = self.SMOOTH_ALPHA * yaw   + (1.0 - self.SMOOTH_ALPHA) * self._smooth_yaw
        self._smooth_pitch = self.SMOOTH_ALPHA * pitch + (1.0 - self.SMOOTH_ALPHA) * self._smooth_pitch

        # Normalize: XBOX_MAX_DPS °/s (after sensitivity) → full stick deflection
        rx = int(max(-self.XBOX_STICK_MAX, min(self.XBOX_STICK_MAX,
                     (self._smooth_yaw / self.XBOX_MAX_DPS) * self.XBOX_STICK_MAX)))
        ry = int(max(-self.XBOX_STICK_MAX, min(self.XBOX_STICK_MAX,
                     (-self._smooth_pitch / self.XBOX_MAX_DPS) * self.XBOX_STICK_MAX)))

        return rx, ry

    def get_motion_state(self):
        gr = self.gyrometer.get_current_reading() if self.gyrometer else None
        ar = self.accelerometer.get_current_reading() if self.accelerometer else None

        if config["enable_accel"] and ar:
            ax = self._gv(ar, config["axis_acc_x"], False, config["inv_acc_x"])
            ay = self._gv(ar, config["axis_acc_y"], False, config["inv_acc_y"])
            az = self._gv(ar, config["axis_acc_z"], False, config["inv_acc_z"])
        else: 
            ax, ay, az = 0.0, 1.0, 0.0

        gp = self._gv(gr, config["axis_gyro_pitch"], True, config["inv_gyro_pitch"]) if gr else 0.0
        gy = self._gv(gr, config["axis_gyro_yaw"],   True, config["inv_gyro_yaw"])   if gr else 0.0
        grl= self._gv(gr, config["axis_gyro_roll"],  True, config["inv_gyro_roll"])  if gr else 0.0

        return ax, ay, az, gp, gy, grl
