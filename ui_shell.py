import os
import sys
import ctypes
import threading
import json
import urllib.request
import winsound
import webbrowser
import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont

try:
    from PIL import Image, ImageTk, ImageOps
except ImportError:
    Image, ImageTk, ImageOps = None, None, None

try:
    import pystray
    from pystray import MenuItem
except ImportError:
    pystray = None

from config_manager import config, save_config, XINPUT_BUTTON_NAMES, APP_VERSION
from theme import ThemeConfig

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
ThemeConfig.initialize_fonts(base_dir)

# Colors
BG_MAIN = ThemeConfig.BG_MAIN
PNL_VIS = ThemeConfig.PNL_VIS
PNL_NET = ThemeConfig.PNL_NET
PNL_TUN = ThemeConfig.PNL_TUN
ACCENT  = ThemeConfig.ACCENT
TOXIC   = ThemeConfig.TOXIC
HDR_TXT = ThemeConfig.HDR_TXT
BORDER  = ThemeConfig.BORDER

# Dimensions
BORDER_WIDTH = ThemeConfig.BORDER_WIDTH
SHADOW_OFFSET = ThemeConfig.SHADOW_OFFSET
BTN_HEIGHT = ThemeConfig.BTN_HEIGHT
ICON_SIZE = ThemeConfig.ICON_SIZE

# Typography scaled to fit 720p 3-column correctly
TITLE_FMT = ThemeConfig.TITLE_FMT
HDR_FMT  = ThemeConfig.HDR_FMT
FONT_FMT = ThemeConfig.FONT_FMT
BTN_FMT = ThemeConfig.BTN_FMT
ICON_FMT = ThemeConfig.ICON_FMT
STATUS_FONT = ("Press Start 2P", 8)

class ShadowCard(ctk.CTkFrame):
    def __init__(self, master, fg_color, width=200, btn_h=60, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        
        self.shadow = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0, width=width, height=btn_h)
        self.shadow.grid(row=0, column=0, sticky="nsew", padx=(SHADOW_OFFSET,0), pady=(SHADOW_OFFSET,0))
        
        self.card = ctk.CTkFrame(self, fg_color=fg_color, corner_radius=0, border_width=BORDER_WIDTH, border_color="#000000")
        self.card.grid(row=0, column=0, sticky="nsew", padx=(0,SHADOW_OFFSET), pady=(0,SHADOW_OFFSET))
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

class BlockSwitch(ctk.CTkFrame):
    def __init__(self, master, text, initial_state=False, bg_color="transparent", on_change=None, label_font=None, **kwargs):
        super().__init__(master, fg_color=bg_color, **kwargs)
        self.state = initial_state
        self.on_change = on_change
        
        use_font = label_font if label_font is not None else FONT_FMT
        self.lbl = ctk.CTkLabel(self, text=text, font=use_font, text_color=HDR_TXT)
        self.lbl.pack(side="top", pady=(0, 5))
        
        self.btn = ctk.CTkButton(self, text="ON" if initial_state else "OFF", width=60, height=36, 
                                 corner_radius=0, border_width=BORDER_WIDTH, border_color="#000000", 
                                 font=BTN_FMT,
                                 fg_color=TOXIC if initial_state else ACCENT,
                                 text_color="#000000",
                                 command=self.toggle)
        self.btn.pack(side="top")
        
    def toggle(self):
        self.state = not self.state
        self.btn.configure(text="ON" if self.state else "OFF", 
                           fg_color=ACCENT if self.state else "#888888",
                           text_color="#000000" if self.state else "#FFFFFF")
        if self.on_change:
            self.on_change(self.state)

    def get(self):
        return self.state

class CompactSwitch(ctk.CTkFrame):
    def __init__(self, master, initial_state=False, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.state = initial_state
        self.on_change = on_change
        self.btn = ctk.CTkButton(self, text="ON" if initial_state else "OFF", width=35, height=24, 
                                 corner_radius=0, border_width=2, border_color="#000000", 
                                 font=BTN_FMT,
                                 fg_color=TOXIC if initial_state else ACCENT,
                                 text_color="#000000",
                                 command=self.toggle)
        self.btn.pack()
        
    def toggle(self):
        self.state = not self.state
        self.btn.configure(text="ON" if self.state else "OFF", 
                           fg_color=ACCENT if self.state else "#888888",
                           text_color="#000000" if self.state else "#FFFFFF")
        if self.on_change:
            self.on_change(self.state)

    def get(self):
        return self.state

class BlockSlider(tk.Canvas):
    def __init__(self, master, width=280, height=45, bg_color="#FFFFFF", min_val=0.0, max_val=1.0, initial=0.5, on_change=None):
        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial
        self.num_blocks = 12
        self.on_change = on_change
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Configure>", self._on_configure)
        self.draw()
        
    def draw(self):
        self.delete("all")
        w = self.winfo_width() if self.winfo_width() > 1 else int(self["width"])
        h = self.winfo_height() if self.winfo_height() > 1 else int(self["height"])
        
        block_w = (w - 30) / self.num_blocks
        
        pct = (self.value - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        filled_count = int(pct * self.num_blocks)

        for i in range(self.num_blocks):
            x1 = 15 + i * block_w + 3
            y1 = h/2 - 8
            x2 = 15 + (i+1) * block_w - 3
            y2 = h/2 + 8
            fill_color = ACCENT if i < filled_count else "#888888"
            self.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="black", width=2)

        cx = 15 + pct * (w - 30)
        self.create_rectangle(cx - 15, h/2 - 15, cx + 15, h/2 + 15, fill=ACCENT, outline="black", width=4)
        
    def _update_val(self, event):
        w = self.winfo_width()
        x = max(15, min(event.x, w - 15))
        pct = (x - 15) / (w - 30)
        self.value = round(self.min_val + pct * (self.max_val - self.min_val), 2)
        self.draw()
        if self.on_change:
            self.on_change(self.value)
        
    def _on_click(self, event):
        self._update_val(event)
        
    def _on_drag(self, event):
        self._update_val(event)
        
    def _on_configure(self, event):
        self.draw()
        
    def get(self):
        return self.value
        
    def set(self, val):
        self.value = max(self.min_val, min(val, self.max_val))
        self.draw()
        if self.on_change:
            self.on_change(self.value)

class GyroPuppetUI(ctk.CTk):
    def __init__(self, motion_engine, dsu_server):
        super().__init__()
        self.motion_engine = motion_engine
        self.dsu_server = dsu_server
        
        self.title("GyroPuppet")
        self.geometry("1280x720")  # Ensure app fits MSI Claw resolution
        self.resizable(True, True)  # Allow resizing and the maximize button
        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.configure(fg_color=BG_MAIN)
        self.base_dir = base_dir
        
        # Global pause state (toggled by hotkey)
        self.gyro_paused = False
        
        self._setup_window_icon()
        self.build_ui()
        self.build_visualizer()
        
        # Start motion update thread
        self.vis_roll = 0.0
        self.vis_pitch = 0.0
        self.vis_yaw = 0.0
        self.after(50, self.update_visualizer)
        
        # Start global hotkey listener
        self._start_hotkey_listener()

        # Escape key cancels any active hotkey binding
        self.bind("<Escape>", self._cancel_bind)
        
        self._anim_index = 0
        self.after(400, self._animate_logo)
        
        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _setup_window_icon(self):
        try:
            img_path = os.path.join(base_dir, "assets", "icons", "GyroPuppet-Logo.ico")
            if os.path.exists(img_path):
                self.iconbitmap(img_path)
        except Exception as e:
            print("Failed to load icon:", e)

    def _create_shadow_btn(self, parent, text, command, fg_color=ACCENT, icon_char="", width=280, height=None):
        btn_h = height if height is not None else BTN_HEIGHT
        wrapper = ctk.CTkFrame(parent, fg_color="transparent", width=width+SHADOW_OFFSET, height=btn_h+SHADOW_OFFSET)
        wrapper.grid_propagate(False)
        
        shadow = ctk.CTkFrame(wrapper, fg_color="#000000", corner_radius=0, width=width, height=btn_h)
        shadow.grid(row=0, column=0, sticky="nsew", padx=(SHADOW_OFFSET,0), pady=(SHADOW_OFFSET,0))
        
        btn = ctk.CTkFrame(wrapper, width=width, height=btn_h, fg_color=fg_color, 
                           corner_radius=0, border_width=BORDER_WIDTH, border_color="#000000")
        btn.grid(row=0, column=0, sticky="nsew", padx=(0,SHADOW_OFFSET), pady=(0,SHADOW_OFFSET))
        btn.pack_propagate(False)
        btn.grid_propagate(False)
        wrapper.columnconfigure(0, weight=1)
        wrapper.rowconfigure(0, weight=1)
        
        content_f = ctk.CTkFrame(btn, fg_color="transparent")
        content_f.place(relx=0.5, rely=0.5, anchor="center")
        
        if icon_char:
            lbl_icon = ctk.CTkLabel(content_f, text=icon_char, font=ICON_FMT, text_color="#000000")
            lbl_icon.pack(side="left", padx=(0, 10))
            
        lbl_text = ctk.CTkLabel(content_f, text=text, font=BTN_FMT, text_color="#000000")
        lbl_text.pack(side="left")
        
        btn.lbl_text = lbl_text
        
        def on_press(e):
            btn.grid_configure(padx=(2,SHADOW_OFFSET-2), pady=(2,SHADOW_OFFSET-2))
        def on_release(e):
            btn.grid_configure(padx=(0,SHADOW_OFFSET), pady=(0,SHADOW_OFFSET))
            if command: command()
            
        def on_enter(e):
            btn.configure(fg_color=TOXIC)
        def on_leave(e):
            btn.configure(fg_color=fg_color)
            btn.grid_configure(padx=(0,SHADOW_OFFSET), pady=(0,SHADOW_OFFSET))

        for w in [btn, content_f, lbl_text] + ([lbl_icon] if icon_char else []):
            w.bind("<ButtonPress-1>", on_press)
            w.bind("<ButtonRelease-1>", on_release)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            
        return wrapper, btn

    def _create_step_button(self, parent, symbol, command):
        return ctk.CTkButton(
            parent,
            text=symbol,
            width=32,
            height=32,
            corner_radius=0,
            border_width=2,
            border_color="#000000",
            fg_color=ACCENT,
            hover_color=TOXIC,
            text_color="#000000",
            font=ThemeConfig.STEP_BTN_FMT,
            command=command
        )

    def _step_slider(self, slider, delta):
        value = round(slider.get() + delta, 3)
        slider.set(value)

    def _open_support(self):
        webbrowser.open("https://ko-fi.com/halim1410")

    def build_ui(self):
        
        # Header — 100px locked, no propagation
        self.header_frame = ctk.CTkFrame(self, height=100, corner_radius=0, fg_color=BG_MAIN)
        self.header_frame.pack(side="top", fill="x", pady=0)
        self.header_frame.pack_propagate(False)
        self.header_frame.grid_propagate(False)
        self.header_frame.columnconfigure((0, 1, 2), weight=1)
        self.header_frame.rowconfigure(0, weight=1)

        self.left_header = ctk.CTkFrame(self.header_frame, fg_color=BG_MAIN, corner_radius=0)
        self.left_header.grid(row=0, column=0, sticky="w", padx=15, pady=0)

        self.logo_lbl = ctk.CTkLabel(self.left_header, text="", fg_color="transparent")
        self.tk_support_icon = None
        try:
            self.tk_support_icon = ctk.CTkImage(light_image=Image.open(os.path.join(self.base_dir, "assets", "images", "SUPPORT-DEV.png")), size=(80, 80))
            no_sensor_path = os.path.join(self.base_dir, "assets", "animations", "logo-v1", "no-sensors-greyed.png")
            if Image and os.path.exists(no_sensor_path):
                ns_img = Image.open(no_sensor_path).convert("RGBA")
                self.tk_logo_grey = ctk.CTkImage(light_image=ns_img, dark_image=ns_img, size=(96, 96))
            else:
                self.tk_logo_grey = None
                
            idle_path = os.path.join(self.base_dir, "assets", "animations", "logo-v1", "logo-raise-hands.png")
            if Image and os.path.exists(idle_path):
                idle_img = Image.open(idle_path).convert("RGBA")
                self.tk_logo_idle = ctk.CTkImage(light_image=idle_img, dark_image=idle_img, size=(96, 96))
            else:
                self.tk_logo_idle = None

            v1_path = os.path.join(self.base_dir, "assets", "animations", "logo-v1", "v1-1.png")
            v2_path = os.path.join(self.base_dir, "assets", "animations", "logo-v1", "v2-2.png")
            v3_path = os.path.join(self.base_dir, "assets", "animations", "logo-v1", "v3-3.png")
            
            if Image and os.path.exists(v1_path) and os.path.exists(v2_path) and os.path.exists(v3_path):
                v1_tk = ctk.CTkImage(light_image=Image.open(v1_path).convert("RGBA"), size=(96, 96))
                v2_tk = ctk.CTkImage(light_image=Image.open(v2_path).convert("RGBA"), size=(96, 96))
                v3_tk = ctk.CTkImage(light_image=Image.open(v3_path).convert("RGBA"), size=(96, 96))
                self.tk_active_frames = [v1_tk, v2_tk, v3_tk, v2_tk]
            else:
                self.tk_active_frames = []
        except Exception as e:
            print("Logo load error:", e)
            self.tk_logo_grey = None
            self.tk_logo_idle = None
            self.tk_active_frames = []
            
        if self.tk_logo_grey:
            self.logo_lbl.configure(image=self.tk_logo_grey)
        else:
            self.logo_lbl.configure(text="[LOGO]", font=TITLE_FMT, text_color="#FFF")
            
        self.logo_lbl.pack(side="left", anchor="center")

        self.ver_label = ctk.CTkLabel(self.left_header, text=f" {APP_VERSION}", font=("Press Start 2P", 8), text_color="#888888")
        self.ver_label.pack(side="left", anchor="center")

        self.status_frame = ctk.CTkFrame(self.left_header, fg_color=BG_MAIN, corner_radius=0)
        self.status_frame.pack(side="left", padx=(15, 0), pady=(12, 0), anchor="center")

        self.status_canvas = tk.Canvas(self.status_frame, width=62, height=20, bg=BG_MAIN, highlightthickness=0)
        self.status_canvas.pack()
        self.status_bars = [
            self.status_canvas.create_rectangle(6 + i * 18, 2, 16 + i * 18, 18, fill="#FF0000", outline="black")
            for i in range(3)
        ]
        self.status_label = ctk.CTkLabel(self.status_frame, text="[ LINK ERROR ]", font=STATUS_FONT, text_color="#FFFFFF")
        self.status_label.pack(pady=0)

        self.title_frame = ctk.CTkFrame(self.header_frame, fg_color=BG_MAIN, corner_radius=0)
        self.title_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.title_left = ctk.CTkLabel(self.title_frame, text="GYRO", font=TITLE_FMT, text_color="#00AC9F")
        self.title_right = ctk.CTkLabel(self.title_frame, text="PUPPET", font=TITLE_FMT, text_color="#008060")
        self.title_left.pack(side="left", pady=0)
        self.title_right.pack(side="left", pady=0)

        self.right_header = ctk.CTkFrame(self.header_frame, fg_color=BG_MAIN, corner_radius=0)
        self.right_header.grid(row=0, column=2, sticky="e", padx=15, pady=0)
        
        self.support_container = ctk.CTkFrame(self.right_header, fg_color="transparent", cursor="hand2")
        self.support_img = ctk.CTkLabel(self.support_container, image=self.tk_support_icon, text="")
        self.support_txt = ctk.CTkLabel(self.support_container, text="SUPPORT DEV", font=("Press Start 2P", 8), text_color=ThemeConfig.TOXIC)

        self.support_img.pack(side="left", pady=0)
        self.support_txt.pack(side="left", padx=(8, 0))
        self.support_container.pack(padx=(0, 15), pady=10)

        def _on_enter(e):
            self.support_txt.configure(text_color="#FFFFFF")
        def _on_leave(e):
            self.support_txt.configure(text_color=ThemeConfig.TOXIC)
        def _on_click(e):
            self._open_support()

        for w in (self.support_container, self.support_img, self.support_txt):
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)
            w.bind("<Button-1>", _on_click)

        # Main Body — zero top gap, minimal bottom gap
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.pack(side="top", fill="both", expand=True, padx=15, pady=(15, 12))
        
        self.main_frame.columnconfigure((0, 1, 2), weight=1, uniform="col")
        self.main_frame.rowconfigure(0, weight=1)
        
        # --- Column 0 (Left - Network) ---
        self.col_net = ShadowCard(self.main_frame, fg_color=PNL_NET)
        self.col_net.grid(row=0, column=0, sticky="nsew", padx=10)
        
        ctk.CTkLabel(self.col_net.card, text="Network & Config", font=HDR_FMT, text_color=HDR_TXT).pack(pady=(6, 15))
        
        # ── Mode Selector ──
        mode_row = ctk.CTkFrame(self.col_net.card, fg_color="transparent")
        mode_row.pack(fill="x", padx=30, pady=(10, 10))
        ctk.CTkLabel(mode_row, text="Mode", font=FONT_FMT, text_color=HDR_TXT).pack(side="left")
        self.mode_var = tk.StringVar(value=config.get("mode", "None"))
        self.mode_menu = ctk.CTkOptionMenu(
            mode_row,
            variable=self.mode_var,
            values=["None", "Mouse Emulation", "Xbox Right Stick"],
            width=170,
            height=32,
            corner_radius=0,
            fg_color="#FFFFFF",
            text_color="#000000",
            button_color=ACCENT,
            button_hover_color=TOXIC,
            dropdown_fg_color="#FFFFFF",
            font=FONT_FMT,
            dropdown_font=FONT_FMT,
            command=self._on_mode_change,
        )
        self.mode_menu.pack(side="right")

        # ── Hotkey Toggle Row (Click-to-Bind) ──
        self.is_binding = False
        self._binding_buttons = 0  # bitmask of currently held buttons during binding
        hotkey_row = ctk.CTkFrame(self.col_net.card, fg_color="transparent")
        hotkey_row.pack(fill="x", padx=30, pady=(10, 10))
        ctk.CTkLabel(hotkey_row, text="Hotkey Toggle", font=FONT_FMT, text_color=HDR_TXT).pack(side="left")

        self.hotkey_display = ctk.CTkLabel(
            hotkey_row,
            text=self._hotkey_display_text(),
            font=FONT_FMT,
            text_color="#00AC9F",
        )
        self.hotkey_display.pack(side="right")

        self.hotkey_set_btn = ctk.CTkButton(
            hotkey_row,
            text="SET",
            width=42,
            height=24,
            corner_radius=0,
            border_width=2,
            border_color="#000000",
            fg_color=ACCENT,
            hover_color=TOXIC,
            text_color="#000000",
            font=("Courier New", 10, "bold"),
            command=self._begin_hotkey_bind,
        )
        self.hotkey_set_btn.pack(side="right", padx=(0, 6))

        # ── Independent DSU Server Toggle ──
        def _toggle_dsu(val):
            config["enable_dsu"] = val
            if val:
                self.dsu_server.start()
                self.ip_entry.configure(state="normal")
                self.port_entry.configure(state="normal")
            else:
                self.dsu_server.stop()
                self.ip_entry.configure(state="disabled")
                self.port_entry.configure(state="disabled")

        self.dsu_switch = BlockSwitch(
            self.col_net.card,
            text="Enable DSU Server",
            initial_state=config.get("enable_dsu", True),
            bg_color=PNL_NET,
            on_change=_toggle_dsu,
            label_font=FONT_FMT
        )
        self.dsu_switch.pack(pady=(5, 5), padx=15, anchor="center")

        self.ip_entry = ctk.CTkEntry(self.col_net.card, placeholder_text="IP Address", font=FONT_FMT, height=42, corner_radius=0, border_width=BORDER_WIDTH, border_color=BORDER, text_color=HDR_TXT, fg_color="#FFFFFF")
        self.ip_entry.insert(0, config.get("server_ip", "127.0.0.1"))
        self.ip_entry.pack(pady=(10, 5), fill="x", padx=30)
        
        self.port_entry = ctk.CTkEntry(self.col_net.card, placeholder_text="Port", font=FONT_FMT, height=42, corner_radius=0, border_width=BORDER_WIDTH, border_color=BORDER, text_color=HDR_TXT, fg_color="#FFFFFF")
        self.port_entry.insert(0, str(config.get("server_port", 26760)))
        self.port_entry.pack(pady=(3, 5), fill="x", padx=30)

        # Sync IP/Port field state with DSU toggle on boot
        if not config.get("enable_dsu", True):
            self.ip_entry.configure(state="disabled")
            self.port_entry.configure(state="disabled")
        
        # Flexible spacer — distributes gap between text fields and switches
        ctk.CTkFrame(self.col_net.card, fg_color="transparent", width=1, height=1).pack(expand=True)
        
        # Live config toggle fix
        def _toggle_accel(val):
            config["enable_accel"] = val
            
        self.accel_switch = BlockSwitch(self.col_net.card, text="Enable Accelerometer", 
                                        initial_state=config.get("enable_accel", True), bg_color=PNL_NET,
                                        on_change=_toggle_accel, label_font=FONT_FMT)
        self.accel_switch.pack(pady=(5, 5), padx=15, anchor="center")
        
        self.startup_switch = BlockSwitch(
            self.col_net.card,
            text="Run at Startup",
            initial_state=config.get("run_at_startup", False),
            bg_color=PNL_NET,
            on_change=lambda v: config.__setitem__("run_at_startup", v),
            label_font=FONT_FMT
        )
        self.startup_switch.pack(pady=(2, 8), padx=15, anchor="center")
        
        # Spacer — absorbs leftover space; no fill to prevent border bleed
        ctk.CTkFrame(self.col_net.card, fg_color="transparent", width=1, height=1).pack(expand=True)
        
        # --- Column 1 (Middle - Visualizer) ---
        self.col_vis = ShadowCard(self.main_frame, fg_color=PNL_VIS)
        self.col_vis.grid(row=0, column=1, sticky="nsew", padx=10)
        
        ctk.CTkLabel(self.col_vis.card, text="Real-time Visualizer", font=HDR_FMT, text_color=HDR_TXT).pack(pady=(6, 15))
        
        # Stage centering via pack
        # 300x300 bounding box keeping aspects sharp and proportional
        self.canvas_bounds = ctk.CTkFrame(self.col_vis.card, fg_color="transparent")
        self.canvas_bounds.pack(expand=True, fill="both", padx=8, pady=(4, 8))
        
        self.canvas = tk.Canvas(self.canvas_bounds, width=300, height=300, bg="#E0E0E0", highlightthickness=BORDER_WIDTH, highlightbackground=BORDER)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        
        self.reset_wrapper, self.btn_reset = self._create_shadow_btn(self.col_vis.card, "Reset Visualizer", self.reset_visualizer, icon_char="↺", width=300, height=50)
        self.reset_wrapper.pack(pady=(8, 4), padx=(20, 20), anchor="center")
        
        self.cal_wrapper, self.btn_calibrate = self._create_shadow_btn(self.col_vis.card, "Calibrate Drift", self.calibrate_drift, icon_char="⊕", width=300, height=50)
        self.cal_wrapper.pack(pady=(4, 10), padx=(20, 20), anchor="center")
        
        # --- Column 2 (Right - Tuning) ---
        self.col_tune = ShadowCard(self.main_frame, fg_color=PNL_TUN)
        self.col_tune.grid(row=0, column=2, sticky="nsew", padx=10)
        
        ctk.CTkLabel(self.col_tune.card, text="Advanced Tuning", font=HDR_FMT, text_color=HDR_TXT).pack(pady=(6, 15))
        
        sens_row = ctk.CTkFrame(self.col_tune.card, fg_color="transparent")
        sens_row.pack(fill="x", padx=20, pady=(1, 0))
        ctk.CTkLabel(sens_row, text="Sensitivity", font=FONT_FMT, text_color=HDR_TXT).pack(side="left")
        self.lbl_sens_val = ctk.CTkLabel(sens_row, text=f"{config.get('gyro_sensitivity', 1.0):.2f}x", font=FONT_FMT, text_color=HDR_TXT)
        self.lbl_sens_val.pack(side="right")
        self.sens_control = ctk.CTkFrame(self.col_tune.card, fg_color="transparent")
        self.sens_control.pack(pady=(0, 1), fill="x", padx=20)
        self.sens_control.columnconfigure(0, minsize=40)
        self.sens_control.columnconfigure(1, weight=1)
        self.sens_control.columnconfigure(2, minsize=40)
        self.sens_minus = self._create_step_button(self.sens_control, "-", lambda: self._step_slider(self.sens_slider, -0.01))
        self.sens_minus.grid(row=0, column=0, padx=(0, 2), pady=2, sticky="w")
        self.sens_slider = BlockSlider(self.sens_control, width=220, height=32, bg_color=PNL_TUN, min_val=0.1, max_val=3.0, initial=config.get("gyro_sensitivity", 1.0), on_change=lambda v: self.lbl_sens_val.configure(text=f"{v:.2f}x"))
        self.sens_slider.grid(row=0, column=1, sticky="ew", pady=2)
        self.sens_plus = self._create_step_button(self.sens_control, "+", lambda: self._step_slider(self.sens_slider, 0.01))
        self.sens_plus.grid(row=0, column=2, padx=(2, 0), pady=2, sticky="e")
        
        dead_row = ctk.CTkFrame(self.col_tune.card, fg_color="transparent")
        dead_row.pack(fill="x", padx=20, pady=(1, 0))
        ctk.CTkLabel(dead_row, text="Deadzone", font=FONT_FMT, text_color=HDR_TXT).pack(side="left")
        self.lbl_dead_val = ctk.CTkLabel(dead_row, text=f"{config.get('gyro_deadzone', 0.05):.2f}", font=FONT_FMT, text_color=HDR_TXT)
        self.lbl_dead_val.pack(side="right")
        self.dead_control = ctk.CTkFrame(self.col_tune.card, fg_color="transparent")
        self.dead_control.pack(pady=(0, 1), fill="x", padx=20)
        self.dead_control.columnconfigure(0, minsize=40)
        self.dead_control.columnconfigure(1, weight=1)
        self.dead_control.columnconfigure(2, minsize=40)
        self.dead_minus = self._create_step_button(self.dead_control, "-", lambda: self._step_slider(self.dead_slider, -0.01))
        self.dead_minus.grid(row=0, column=0, padx=(0, 2), pady=2, sticky="w")
        self.dead_slider = BlockSlider(self.dead_control, width=220, height=32, bg_color=PNL_TUN, min_val=0.0, max_val=2.0, initial=config.get("gyro_deadzone", 0.05), on_change=lambda v: self.lbl_dead_val.configure(text=f"{v:.2f}"))
        self.dead_slider.grid(row=0, column=1, sticky="ew", pady=2)
        self.dead_plus = self._create_step_button(self.dead_control, "+", lambda: self._step_slider(self.dead_slider, 0.01))
        self.dead_plus.grid(row=0, column=2, padx=(2, 0), pady=2, sticky="e")
        
        # ── Bottom-up anchoring: pack bottom elements FIRST to prevent clipping ──
        # 1. Save button at the very bottom
        self.save_wrapper, self.btn_save_close = self._create_shadow_btn(self.col_tune.card, "Save & Close", self.apply_and_close, fg_color=ACCENT, width=280, height=44)
        self.save_wrapper.pack(side="bottom", pady=(2, 10), padx=15, anchor="center")
        # 2. Apply button just above it
        self.apply_wrapper, self.btn_apply = self._create_shadow_btn(self.col_tune.card, "Apply Settings", self.apply_live, fg_color=ACCENT, width=280, height=44)
        self.apply_wrapper.pack(side="bottom", pady=(2, 2), padx=15, anchor="center")
        # 3. Debug checkbox above buttons
        self.debug_border_checkbox = ctk.CTkCheckBox(
            self.col_tune.card,
            text="Show Debug Borders",
            font=STATUS_FONT,
            text_color=HDR_TXT,
            fg_color=BG_MAIN,
            corner_radius=0,
            command=self._toggle_debug_borders
        )
        self.debug_border_checkbox.pack(side="bottom", pady=(10, 15), padx=20, anchor="w")

        # Expanding spacer above the grid
        ctk.CTkFrame(self.col_tune.card, fg_color="transparent", width=1, height=1).pack(side="top", expand=True)

        # 4. Tuning Grid — perfectly centered
        self.axes_frame = ctk.CTkFrame(self.col_tune.card, fg_color="transparent")
        self.axes_frame.pack(side="top", pady=(0, 0), fill="x", padx=5)
        
        # Expanding spacer below the grid
        ctk.CTkFrame(self.col_tune.card, fg_color="transparent", width=1, height=1).pack(side="top", expand=True)
        self.axes_frame.columnconfigure((0, 1, 2), weight=1)
        self.axes_frame.rowconfigure((0, 1), weight=1, minsize=65)
        
        self.axes_inputs = {}
        self.axes_frames = {}
        label_pairs = [
            ("↕", "Acc X", "axis_acc_x", "inv_acc_x"), 
            ("↔", "Acc Y", "axis_acc_y", "inv_acc_y"), 
            ("↺", "Acc Z", "axis_acc_z", "inv_acc_z"), 
            ("↕", "Pitch", "axis_gyro_pitch", "inv_gyro_pitch"), 
            ("↔", "Yaw",   "axis_gyro_yaw", "inv_gyro_yaw"), 
            ("↺", "Roll",  "axis_gyro_roll", "inv_gyro_roll")
        ]
        for i, (icon_char, label_txt, ax_key, inv_key) in enumerate(label_pairs):
            # Carved look → slightly darker mint green with thin inset style border
            axis_f = ctk.CTkFrame(self.axes_frame, fg_color="#BEE5BE", corner_radius=0, border_width=2, border_color="#8FBE8F")
            axis_f.grid(row=i//3, column=i%3, padx=3, pady=2, sticky="ew") # 3x2 Matrix, no vertical stretch
            
            # Composite Header — tighter padding
            hdr_f = ctk.CTkFrame(axis_f, fg_color="transparent")
            hdr_f.pack(pady=(4, 0))
            
            ctk.CTkLabel(hdr_f, text=icon_char, font=ICON_FMT, text_color="#000000").pack(side="left")
            ctk.CTkLabel(hdr_f, text=label_txt, font=FONT_FMT, text_color="#000000").pack(side="left", padx=(4, 0))
            
            val = config.get(ax_key, "x:1.0").split(":")[0]
            menu = ctk.CTkOptionMenu(axis_f, values=["x", "y", "z"], width=40, height=22,
                                     corner_radius=0, fg_color="#FFFFFF", text_color="#000000",
                                     button_color="#CCCCCC", dropdown_fg_color="#FFFFFF",
                                     font=("Arial", 11, "bold"), dropdown_font=("Arial", 11, "bold"))
            menu.set(val)
            menu.pack(pady=2)
            
            inv_f = ctk.CTkFrame(axis_f, fg_color="transparent")
            inv_f.pack(pady=(2, 4))
            ctk.CTkLabel(inv_f, text="Inv", font=("Arial", 11, "bold"), text_color="#000000").pack(side="left")
            inv_sw = CompactSwitch(inv_f, initial_state=config.get(inv_key, False))
            inv_sw.pack(side="left")
            
            self.axes_inputs[ax_key] = menu
            self.axes_inputs[inv_key] = inv_sw
            self.axes_frames[ax_key] = axis_f

    def _hotkey_display_text(self):
        """Return a human-readable label for the current hotkey binding."""
        mask = config.get("toggle_hotkey", 0)
        if mask == 0:
            return "[ UNBOUND ]"
        if mask == 9999:
            return "[ KBD DEV ]"
        names = [name for bit, name in sorted(XINPUT_BUTTON_NAMES.items()) if mask & bit]
        return "[ " + "+".join(names) + " ]" if names else "[ UNBOUND ]"

    def _begin_hotkey_bind(self):
        """Enter or cancel binding mode (click-to-cancel toggle)."""
        if self.is_binding:
            # Already binding — abort immediately
            self._cancel_bind()
            return
        self.is_binding = True
        self._binding_buttons = 0
        self.hotkey_set_btn.configure(text="✖")
        self.hotkey_display.configure(text="[ Press key(s) ]", text_color="#FFAA00")
        # Start a background thread to capture the binding
        threading.Thread(target=self._binding_worker, daemon=True).start()

    def _cancel_bind(self, event=None):
        """Abort binding mode and revert UI to last known state."""
        if not self.is_binding:
            return
        self.is_binding = False
        self.hotkey_set_btn.configure(text="SET")
        self.hotkey_display.configure(text=self._hotkey_display_text(), text_color="#00AC9F")

    def _binding_worker(self):
        """Capture all buttons held simultaneously; confirm on full release.
        Falls back to Ctrl key press for dev-mode (keyboard-only) binding.
        Shows [ NO GAMEPAD ] warning if no controller is connected."""
        import ctypes as _ct
        import time as _time

        class XINPUT_GAMEPAD(_ct.Structure):
            _fields_ = [
                ("wButtons", _ct.c_ushort),
                ("bLeftTrigger", _ct.c_ubyte),
                ("bRightTrigger", _ct.c_ubyte),
                ("sThumbLX", _ct.c_short),
                ("sThumbLY", _ct.c_short),
                ("sThumbRX", _ct.c_short),
                ("sThumbRY", _ct.c_short),
            ]

        class XINPUT_STATE(_ct.Structure):
            _fields_ = [
                ("dwPacketNumber", _ct.c_ulong),
                ("Gamepad", XINPUT_GAMEPAD),
            ]

        xinput = None
        for dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                xinput = _ct.windll.LoadLibrary(dll_name + ".dll")
                break
            except OSError:
                continue

        if xinput is None:
            self.after(0, self._show_no_gamepad_warning)
            return

        state = XINPUT_STATE()
        accumulated = 0
        had_press = False
        gaks = _ct.windll.user32.GetAsyncKeyState

        while self.is_binding:
            # Dev-mode fallback: Ctrl key simulates a successful bind
            if gaks(0x11) & 0x8000:  # VK_CONTROL
                self.after(0, self._finish_binding, 9999)
                return

            result = xinput.XInputGetState(0, _ct.byref(state))
            if result != 0:
                # Controller disconnected / not present
                self.after(0, self._show_no_gamepad_warning)
                return

            btns = state.Gamepad.wButtons
            if btns:
                accumulated |= btns
                had_press = True
            elif had_press:
                # All buttons released — binding confirmed
                self.after(0, self._finish_binding, accumulated)
                return

            _time.sleep(0.03)  # ~33 Hz polling during bind

    def _show_no_gamepad_warning(self):
        """Flash a red warning, then revert to normal state after 2 s."""
        self.is_binding = False
        self.hotkey_set_btn.configure(text="SET")
        self.hotkey_display.configure(text="[ NO GAMEPAD ]", text_color="#DF0024")
        self.after(2000, lambda: self.hotkey_display.configure(
            text=self._hotkey_display_text(), text_color="#00AC9F"))

    def _finish_binding(self, mask):
        """Save the captured binding and update UI."""
        self.is_binding = False
        if mask:
            config["toggle_hotkey"] = mask
            save_config()
        self.hotkey_set_btn.configure(text="SET")
        self.hotkey_display.configure(text=self._hotkey_display_text(), text_color="#00AC9F")

    def build_visualizer(self):
        self.grid_rects = []
        for x in range(10, 280, 20):
            for y in range(10, 280, 20):
                rect = self.canvas.create_rectangle(x, y, x+2, y+2, fill="#C2D4E8", outline="")
                self.grid_rects.append(rect)
                
        img_path = os.path.join(self.base_dir, "assets", "images", "PixelArt-3dModel.png")
        if Image and os.path.exists(img_path):
            try:
                # Persistent base source for mathematical rotation cloning
                self.img_source = Image.open(img_path).convert("RGBA")
                self.img_source.thumbnail((240, 240), Image.Resampling.NEAREST)
                self.tk_img = ImageTk.PhotoImage(self.img_source)
                self.img_item = self.canvas.create_image(150, 150, image=self.tk_img, anchor="center")
            except Exception:
                self.canvas.create_text(140, 140, text="[Missing Image]", font=("Courier New", 18, "bold"), fill="black")
        else:
            self.canvas.create_text(140, 140, text="[Missing PIL]", font=("Courier New", 14, "bold"), fill="black")

    def update_visualizer(self):
        try:
            import math
            # Poll engine bindings directly 
            ax, ay, az, pitch, yaw, roll = self.motion_engine.get_motion_state()
            
            # Active Axis Highlighting & Grid Flicker Logic
            deadzone = config.get("gyro_deadzone", 0.05)
            
            motion_str = {
                "axis_acc_x": ax, "axis_acc_y": ay, "axis_acc_z": az,
                "axis_gyro_pitch": pitch, "axis_gyro_yaw": yaw, "axis_gyro_roll": roll
            }
            
            is_active = False
            debug_borders = self.debug_border_checkbox.get() if hasattr(self, 'debug_border_checkbox') else False
            for k, val in motion_str.items():
                if hasattr(self, 'axes_frames') and k in self.axes_frames:
                    if abs(val) > (deadzone * 2.0) and debug_borders:
                        self.axes_frames[k].configure(border_color="#00E5FF", border_width=BORDER_WIDTH)
                        is_active = True
                    else:
                        self.axes_frames[k].configure(border_color="#8FBE8F", border_width=2)
            
            if hasattr(self, 'grid_rects'):
                grid_color = "#FFF5D6" if is_active else "#C2D4E8"
                if not hasattr(self, '_last_grid_color') or self._last_grid_color != grid_color:
                    for r in self.grid_rects:
                        self.canvas.itemconfigure(r, fill=grid_color)
                    self._last_grid_color = grid_color

            # v13 physical Flet equivalent integration mapping strictly over dt=0.05
            self.vis_pitch += pitch * 0.05
            self.vis_yaw   -= yaw * 0.05
            self.vis_roll  -= roll * 0.05
            
            if hasattr(self, 'img_source') and hasattr(self, 'img_item'):
                pr = math.radians(self.vis_pitch)
                yr = math.radians(self.vis_yaw)
                
                # Pseudo-3D Perspective Squish mimicking Flet 3D Rotate natively
                sx = abs(math.cos(yr))
                sy = abs(math.cos(pr))
                
                orig_w, orig_h = self.img_source.size
                nw = max(1, int(orig_w * sx))
                nh = max(1, int(orig_h * sy))
                
                # Resize binds physical rotation boundary natively rendering in perspective bounds
                img = self.img_source.resize((nw, nh), Image.Resampling.BILINEAR)
                rot_img = img.rotate(-self.vis_roll, expand=True, resample=Image.Resampling.BICUBIC)
                
                self.tk_img = ImageTk.PhotoImage(rot_img)
                self.canvas.coords(self.img_item, 150, 150)
                self.canvas.itemconfigure(self.img_item, image=self.tk_img)
        except Exception:
            pass

        self._refresh_link_status()
        self.after(50, self.update_visualizer)

    def _animate_logo(self):
        try:
            status = self.status_label.cget("text")
            if status in ('[ SYSTEM IDLE ]', '[ PAUSED ]'):
                if getattr(self, 'tk_logo_idle', None):
                    self.logo_lbl.configure(image=self.tk_logo_idle)
                self._anim_index = 0
            elif status == '[ LINK ACTIVE ]':
                if getattr(self, 'tk_active_frames', None) and len(self.tk_active_frames) > 0:
                    self.logo_lbl.configure(image=self.tk_active_frames[self._anim_index])
                    self._anim_index = (self._anim_index + 1) % 4
            elif status in ('[ NO SENSOR DETECTED ]', '[ LINK ERROR ]'):
                if getattr(self, 'tk_logo_grey', None):
                    self.logo_lbl.configure(image=self.tk_logo_grey)
                self._anim_index = 0
            else:
                if getattr(self, 'tk_logo_grey', None):
                    self.logo_lbl.configure(image=self.tk_logo_grey)
                self._anim_index = 0
        except Exception:
            pass
        self.after(400, self._animate_logo)

    def _refresh_link_status(self):
        if self.motion_engine.gyrometer is None:
            fill_colors = ['#DF0024', '#DF0024', '#DF0024']
            label_text = '[ NO SENSOR DETECTED ]'
            label_color = '#DF0024'
        elif config.get("enable_dsu") == False and self.get_mode() == "None":
            fill_colors = ['#FFAA00', '#FFAA00', '#FFAA00']
            label_text = '[ SYSTEM IDLE ]'
            label_color = '#FFAA00'
        elif self.gyro_paused:
            fill_colors = ['#FFAA00', '#FFAA00', '#FFAA00']
            label_text = '[ PAUSED ]'
            label_color = '#FFAA00'
        else:
            fill_colors = ['#39FF14', '#39FF14', '#39FF14']
            label_text = '[ LINK ACTIVE ]'
            label_color = '#39FF14'

        for bar, color in zip(self.status_bars, fill_colors):
            self.status_canvas.itemconfigure(bar, fill=color)
        self.status_label.configure(text=label_text, text_color=label_color)

    def _toggle_debug_borders(self):
        # This callback exists to refresh active borders on toggle
        if hasattr(self, 'axes_frames'):
            for axis_f in self.axes_frames.values():
                axis_f.configure(border_color="#8FBE8F", border_width=2)

    def _on_mode_change(self, value):
        """Save mode to config. DSU is independent — no IP/port toggling here."""
        config["mode"] = value
        if value == "Xbox Right Stick":
            self.hotkey_display.configure(text="[ P2 CONFLICT RISK ]", text_color="#FFAA00")
            self.after(2000, lambda: self.hotkey_display.configure(
                text=self._hotkey_display_text(), text_color="#00AC9F"))

    def get_mode(self):
        """Return the currently selected operational mode string."""
        return self.mode_var.get()

    def toggle_gyro_pause(self):
        """Toggle the global gyro pause state (called by hotkey listener)."""
        self.gyro_paused = not self.gyro_paused
        # Auditory feedback via winsound — non-blocking in a thread
        def _beep():
            try:
                if not self.gyro_paused:
                    winsound.Beep(1000, 100)  # ON → high-pitch short beep
                else:
                    winsound.Beep(500, 150)   # OFF → low-pitch short beep
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()

    def _start_hotkey_listener(self):
        """Poll for the user-configured hotkey combo via XInput in a daemon thread.

        Falls back to keyboard Ctrl+Shift+G if no gamepad is detected.
        Uses ctypes to call XInputGetState directly — no extra dependencies.
        """
        import ctypes as _ct

        class XINPUT_GAMEPAD(_ct.Structure):
            _fields_ = [
                ("wButtons", _ct.c_ushort),
                ("bLeftTrigger", _ct.c_ubyte),
                ("bRightTrigger", _ct.c_ubyte),
                ("sThumbLX", _ct.c_short),
                ("sThumbLY", _ct.c_short),
                ("sThumbRX", _ct.c_short),
                ("sThumbRY", _ct.c_short),
            ]

        class XINPUT_STATE(_ct.Structure):
            _fields_ = [
                ("dwPacketNumber", _ct.c_ulong),
                ("Gamepad", XINPUT_GAMEPAD),
            ]

        # Try loading XInput DLLs (newest first)
        xinput = None
        for dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                xinput = _ct.windll.LoadLibrary(dll_name + ".dll")
                break
            except OSError:
                continue

        def _hotkey_worker():
            import time as _time
            was_pressed = False
            state = XINPUT_STATE()

            while True:
                # Skip hotkey detection while in binding mode
                if self.is_binding:
                    _time.sleep(0.05)
                    continue

                pressed = False
                hotkey_mask = config.get("toggle_hotkey", 0)

                if xinput is not None and hotkey_mask:
                    result = xinput.XInputGetState(0, _ct.byref(state))
                    if result == 0:  # ERROR_SUCCESS
                        btns = state.Gamepad.wButtons
                        # All bits in the hotkey mask must be set
                        pressed = (btns & hotkey_mask) == hotkey_mask

                # Fallback: Ctrl+Shift+G via GetAsyncKeyState
                if not pressed:
                    VK_CONTROL = 0x11
                    VK_SHIFT   = 0x10
                    VK_G       = 0x47
                    gaks = _ct.windll.user32.GetAsyncKeyState
                    if (gaks(VK_CONTROL) & 0x8000 and
                        gaks(VK_SHIFT) & 0x8000 and
                        gaks(VK_G) & 0x8000):
                        pressed = True

                # Edge-trigger: toggle only on press transition
                if pressed and not was_pressed:
                    self.after(0, self.toggle_gyro_pause)
                was_pressed = pressed

                _time.sleep(0.05)  # 20 Hz polling

        t = threading.Thread(target=_hotkey_worker, daemon=True)
        t.start()

    def reset_visualizer(self):
        self.vis_roll = 0.0
        self.vis_pitch = 0.0
        self.vis_yaw = 0.0
        self.motion_engine.reset_calibration()

    def calibrate_drift(self):
        if hasattr(self.btn_calibrate, 'lbl_text'):
            self.btn_calibrate.lbl_text.configure(text="Calibrating...")
        self.motion_engine.calibrate()
        # Automatically restore button purely for UI feedback
        self.after(1500, lambda: self.btn_calibrate.lbl_text.configure(text="Calibrate Drift") if hasattr(self.btn_calibrate, 'lbl_text') else None)

    def hide_window(self):
        self.withdraw()
        if not hasattr(self, 'tray_icon') and pystray:
            import threading
            img_path = os.path.join(self.base_dir, "assets", "icons", "GyroPuppet-Logo.ico")
            if os.path.exists(img_path):
                img = Image.open(img_path).convert("RGBA")
            else:
                img = Image.new('RGBA', (64, 64), (0, 0, 0, 255))
            menu = pystray.Menu(
                MenuItem('Restore', self.show_window, default=True),
                MenuItem('Quit', self.quit_app)
            )
            self.tray_icon = pystray.Icon("GyroPuppet", img, "GyroPuppet", menu)
            if hasattr(self.tray_icon, 'on_clicked'):
                self.tray_icon.on_clicked = self._on_tray_click
            elif hasattr(self.tray_icon, 'on_double_click'):
                self.tray_icon.on_double_click = self._on_tray_click
            if hasattr(self.tray_icon, 'run_detached'):
                self.tray_icon.run_detached()
            else:
                threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _do_show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_tray_click(self, icon, item=None):
        self.show_window(icon, item)

    def show_window(self, icon, item):
        icon.stop()
        if hasattr(self, 'tray_icon'):
            delattr(self, 'tray_icon')
        self.after(0, self._do_show)

    def quit_app(self, icon, item):
        icon.stop()
        self.dsu_server.stop()
        self.motion_engine.stop()
        self.quit()

    def _write_ui_config(self):
        config["server_ip"] = self.ip_entry.get()
        config["server_port"] = int(self.port_entry.get())
        config["enable_accel"] = bool(self.accel_switch.get())
        config["run_at_startup"] = bool(self.startup_switch.get())
        config["gyro_sensitivity"] = float(self.sens_slider.get())
        config["gyro_deadzone"] = float(self.dead_slider.get())
        
        for ax_key, comp in self.axes_inputs.items():
            if "inv" in ax_key:
                config[ax_key] = bool(comp.get())
            else:
                config[ax_key] = f"{comp.get()}:1.0"

    def apply_live(self):
        try:
            self._write_ui_config()
            if hasattr(self, 'dsu_server') and self.dsu_server:
                self.dsu_server.update_bind_address(config.get("server_ip", "127.0.0.1"), config.get("server_port", 26760))
        except Exception as e:
            print("Failed to apply live config:", e)

    def apply_and_close(self):
        try:
            self._write_ui_config()
            if hasattr(self, 'dsu_server') and self.dsu_server:
                self.dsu_server.update_bind_address(config.get("server_ip", "127.0.0.1"), config.get("server_port", 26760))
            from config_manager import save_config
            save_config()
        except Exception as e:
            print("Failed to save config:", e)
        
        self.hide_window()

    def _check_for_updates(self):
        try:
            url = "https://api.github.com/repos/halim1410/GyroPuppet/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'GyroPuppet-App'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "")
                release_url = data.get("html_url", "")

                # Simple string comparison (e.g., "v0.1" vs "v0.2.0")
                if latest_version and latest_version != APP_VERSION:
                    # Safely call UI update from the background thread
                    self.after(1000, lambda: self._show_update_popup(latest_version, release_url))
        except Exception as e:
            print(f"Update check failed: {e}")

    def _show_update_popup(self, new_ver, url):
        popup = ctk.CTkToplevel(self)
        popup.title("Update Available")
        popup.geometry("350x150")
        popup.attributes("-topmost", True)
        
        lbl = ctk.CTkLabel(popup, text=f"A new version ({new_ver}) is available!\nYou are currently running {APP_VERSION}.", font=FONT_FMT, text_color=ThemeConfig.HDR_TXT)
        lbl.pack(pady=20)
        
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        btn_dl = ctk.CTkButton(btn_frame, text="Download Update", command=lambda: [webbrowser.open(url), popup.destroy()])
        btn_dl.pack(side="left", padx=10)
        
        btn_dismiss = ctk.CTkButton(btn_frame, text="Dismiss", command=popup.destroy)
        btn_dismiss.pack(side="right", padx=10)
