#!/usr/bin/env python3
"""
Antigravity Desktop Visibility Manager
Toggles Antigravity desktop visibility for clean screenshots and recordings.

Supported Components:
- dock     : Ubuntu Dock favorites and active running dot indicator
- tray     : Top bar status indicator (ubuntu-appindicators)
- window   : Active Antigravity window minimization/restoration
- desktop  : Desktop shortcuts on ~/Desktop

Default Behavior:
- 'hide'   : Hides ALL components (dock, tray, desktop) AND minimizes the window.
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

STATE_FILE = os.path.expanduser("~/.config/antigravity_visibility_state.json")
BACKUP_DIR = os.path.expanduser("~/.local/share/antigravity_desktop_icons_backup")
DESKTOP_DIR = os.path.expanduser("~/Desktop")

ALL_COMPONENTS = ["dock", "tray", "window", "desktop"]
ANTIGRAVITY_APP_IDS = ["antigravity.desktop", "antigravity-ide.desktop"]
APPINDICATOR_EXT = "ubuntu-appindicators@ubuntu.com"


# ---------------------------------------------------------------------------
# Low-level GNOME & Window Management Helpers
# ---------------------------------------------------------------------------

def get_dock_favorites() -> list[str]:
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            capture_output=True, text=True, check=True
        )
        return ast.literal_eval(res.stdout.strip())
    except Exception as e:
        print(f"[!] Warning reading dock favorites: {e}", file=sys.stderr)
        return []

def set_dock_favorites(favorites: list[str]):
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

def minimize_antigravity():
    try:
        res = subprocess.run(["desktop-dom", "focused"], capture_output=True, text=True)
        if "antigravity" in res.stdout.lower():
            subprocess.run(["win-action", "combo", "win", "h", "--intent", "Minimize Antigravity for capture"], check=True)
            time.sleep(0.3)
        else:
            subprocess.run(["desktop-dom", "activate", "antigravity"], capture_output=True)
            time.sleep(0.3)
            subprocess.run(["win-action", "combo", "win", "h", "--intent", "Minimize Antigravity for capture"], check=True)
            time.sleep(0.3)
        print("[OK] Antigravity window minimized.")
    except Exception as e:
        print(f"[!] Warning minimizing Antigravity window: {e}", file=sys.stderr)

def restore_antigravity():
    try:
        subprocess.run(["desktop-dom", "activate", "antigravity"], check=True)
        print("[OK] Antigravity window activated and restored to foreground.")
    except Exception as e:
        print(f"[!] Warning activating Antigravity window: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning reading state file: {e}", file=sys.stderr)
    return {
        "hidden_components": [],
        "saved_favorites": [],
        "saved_show_running": True,
        "saved_appindicators_enabled": True,
        "desktop_files": [],
        "hidden_at": None
    }

def save_state(state: dict):
    if not state.get("hidden_components"):
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        return

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Component Resolvers
# ---------------------------------------------------------------------------

def resolve_target_components(action: str, args) -> set[str]:
    """
    Resolves which components to operate on based on --only, --skip, and individual flags.
    Defaults to all components.
    """
    if getattr(args, "only", None):
        targets = set(args.only)
    else:
        targets = set(ALL_COMPONENTS)

    # Exclusions via --skip
    if getattr(args, "skip", None):
        targets -= set(args.skip)

    # Specific convenience flags
    if getattr(args, "no_minimize", False) or getattr(args, "no_window", False):
        targets.discard("window")
    if getattr(args, "no_dock", False):
        targets.discard("dock")
    if getattr(args, "no_tray", False):
        targets.discard("tray")
    if getattr(args, "no_desktop", False):
        targets.discard("desktop")

    return targets


# ---------------------------------------------------------------------------
# Core Operations: Hide, Show, Status
# ---------------------------------------------------------------------------

def hide_components(targets: set[str]):
    state = load_state()
    hidden_comps = set(state.get("hidden_components", []))

    print("----------------------------------------------------")
    print(f" HIDING COMPONENTS: {', '.join(sorted(targets)) if targets else 'None'}")
    print("----------------------------------------------------")

    # 1. Dock
    if "dock" in targets and "dock" not in hidden_comps:
        current_favs = get_dock_favorites()
        state["saved_favorites"] = current_favs
        state["saved_show_running"] = get_dash_show_running()

        filtered_favs = [app for app in current_favs if app not in ANTIGRAVITY_APP_IDS]
        set_dock_favorites(filtered_favs)
        set_dash_show_running(False)
        hidden_comps.add("dock")
        print("[OK] Removed Antigravity icons and suppressed active running indicator in Dock.")

    # 2. Tray
    if "tray" in targets and "tray" not in hidden_comps:
        was_enabled = is_extension_enabled(APPINDICATOR_EXT)
        state["saved_appindicators_enabled"] = was_enabled
        if was_enabled:
            set_extension_state(APPINDICATOR_EXT, False)
        hidden_comps.add("tray")
        print("[OK] Top bar Antigravity tray icon hidden (ubuntu-appindicators disabled).")

    # 3. Desktop Shortcuts
    if "desktop" in targets and "desktop" not in hidden_comps:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        moved_files = state.get("desktop_files", [])
        if os.path.isdir(DESKTOP_DIR):
            for item in os.listdir(DESKTOP_DIR):
                if "antigravity" in item.lower():
                    src = os.path.join(DESKTOP_DIR, item)
                    dst = os.path.join(BACKUP_DIR, item)
                    shutil.move(src, dst)
                    if item not in moved_files:
                        moved_files.append(item)
                    print(f"[OK] Temporarily moved desktop item '{item}' to backup.")
        state["desktop_files"] = moved_files
        hidden_comps.add("desktop")

    # 4. Window Minimization
    if "window" in targets:
        minimize_antigravity()
        hidden_comps.add("window")
    else:
        print("[INFO] Window minimization skipped (--no-minimize / omitted).")

    state["hidden_components"] = list(hidden_comps)
    state["hidden_at"] = time.time()
    save_state(state)
    print("----------------------------------------------------")
    print("[SUCCESS] Specified Antigravity components are now hidden.")


def show_components(targets: set[str] | None = None):
    state = load_state()
    hidden_comps = set(state.get("hidden_components", []))

    # If targets was not explicitly filtered by user flags, restore all currently hidden
    if targets is None:
        targets = set(hidden_comps) if hidden_comps else set(ALL_COMPONENTS)

    print("----------------------------------------------------")
    print(f" RESTORING COMPONENTS: {', '.join(sorted(targets)) if targets else 'None'}")
    print("----------------------------------------------------")

    # 1. Dock
    if "dock" in targets:
        saved_favs = state.get("saved_favorites", [])
        if saved_favs:
            set_dock_favorites(saved_favs)
        else:
            current = get_dock_favorites()
            for app in ANTIGRAVITY_APP_IDS:
                if app not in current:
                    current.append(app)
            set_dock_favorites(current)

        saved_show_running = state.get("saved_show_running", True)
        set_dash_show_running(saved_show_running)
        hidden_comps.discard("dock")
        print("[OK] Restored Ubuntu Dock favorites and running indicator.")

    # 2. Tray
    if "tray" in targets:
        should_enable = state.get("saved_appindicators_enabled", True)
        if should_enable:
            set_extension_state(APPINDICATOR_EXT, True)
        hidden_comps.discard("tray")
        print("[OK] Restored top bar tray icons.")

    # 3. Desktop Shortcuts
    if "desktop" in targets:
        desktop_files = state.get("desktop_files", [])
        for item in desktop_files:
            src = os.path.join(BACKUP_DIR, item)
            dst = os.path.join(DESKTOP_DIR, item)
            if os.path.exists(src):
                shutil.move(src, dst)
                print(f"[OK] Restored desktop item '{item}'.")
        state["desktop_files"] = []
        hidden_comps.discard("desktop")

    # 4. Window Restoration
    if "window" in targets:
        time.sleep(0.2)
        restore_antigravity()
        hidden_comps.discard("window")
    else:
        print("[INFO] Window restoration skipped (--no-window / omitted).")

    state["hidden_components"] = list(hidden_comps)
    save_state(state)

    # Clean up empty backup directory if applicable
    if os.path.exists(BACKUP_DIR) and not os.listdir(BACKUP_DIR):
        try:
            os.rmdir(BACKUP_DIR)
        except Exception:
            pass

    print("----------------------------------------------------")
    if not hidden_comps:
        print("[SUCCESS] All Antigravity components fully restored.")
    else:
        print(f"[INFO] Restored requested components. Still hidden: {', '.join(sorted(hidden_comps))}")


def show_status():
    current_favorites = get_dock_favorites()
    ag_in_dock = [app for app in ANTIGRAVITY_APP_IDS if app in current_favorites]
    show_running = get_dash_show_running()
    appind_enabled = is_extension_enabled(APPINDICATOR_EXT)
    state = load_state()
    hidden_comps = state.get("hidden_components", [])

    print("====================================================")
    print("      ANTIGRAVITY DESKTOP VISIBILITY STATUS         ")
    print("====================================================")
    print(f"Dock Favorites : {'🟢 Visible' if ag_in_dock else '⚪ Hidden'}")
    if ag_in_dock:
        print(f"  └ Icons      : {', '.join(ag_in_dock)}")
    print(f"Running Dots   : {'🟢 Shown (show-running=True)' if show_running else '⚪ Suppressed (show-running=False)'}")
    print(f"Top Bar Tray   : {'🟢 Visible (appindicators=On)' if appind_enabled else '⚪ Hidden (appindicators=Off)'}")
    print(f"Window State   : {'⚪ Minimized / Tracked' if 'window' in hidden_comps else '🟢 Active / Untracked'}")
    print(f"State File     : {'🟢 Active backup: ' + ', '.join(hidden_comps) if hidden_comps else '⚪ Clean (No active hides)'}")
    print("====================================================")


# ---------------------------------------------------------------------------
# CLI Argument Parsing
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
        help=f"Skip specified components from action: {', '.join(ALL_COMPONENTS)}"
    )
    parser.add_argument("--no-dock", action="store_true", help="Do not touch the Ubuntu Dock")
    parser.add_argument("--no-tray", action="store_true", help="Do not touch the top bar tray icon")
    parser.add_argument("--no-desktop", action="store_true", help="Do not touch ~/Desktop shortcuts")

    if is_hide:
        parser.add_argument(
            "--no-minimize", action="store_true",
            help="Do NOT minimize the Antigravity window (default: minimize window)"
        )
        parser.add_argument(
            "--no-window", action="store_true", dest="no_minimize",
            help="Alias for --no-minimize"
        )
    else:
        parser.add_argument(
            "--no-window", action="store_true",
            help="Do NOT restore/activate the Antigravity window (keep current focus)"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Antigravity Desktop Visibility Manager - Clean screen recording & screenshot helper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Hide all components (Dock, Tray, Desktop, and minimize window)
  antigravity-visibility hide

  # Hide everything EXCEPT minimizing the window (keep window visible)
  antigravity-visibility hide --no-minimize

  # Hide only the dock and tray icons
  antigravity-visibility hide --only dock tray

  # Restore all hidden components
  antigravity-visibility restore

  # Restore only the dock, keep tray hidden
  antigravity-visibility restore --only dock

  # Check current status
  antigravity-visibility status
"""
    )

    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # hide subcommand
    parser_hide = subparsers.add_parser("hide", help="Hide Antigravity components (all by default)")
    add_common_filter_args(parser_hide, is_hide=True)

    # show / restore subcommands
    parser_show = subparsers.add_parser("show", help="Restore Antigravity components (all by default)")
    add_common_filter_args(parser_show, is_hide=False)

    parser_restore = subparsers.add_parser("restore", help="Alias for 'show'")
    add_common_filter_args(parser_restore, is_hide=False)

    # toggle subcommand
    parser_toggle = subparsers.add_parser("toggle", help="Toggle visibility based on current state")
    add_common_filter_args(parser_toggle, is_hide=True)

    # status subcommand
    subparsers.add_parser("status", help="Show current visibility and state status")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(0)

    if args.action == "hide":
        targets = resolve_target_components("hide", args)
        hide_components(targets)

    elif args.action in ["show", "restore"]:
        # If user explicitly passed filtering flags, resolve targets; else None (restore all)
        has_filters = any([
            getattr(args, "only", None),
            getattr(args, "skip", None),
            getattr(args, "no_window", False),
            getattr(args, "no_dock", False),
            getattr(args, "no_tray", False),
            getattr(args, "no_desktop", False)
        ])
        targets = resolve_target_components("show", args) if has_filters else None
        show_components(targets)

    elif args.action == "toggle":
        if os.path.exists(STATE_FILE):
            show_components()
        else:
            targets = resolve_target_components("hide", args)
            hide_components(targets)

    elif args.action == "status":
        show_status()


if __name__ == "__main__":
    main()
