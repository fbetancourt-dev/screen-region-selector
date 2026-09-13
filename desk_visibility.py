#!/usr/bin/env python3
"""
Desktop Visibility Manager (desk-visibility)
Toggles visibility of all desktop icons, folders, files, and links on Ubuntu / GNOME.
Leverages the native Desktop Icons NG (DING) subsystem without moving or altering files.

Usage:
  desk-visibility hide       - Instantly hides all desktop icons, folders, and files
  desk-visibility show       - Instantly restores all desktop icons, folders, and files
  desk-visibility restore    - Alias for 'show'
  desk-visibility toggle     - Toggles between visible and hidden
  desk-visibility status     - Displays current desktop icon layer status

Author: Francisco Betancourt (@fbetancourt-dev)
License: MIT
"""

import sys
import os
import subprocess
import argparse
from typing import List, Dict, Any, Optional

DESKTOP_EXTENSIONS = [
    "ding@rastersoft.com",          # Desktop Icons NG (Ubuntu 20.04+)
    "desktop-icons@csoriano"        # Classic GNOME Desktop Icons
]

DESKTOP_DIR = os.path.expanduser("~/Desktop")
DING_SCHEMA = "org.gnome.shell.extensions.ding"


def get_installed_desktop_extensions() -> List[str]:
    """Finds which desktop icon extension is installed on this system."""
    try:
        res = subprocess.run(["gnome-extensions", "list"], capture_output=True, text=True, check=True)
        all_exts = res.stdout.splitlines()
        return [ext for ext in DESKTOP_EXTENSIONS if ext in all_exts]
    except Exception:
        return []


def is_extension_enabled(ext_id: str) -> bool:
    try:
        res = subprocess.run(["gnome-extensions", "list", "--enabled"], capture_output=True, text=True, check=True)
        return ext_id in res.stdout
    except Exception:
        return False


def set_extension_state(ext_id: str, enable: bool) -> bool:
    action = "enable" if enable else "disable"
    try:
        subprocess.run(["gnome-extensions", action, ext_id], check=True)
        return True
    except Exception as e:
        print(f"[!] Error setting extension '{ext_id}' to {action}: {e}", file=sys.stderr)
        return False


def get_desktop_items_summary() -> List[Dict[str, str]]:
    items = []
    if os.path.isdir(DESKTOP_DIR):
        for name in sorted(os.listdir(DESKTOP_DIR)):
            path = os.path.join(DESKTOP_DIR, name)
            kind = "Folder" if os.path.isdir(path) else ("Launcher" if name.endswith(".desktop") else "File")
            items.append({"name": name, "type": kind})
    return items


def hide_desktop():
    exts = get_installed_desktop_extensions()
    if not exts:
        print("[!] No supported desktop icons extension found (ding@rastersoft.com).", file=sys.stderr)
        sys.exit(1)

    changed = False
    for ext in exts:
        if is_extension_enabled(ext):
            if set_extension_state(ext, False):
                changed = True

    items = get_desktop_items_summary()
    print("-------------------------------------------------------------------")
    print("                 DESKTOP VISIBILITY: HIDDEN                        ")
    print("-------------------------------------------------------------------")
    print(f"[OK] Desktop icon layer disabled via GNOME extension.")
    print(f"[OK] {len(items)} items on ~/Desktop are now completely hidden from view.")
    print("-------------------------------------------------------------------")


def show_desktop():
    exts = get_installed_desktop_extensions()
    if not exts:
        print("[!] No supported desktop icons extension found (ding@rastersoft.com).", file=sys.stderr)
        sys.exit(1)

    for ext in exts:
        set_extension_state(ext, True)

    items = get_desktop_items_summary()
    print("-------------------------------------------------------------------")
    print("                DESKTOP VISIBILITY: VISIBLE                        ")
    print("-------------------------------------------------------------------")
    print(f"[OK] Desktop icon layer enabled via GNOME extension.")
    print(f"[OK] Restored {len(items)} desktop items to view.")
    print("-------------------------------------------------------------------")


def toggle_desktop():
    exts = get_installed_desktop_extensions()
    if not exts:
        print("[!] No supported desktop icons extension found.", file=sys.stderr)
        sys.exit(1)

    primary_ext = exts[0]
    if is_extension_enabled(primary_ext):
        hide_desktop()
    else:
        show_desktop()


def show_status():
    exts = get_installed_desktop_extensions()
    primary_ext = exts[0] if exts else "None"
    enabled = is_extension_enabled(primary_ext) if exts else False
    items = get_desktop_items_summary()

    # Read system icon flags if schema exists
    show_home = None
    show_trash = None
    try:
        res_home = subprocess.run(["gsettings", "get", DING_SCHEMA, "show-home"], capture_output=True, text=True)
        if res_home.returncode == 0:
            show_home = res_home.stdout.strip() == "true"
        res_trash = subprocess.run(["gsettings", "get", DING_SCHEMA, "show-trash"], capture_output=True, text=True)
        if res_trash.returncode == 0:
            show_trash = res_trash.stdout.strip() == "true"
    except Exception:
        pass

    print("===================================================================")
    print("                    DESKTOP VISIBILITY STATUS                      ")
    print("===================================================================")
    print(f"Desktop Icon Layer : {'🟢 Visible (Enabled)' if enabled else '⚪ Hidden (Disabled)'}")
    print(f"Active Extension   : {primary_ext}")
    if show_home is not None:
        print(f"Home Folder Icon   : {'🟢 Shown' if show_home else '⚪ Hidden'}")
    if show_trash is not None:
        print(f"Trash Can Icon     : {'🟢 Shown' if show_trash else '⚪ Hidden'}")
    print("-------------------------------------------------------------------")
    print(f"Desktop Directory  : {DESKTOP_DIR} ({len(items)} items)")
    for it in items[:10]:
        print(f"  ├ [{it['type']}] {it['name']}")
    if len(items) > 10:
        print(f"  └ ... and {len(items) - 10} more item(s)")
    print("===================================================================")


def main():
    parser = argparse.ArgumentParser(
        prog="desk-visibility",
        description="Desktop Visibility Manager - Instant clean desktop for recordings and screenshots.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Hide all desktop icons, folders, and files
  desk-visibility hide

  # Show all desktop icons, folders, and files
  desk-visibility show

  # Toggle between hidden and visible
  desk-visibility toggle

  # Check current desktop status
  desk-visibility status
"""
    )

    parser.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["hide", "show", "restore", "toggle", "status"],
        help="Action to perform (default: status)"
    )

    args = parser.parse_args()

    if args.action == "hide":
        hide_desktop()
    elif args.action in ["show", "restore"]:
        show_desktop()
    elif args.action == "toggle":
        toggle_desktop()
    elif args.action == "status":
        show_status()


if __name__ == "__main__":
    main()
