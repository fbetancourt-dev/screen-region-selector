#!/usr/bin/env python3
"""
Automated Clean Desktop Showcase Capture
1. Hides Antigravity window and dock icons via antigravity-visibility hide
2. Captures clean desktop screenshots showcasing the demos
3. Generates high-resolution showcase graphics
4. Automatically restores Antigravity window and dock icons via antigravity-visibility restore
"""

import subprocess
import time
import os
import shutil
from PIL import Image, ImageDraw, ImageFont

REPO_DIR = "/home/fbetancourt/Gemini/screen-region-selector"
ASSETS_DIR = os.path.join(REPO_DIR, "assets")
ARTIFACTS_DIR = "/home/fbetancourt/.gemini/antigravity/brain/8d1924d8-7703-4405-92b0-61ee50632507"

def run_showcase():
    print("[1/5] Hiding Antigravity window and Dock icons...")
    subprocess.run(["antigravity-visibility", "hide"], check=True)
    time.sleep(1.2)

    try:
        raw_screen_path = os.path.join(ASSETS_DIR, "clean_desktop_raw.png")
        print("[2/5] Capturing clean desktop without Antigravity...")
        subprocess.run(["gnome-screenshot", "-f", raw_screen_path], check=True)
        time.sleep(0.5)

        print("[3/5] Generating showcase demonstration graphic on clean desktop...")
        img = Image.open(raw_screen_path).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw a gorgeous Snagit Cyan region selection on the desktop
        sel_box = (320, 240, 1280, 820)
        # Soft blue tint fill
        draw.rectangle(sel_box, fill=(0, 180, 255, 80), outline=(0, 229, 255, 255), width=4)

        # Draw dimension badge near bottom-right of box
        badge_w, badge_h = 160, 36
        bx1, by1 = sel_box[2] - badge_w, sel_box[3] + 10
        draw.rectangle((bx1, by1, bx1 + badge_w, by1 + badge_h), fill=(15, 20, 30, 240), outline=(0, 229, 255, 255), width=2)
        draw.text((bx1 + 18, by1 + 10), "960 x 580 px", fill=(0, 229, 255, 255))

        # Draw Snagit Red comparison box
        red_box = (1360, 240, 1850, 600)
        draw.rectangle(red_box, outline=(255, 50, 50, 255), width=5)
        rx1, ry1 = red_box[0], red_box[1] - 34
        draw.rectangle((rx1, ry1, rx1 + 220, ry1 + 30), fill=(15, 20, 30, 240), outline=(255, 50, 50, 255), width=1)
        draw.text((rx1 + 12, ry1 + 8), "Solid 5px Border Mode", fill=(255, 80, 80, 255))

        final = Image.alpha_composite(img, overlay).convert("RGB")
        showcase_out = os.path.join(ASSETS_DIR, "clean_showcase_snagit.png")
        final.save(showcase_out)

        # Copy to artifacts directory
        artifact_showcase = os.path.join(ARTIFACTS_DIR, "clean_showcase_snagit.png")
        shutil.copyfile(showcase_out, artifact_showcase)
        print(f"[4/5] Clean showcase saved to: {showcase_out}")

    finally:
        print("[5/5] Restoring Antigravity window and original Dock icons...")
        time.sleep(0.5)
        subprocess.run(["antigravity-visibility", "restore"], check=True)
        print("[OK] Restore complete.")

if __name__ == "__main__":
    run_showcase()
