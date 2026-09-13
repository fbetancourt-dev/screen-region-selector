#!/usr/bin/env python3
"""
Python Wrapper for slop / slurp / snagit_selector
Author: Francisco Betancourt (@fbetancourt-dev)
License: MIT
"""

from __future__ import annotations
import json
import subprocess
import shutil
from typing import TypedDict, Optional

class Region(TypedDict):
    x: int
    y: int
    width: int
    height: int
    geometry: str

def select_region_slop(
    mode: str = "tint",
    color: str = "0.0,0.7,1.0,0.35",
    border_size: int = 6
) -> Optional[Region]:
    """
    Selects a screen region using slop.
    :param mode: 'tint' (shaded box via -l) or 'border' (outline box via -b)
    :param color: RGBA color string (e.g. '0.0,0.7,1.0,0.35')
    :param border_size: thickness in pixels (used in 'border' mode)
    :return: Region dict or None if cancelled
    """
    if not shutil.which("slop"):
        raise FileNotFoundError("slop binary not found. Install via 'sudo apt install slop'.")

    cmd = ["slop", "-f", "%x %y %w %h %g"]
    if mode == "tint":
        cmd.extend(["-l", "-c", color])
    else:
        cmd.extend(["-b", str(border_size), "-c", color])

    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip()
    if not out or proc.returncode != 0:
        return None

    parts = out.split()
    if len(parts) < 5:
        return None

    return {
        "x": int(parts[0]),
        "y": int(parts[1]),
        "width": int(parts[2]),
        "height": int(parts[3]),
        "geometry": parts[4]
    }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Interactive Screen Region Picker")
    parser.add_argument("--mode", choices=["tint", "border"], default="tint", help="Selection style")
    parser.add_argument("--color", default="0.0,0.7,1.0,0.35", help="RGBA color (e.g. 0.0,0.7,1.0,0.35)")
    parser.add_argument("--border", type=int, default=6, help="Border width in pixels")
    args = parser.parse_args()

    region = select_region_slop(mode=args.mode, color=args.color, border_size=args.border)
    if region:
        print(json.dumps(region, indent=2))
    else:
        print("Selection cancelled.", file=sys.stderr)
        sys.exit(1)
