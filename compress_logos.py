import os
from PIL import Image

base_dir = r"e:\gyro-puupet-dsu-mouse"
logo_dir = os.path.join(base_dir, "logo", "logo-animation-v1")

files_to_compress = [
    "no-sensors-greyed.png",
    "logo-raise-hands.png",
    "v1-1.png",
    "v2-2.png",
    "v3-3.png"
]

for f in files_to_compress:
    path = os.path.join(logo_dir, f)
    if os.path.exists(path):
        img = Image.open(path)
        # Resize to max 256x256 while preserving aspect ratio
        img.thumbnail((256, 256), Image.Resampling.LANCZOS)
        img.save(path, optimize=True)
        print(f"Compressed {f}")
