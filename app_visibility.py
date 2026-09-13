#!/usr/bin/env python3
"""
App Visibility Manager (app-visibility)
Universal CLI tool to hide/restore desktop artifacts for any application on Ubuntu / GNOME.
Designed for clean screen recordings, screenshots, and live presentations.

Supported Components:
- dock     : Ubuntu Dock favorite launcher and active running dot indicator
- tray     : Top bar status indicators (ubuntu-appindicators)
- window   : Application window minimization and restoration
- desktop  : Desktop shortcuts on ~/Desktop

Default Behavior:
- 'hide'   : Hides ALL components (dock, tray, desktop) AND minimizes window(s).
- 'show'   : Restores ALL hidden components and restores window focus.
- Granular : Use --only or --skip/--no-* flags to selectively control components.

Author: Francisco Betancourt (@fbetancourt-dev)
License: MIT
"""

import sys
import os
import ast
import json
import shutil
import subprocess
import argparse
import time
from typing import List, Set, Dict, Any, Optional

STATE_FILE = os.path.expanduser("~/.config/app_visibility_state.json")
LEGACY_STATE_FILE = os.path.expanduser("~/.config/antigravity_visibility_state.json")
BACKUP_BASE_DIR = os.path.expanduser("~/.local/share/app_visibility_backup")
DESKTOP_DIR = os.path.expanduser("~/Desktop")

ALL_COMPONENTS = ["dock", "tray", "window", "desktop"]
APPINDICATOR_EXT = "ubuntu-appindicators@ubuntu.com"

# Known aliases and typical desktop IDs
KNOWN_ALIASES = {
    "antigravity": ["antigravity.desktop", "antigravity-ide.desktop"],
    "vscode": ["code_code.desktop", "code.desktop"],
    "code": ["code_code.desktop", "code.desktop"],
    "spotify": ["spotify_spotify.desktop", "spotify.desktop"],
    "terminal": ["org.gnome.Terminal.desktop", "terminal.desktop"],
    "gnome-terminal": ["org.gnome.Terminal.desktop"],
    "chrome": ["google-chrome.desktop"],
    "google-chrome": ["google-chrome.desktop"],
    "nautilus": ["org.gnome.Nautilus.desktop"],
    "files": ["org.gnome.Nautilus.desktop"],
    "thunderbird": ["thunderbird_thunderbird.desktop"],
    "calc": ["libreoffice-calc.desktop"],
    "writer": ["libreoffice-writer.desktop"],
    "libreoffice": ["libreoffice-writer.desktop", "libreoffice-calc.desktop", "libreoffice-impress.desktop"],
    "settings": ["org.gnome.Settings.desktop"],
}


# ---------------------------------------------------------------------------
# GNOME & Desktop Helpers
# ---------------------------------------------------------------------------

def get_dock_favorites() -> List[str]:
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            capture_output=True, text=True, check=True
        )
        return ast.literal_eval(res.stdout.strip())
    except Exception as e:
        print(f"[!] Warning reading dock favorites: {e}", file=sys.stderr)
        return []

def set_dock_favorites(favorites: List[str]):
    val_str = str(favorites)
    subprocess.run(
        ["gsettings", "set", "org.gnome.shell", "favorite-apps", val_str],
        check=True
    )

def get_dash_show_running() -> bool:
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.shell.extensions.dash-to-dock", "show-running"],
            capture_output=True, text=True, check=True
        )
        return res.stdout.strip().lower() == "true"
    except Exception:
        return True

def set_dash_show_running(enabled: bool):
    try:
        val = "true" if enabled else "false"
        subprocess.run(
            ["gsettings", "set", "org.gnome.shell.extensions.dash-to-dock", "show-running", val],
            check=True
        )
    except Exception as e:
        print(f"[!] Warning setting show-running: {e}", file=sys.stderr)

def is_extension_enabled(ext_id: str) -> bool:
    try:
        res = subprocess.run(["gnome-extensions", "list", "--enabled"], capture_output=True, text=True)
        return ext_id in res.stdout
    except Exception:
        return False

def set_extension_state(ext_id: str, enable: bool):
    action = "enable" if enable else "disable"
    try:
        subprocess.run(["gnome-extensions", action, ext_id], check=True)
    except Exception as e:
        print(f"[!] Warning toggling extension {ext_id}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Application Discovery & Identification
# ---------------------------------------------------------------------------

def resolve_app_desktop_ids(app_query: str, current_favorites: List[str]) -> List[str]:
    """Finds all relevant .desktop IDs in favorites or system dirs for an app."""
    q = app_query.strip().lower()
    matched = set()

    # 1. Check known aliases
    if q in KNOWN_ALIASES:
        for alias_id in KNOWN_ALIASES[q]:
            matched.add(alias_id)

    # 2. Check current dock favorites
    for fav in current_favorites:
        fav_clean = fav.lower().replace(".desktop", "")
        if q == fav_clean or q in fav.lower():
            matched.add(fav)

    # 3. Check standard application directories if not found in favorites
    if not matched:
        app_dirs = [
            "/usr/share/applications",
            "/var/lib/snapd/desktop/applications",
            os.path.expanduser("~/.local/share/applications")
        ]
        for d in app_dirs:
            if os.path.isdir(d):
                for f in os.listdir(d):
                    if f.endswith(".desktop") and q in f.lower():
                        matched.add(f)

    # Fallback to appending .desktop
    if not matched:
        matched.add(f"{q}.desktop")

    return sorted(list(matched))


# ---------------------------------------------------------------------------
# Window Management via desktop-dom and win-action
# ---------------------------------------------------------------------------

def minimize_app_window(app_query: str):
    """Minimizes window(s) matching the app name."""
    try:
        res = subprocess.run(["desktop-dom", "focused"], capture_output=True, text=True)
        if app_query.lower() in res.stdout.lower():
            subprocess.run(["win-action", "combo", "win", "h", "--intent", f"Minimize {app_query} for capture"], check=True)
            time.sleep(0.3)
        else:
            # Activate it to focus, then send win+h
            subprocess.run(["desktop-dom", "activate", app_query], capture_output=True)
            time.sleep(0.3)
            subprocess.run(["win-action", "combo", "win", "h", "--intent", f"Minimize {app_query} for capture"], check=True)
            time.sleep(0.3)
        print(f"[OK] Application '{app_query}' window minimized.")
    except Exception as e:
        print(f"[!] Warning minimizing '{app_query}' window: {e}", file=sys.stderr)

def restore_app_window(app_query: str):
    """Restores/activates window(s) matching the app name."""
    try:
        subprocess.run(["desktop-dom", "activate", app_query], check=True)
        print(f"[OK] Application '{app_query}' activated and brought to foreground.")
    except Exception as e:
        print(f"[!] Warning activating '{app_query}' window: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_master_state() -> Dict[str, Any]:
    # Migrate legacy antigravity state if exists
    if not os.path.exists(STATE_FILE) and os.path.exists(LEGACY_STATE_FILE):
        try:
            with open(LEGACY_STATE_FILE, "r") as f:
                old = json.load(f)
            return {
                "apps": {
                    "antigravity": {
                        "desktop_ids": ["antigravity.desktop", "antigravity-ide.desktop"],
                        "hidden_components": old.get("hidden_components", ALL_COMPONENTS),
                        "saved_favorites": old.get("saved_favorites", []),
                        "saved_show_running": old.get("saved_show_running", True),
                        "saved_appindicators_enabled": old.get("saved_appindicators_enabled", True),
                        "desktop_files": old.get("desktop_files", []),
                        "hidden_at": old.get("hidden_at", time.time())
                    }
                }
            }
        except Exception:
            pass

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning reading state file: {e}", file=sys.stderr)

    return {"apps": {}}

def save_master_state(state: Dict[str, Any]):
    apps = state.get("apps", {})
    # Filter out empty apps
    active_apps = {k: v for k, v in apps.items() if v.get("hidden_components")}
    state["apps"] = active_apps

    if not active_apps:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        if os.path.exists(LEGACY_STATE_FILE):
            os.remove(LEGACY_STATE_FILE)
        return

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Core Operations: Hide, Show, Status
# ---------------------------------------------------------------------------

def hide_single_app(app_name: str, targets: Set[str], master_state: Dict[str, Any]):
    apps = master_state.setdefault("apps", {})
    app_state = apps.setdefault(app_name, {
        "desktop_ids": [],
        "hidden_components": [],
        "saved_favorites": [],
        "saved_show_running": True,
        "saved_appindicators_enabled": True,
        "desktop_files": [],
        "hidden_at": None
    })

    current_favs = get_dock_favorites()
    desktop_ids = resolve_app_desktop_ids(app_name, current_favs)
    app_state["desktop_ids"] = desktop_ids

    hidden_comps = set(app_state.get("hidden_components", []))

    print("-------------------------------------------------------------------")
    print(f" HIDING APP: '{app_name}'")
    print(f" Target Components : {', '.join(sorted(targets)) if targets else 'None'}")
    print(f" Identified IDs    : {', '.join(desktop_ids)}")
    print("-------------------------------------------------------------------")

    # 1. Dock
    if "dock" in targets and "dock" not in hidden_comps:
        if not app_state.get("saved_favorites"):
            app_state["saved_favorites"] = current_favs
        app_state["saved_show_running"] = get_dash_show_running()

        filtered_favs = [f for f in current_favs if f not in desktop_ids]
        set_dock_favorites(filtered_favs)
        set_dash_show_running(False)
        hidden_comps.add("dock")
        print(f"[OK] Removed '{app_name}' icons and suppressed running dot in Dock.")

    # 2. Tray
    if "tray" in targets and "tray" not in hidden_comps:
        was_enabled = is_extension_enabled(APPINDICATOR_EXT)
        app_state["saved_appindicators_enabled"] = was_enabled
        if was_enabled:
            set_extension_state(APPINDICATOR_EXT, False)
        hidden_comps.add("tray")
        print("[OK] Top bar tray icons hidden (ubuntu-appindicators disabled).")

    # 3. Desktop Shortcuts
    if "desktop" in targets and "desktop" not in hidden_comps:
        backup_dir = os.path.join(BACKUP_BASE_DIR, app_name)
        os.makedirs(backup_dir, exist_ok=True)
        moved_files = app_state.get("desktop_files", [])
        if os.path.isdir(DESKTOP_DIR):
            for item in os.listdir(DESKTOP_DIR):
                if app_name.lower() in item.lower():
                    src = os.path.join(DESKTOP_DIR, item)
                    dst = os.path.join(backup_dir, item)
                    shutil.move(src, dst)
                    if item not in moved_files:
                        moved_files.append(item)
                    print(f"[OK] Temporarily moved desktop shortcut '{item}' to backup.")
        app_state["desktop_files"] = moved_files
        hidden_comps.add("desktop")

    # 4. Window Minimization
    if "window" in targets:
        minimize_app_window(app_name)
        hidden_comps.add("window")
    else:
        print(f"[INFO] Window minimization skipped for '{app_name}' (--no-minimize / omitted).")

    app_state["hidden_components"] = list(hidden_comps)
    app_state["hidden_at"] = time.time()


def show_single_app(app_name: str, targets: Optional[Set[str]], master_state: Dict[str, Any]):
    apps = master_state.get("apps", {})
    app_state = apps.get(app_name, {})

    hidden_comps = set(app_state.get("hidden_components", []))
    if targets is None:
        targets = set(hidden_comps) if hidden_comps else set(ALL_COMPONENTS)

    print("-------------------------------------------------------------------")
    print(f" RESTORING APP: '{app_name}'")
    print(f" Restoring Components : {', '.join(sorted(targets)) if targets else 'None'}")
    print("-------------------------------------------------------------------")

    # 1. Dock
    if "dock" in targets:
        saved_favs = app_state.get("saved_favorites", [])
        if saved_favs:
            set_dock_favorites(saved_favs)
        else:
            current = get_dock_favorites()
            desktop_ids = app_state.get("desktop_ids", []) or resolve_app_desktop_ids(app_name, current)
            for d_id in desktop_ids:
                if d_id not in current:
                    current.append(d_id)
            set_dock_favorites(current)

        saved_show_running = app_state.get("saved_show_running", True)
        set_dash_show_running(saved_show_running)
        hidden_comps.discard("dock")
        print(f"[OK] Restored Dock launcher(s) and running indicators for '{app_name}'.")

    # 2. Tray
    if "tray" in targets:
        # Only re-enable tray if NO OTHER app is still requesting tray hidden
        other_apps_need_tray_hidden = any(
            "tray" in other.get("hidden_components", [])
            for k, other in apps.items() if k != app_name
        )
        if not other_apps_need_tray_hidden and app_state.get("saved_appindicators_enabled", True):
            set_extension_state(APPINDICATOR_EXT, True)
            print("[OK] Restored top bar tray icons.")
        hidden_comps.discard("tray")

    # 3. Desktop Shortcuts
    if "desktop" in targets:
        backup_dir = os.path.join(BACKUP_BASE_DIR, app_name)
        desktop_files = app_state.get("desktop_files", [])
        for item in desktop_files:
            src = os.path.join(backup_dir, item)
            dst = os.path.join(DESKTOP_DIR, item)
            if os.path.exists(src):
                shutil.move(src, dst)
                print(f"[OK] Restored desktop shortcut '{item}'.")
        app_state["desktop_files"] = []
        hidden_comps.discard("desktop")
        if os.path.exists(backup_dir) and not os.listdir(backup_dir):
            try:
                os.rmdir(backup_dir)
            except Exception:
                pass

    # 4. Window Restoration
    if "window" in targets:
        time.sleep(0.2)
        restore_app_window(app_name)
        hidden_comps.discard("window")
    else:
        print(f"[INFO] Window restoration skipped for '{app_name}' (--no-window / omitted).")

    app_state["hidden_components"] = list(hidden_comps)


def show_global_status(app_filter: Optional[str] = None):
    master_state = load_master_state()
    apps = master_state.get("apps", {})
    current_favorites = get_dock_favorites()
    show_running = get_dash_show_running()
    appind_enabled = is_extension_enabled(APPINDICATOR_EXT)

    print("===================================================================")
    print("               APPLICATION VISIBILITY STATUS                       ")
    print("===================================================================")
    print(f"Running Dots   : {'🟢 Shown (show-running=True)' if show_running else '⚪ Suppressed (show-running=False)'}")
    print(f"Top Bar Tray   : {'🟢 Visible (appindicators=On)' if appind_enabled else '⚪ Hidden (appindicators=Off)'}")
    print(f"Active Backup  : {STATE_FILE if os.path.exists(STATE_FILE) else '⚪ Clean (No active hides)'}")
    print("-------------------------------------------------------------------")

    apps_to_inspect = [app_filter] if app_filter else (list(apps.keys()) if apps else ["antigravity", "code", "spotify", "terminal"])

    for app in apps_to_inspect:
        desktop_ids = resolve_app_desktop_ids(app, current_favorites)
        present_in_dock = [d for d in desktop_ids if d in current_favorites]
        app_state = apps.get(app, {})
        hidden_comps = app_state.get("hidden_components", [])

        status_str = "🟢 Normal / Visible" if not hidden_comps else f"⚪ Partially/Fully Hidden: {', '.join(hidden_comps)}"
        print(f"App: {app.upper()}")
        print(f"  ├ State        : {status_str}")
        print(f"  ├ Dock Icons   : {', '.join(present_in_dock) if present_in_dock else '⚪ None in favorites'}")
        print(f"  └ Window State : {'⚪ Minimized / Tracked' if 'window' in hidden_comps else '🟢 Active / Untracked'}")

    print("===================================================================")


# ---------------------------------------------------------------------------
# CLI Argument Parsing & Dispatch
# ---------------------------------------------------------------------------

def add_common_filter_args(parser, is_hide: bool):
    parser.add_argument(
        "--only", nargs="+", choices=ALL_COMPONENTS,
        metavar="COMP",
        help=f"Target ONLY specified components: {', '.join(ALL_COMPONENTS)}"
    )
    parser.add_argument(
        "--skip", nargs="+", choices=ALL_COMPONENTS,
        metavar="COMP",
        help=f"Skip specified components: {', '.join(ALL_COMPONENTS)}"
    )
    parser.add_argument("--no-dock", action="store_true", help="Do not touch the Ubuntu Dock")
    parser.add_argument("--no-tray", action="store_true", help="Do not touch the top bar tray icon")
    parser.add_argument("--no-desktop", action="store_true", help="Do not touch ~/Desktop shortcuts")

    if is_hide:
        parser.add_argument(
            "--no-minimize", action="store_true",
            help="Do NOT minimize window(s) (default: minimize window)"
        )
        parser.add_argument(
            "--no-window", action="store_true", dest="no_minimize",
            help="Alias for --no-minimize"
        )
    else:
        parser.add_argument(
            "--no-window", action="store_true",
            help="Do NOT restore/activate window(s) (keep current focus)"
        )


def resolve_target_components(args, is_hide: bool) -> Set[str]:
    if getattr(args, "only", None):
        targets = set(args.only)
    else:
        targets = set(ALL_COMPONENTS)

    if getattr(args, "skip", None):
        targets -= set(args.skip)

    if getattr(args, "no_minimize", False) or getattr(args, "no_window", False):
        targets.discard("window")
    if getattr(args, "no_dock", False):
        targets.discard("dock")
    if getattr(args, "no_tray", False):
        targets.discard("tray")
    if getattr(args, "no_desktop", False):
        targets.discard("desktop")

    return targets


def main():
    parser = argparse.ArgumentParser(
        prog="app-visibility",
        description="Universal Application Visibility Manager for Ubuntu / GNOME desktop.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Hide Antigravity completely (default app if none specified)
  app-visibility hide

  # Hide Spotify (Dock, Tray, Desktop, and minimize window)
  app-visibility hide spotify

  # Hide VS Code without minimizing its window
  app-visibility hide code --no-minimize

  # Hide multiple apps at once
  app-visibility hide spotify code terminal

  # Hide only the dock icon for Spotify
  app-visibility hide spotify --only dock

  # Restore Spotify
  app-visibility restore spotify

  # Restore ALL currently hidden apps
  app-visibility restore

  # Check visibility status of all tracked apps
  app-visibility status
"""
    )

    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # hide subcommand
    parser_hide = subparsers.add_parser("hide", help="Hide application desktop artifacts")
    parser_hide.add_argument("apps", nargs="*", default=[], help="App name(s) to hide (default: antigravity)")
    add_common_filter_args(parser_hide, is_hide=True)

    # show / restore subcommands
    parser_show = subparsers.add_parser("show", help="Restore application desktop artifacts")
    parser_show.add_argument("apps", nargs="*", default=[], help="App name(s) to restore (default: all hidden)")
    add_common_filter_args(parser_show, is_hide=False)

    parser_restore = subparsers.add_parser("restore", help="Alias for 'show'")
    parser_restore.add_argument("apps", nargs="*", default=[], help="App name(s) to restore (default: all hidden)")
    add_common_filter_args(parser_restore, is_hide=False)

    # toggle subcommand
    parser_toggle = subparsers.add_parser("toggle", help="Toggle application visibility")
    parser_toggle.add_argument("apps", nargs="*", default=[], help="App name(s) to toggle (default: antigravity)")
    add_common_filter_args(parser_toggle, is_hide=True)

    # status subcommand
    parser_status = subparsers.add_parser("status", help="Show visibility status")
    parser_status.add_argument("app", nargs="?", default=None, help="Optional app name to inspect")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(0)

    master_state = load_master_state()

    if args.action == "hide":
        apps = args.apps if args.apps else ["antigravity"]
        targets = resolve_target_components(args, is_hide=True)
        for app in apps:
            hide_single_app(app, targets, master_state)
        save_master_state(master_state)
        print("-------------------------------------------------------------------")
        print(f"[SUCCESS] Specified components for {', '.join(apps)} are now hidden.")

    elif args.action in ["show", "restore"]:
        has_filters = any([
            getattr(args, "only", None),
            getattr(args, "skip", None),
            getattr(args, "no_window", False),
            getattr(args, "no_dock", False),
            getattr(args, "no_tray", False),
            getattr(args, "no_desktop", False)
        ])
        targets = resolve_target_components(args, is_hide=False) if has_filters else None

        active_hidden_apps = list(master_state.get("apps", {}).keys())
        apps_to_restore = args.apps if args.apps else (active_hidden_apps if active_hidden_apps else ["antigravity"])

        for app in apps_to_restore:
            show_single_app(app, targets, master_state)

        save_master_state(master_state)
        print("-------------------------------------------------------------------")
        print(f"[SUCCESS] Restore operation completed for {', '.join(apps_to_restore)}.")

    elif args.action == "toggle":
        apps = args.apps if args.apps else ["antigravity"]
        targets = resolve_target_components(args, is_hide=True)
        active_apps = master_state.get("apps", {})

        for app in apps:
            if app in active_apps and active_apps[app].get("hidden_components"):
                show_single_app(app, None, master_state)
            else:
                hide_single_app(app, targets, master_state)

        save_master_state(master_state)

    elif args.action == "status":
        show_global_status(args.app)


if __name__ == "__main__":
    main()
