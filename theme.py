import os
import sys
import customtkinter as ctk

class ThemeConfig:
    # Colors
    BG_MAIN = "#2D2D44"
    PNL_VIS = "#FFF5D6"
    PNL_NET = "#FFD6E0"
    PNL_TUN = "#D6F5D6"
    ACCENT = "#00E5FF"
    TOXIC = "#39FF14"
    HDR_TXT = BG_MAIN  # Updated to match BG_MAIN for cut-out effect
    BORDER = "#000000"

    # Dimensions
    BORDER_WIDTH = 4
    SHADOW_OFFSET = 5
    BTN_HEIGHT = 60
    ICON_SIZE = 24

    TITLE_FMT = ("Silkscreen", 32, "bold")  # Safe fallbacks prior to load
    HDR_FMT = ("Silkscreen", 20, "bold")
    FONT_FMT = ("Courier New", 12, "bold")
    BTN_FMT = ("Courier New", 14, "bold")
    STEP_BTN_FMT = ("Silkscreen", 16, "bold")
    ICON_FMT = ("Arial", 24, "bold")
    BADGE_FONT = ("Press Start 2P", 10)

    @classmethod
    def initialize_fonts(cls, base_dir):
        slk_path = os.path.join(base_dir, "assets", "fonts", "slkscrb.ttf")
        press_path = os.path.join(base_dir, "assets", "fonts", "pressstart2p.ttf")

        if os.path.exists(slk_path):
            ctk.FontManager.load_font(slk_path)
            cls.TITLE_FMT = ("Silkscreen", 32, "bold")
            cls.HDR_FMT = ("Silkscreen", 20, "bold")
            print(f"Loaded {slk_path}")
            
        if os.path.exists(press_path):
            ctk.FontManager.load_font(press_path)
            cls.FONT_FMT = ("Press Start 2P", 12)
            cls.BTN_FMT = ("Press Start 2P", 14)
            print(f"Loaded {press_path}")
