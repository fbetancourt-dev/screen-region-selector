#!/usr/bin/env python3
"""
Antigravity Desktop Visibility Manager (Compatibility Wrapper)
Forwards all calls directly to the universal 'app-visibility' engine targeting 'antigravity'.
"""

import sys
import subprocess

def main():
    args = sys.argv[1:]
    if not args:
        subprocess.run(["app-visibility", "--help"])
        return

    action = args[0]
    rest = args[1:]

    # Check if user already specified 'antigravity' in args
    if any(arg in ["antigravity", "antigravity-ide"] for arg in rest):
        cmd = ["app-visibility", action] + rest
    else:
        if action in ["hide", "show", "restore", "toggle"]:
            cmd = ["app-visibility", action, "antigravity"] + rest
        elif action == "status":
            cmd = ["app-visibility", "status", "antigravity"] + rest
        else:
            cmd = ["app-visibility"] + args

    sys.exit(subprocess.run(cmd).returncode)

if __name__ == "__main__":
    main()
