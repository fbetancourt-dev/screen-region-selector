#!/usr/bin/env bash
# ==============================================================================
# Screen Region Selector - Solid Borders Demo (High Visibility)
# Author: Francisco Betancourt (@fbetancourt-dev)
# License: MIT
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_IMG="$SCRIPT_DIR/capture_border_demo.png"

BORDER_SIZE=6
COLOR="0.0,0.9,1.0,1.0"
STYLE_NAME="Solid Neon Cyan (6px Bold)"

select_border_style() {
    clear
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "\033[1;32m       🎯 HIGH-VISIBILITY SOLID BORDERS DEMO        \033[0m"
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "Choose a high-visibility border style:\n"
    echo -e "  \033[1;36m1)\033[0m Solid Neon Cyan (6px Bold, 100% Opacity) [Default]"
    echo -e "  \033[1;31m2)\033[0m Solid Snagit Red (6px Bold, High Contrast)"
    echo -e "  \033[1;33m3)\033[0m Solid Electric Yellow (6px Ultra-Bright)"
    echo -e "  \033[1;32m4)\033[0m Solid Lime Green (6px Fluorescent)"
    echo -e "  \033[1;35m5)\033[0m Solid Hot Pink / Magenta (6px Cyberpunk)"
    echo -e "----------------------------------------------------"
    read -rp "Select option [1-5, default '1']: " CHOICE

    case "${CHOICE:-1}" in
        2)
            BORDER_SIZE=6
            COLOR="1.0,0.15,0.15,1.0"
            STYLE_NAME="Solid Snagit Red (6px Bold)"
            ;;
        3)
            BORDER_SIZE=6
            COLOR="1.0,0.95,0.0,1.0"
            STYLE_NAME="Solid Electric Yellow (6px Bold)"
            ;;
        4)
            BORDER_SIZE=6
            COLOR="0.0,1.0,0.3,1.0"
            STYLE_NAME="Solid Lime Green (6px Bold)"
            ;;
        5)
            BORDER_SIZE=6
            COLOR="1.0,0.1,0.8,1.0"
            STYLE_NAME="Solid Hot Pink (6px Bold)"
            ;;
        *)
            BORDER_SIZE=6
            COLOR="0.0,0.9,1.0,1.0"
            STYLE_NAME="Solid Neon Cyan (6px Bold)"
            ;;
    esac

    echo -e "\nSelect border thickness (in pixels):"
    echo -e "  \033[1;37m1)\033[0m Standard (4px)"
    echo -e "  \033[1;37m2)\033[0m Bold (6px) [Default]"
    echo -e "  \033[1;37m3)\033[0m Extra Heavy (10px)"
    read -rp "Select thickness [1-3, default '2']: " THICK_CHOICE

    case "${THICK_CHOICE:-2}" in
        1) BORDER_SIZE=4 ;;
        3) BORDER_SIZE=10 ;;
        *) BORDER_SIZE=6 ;;
    esac
}

select_border_style

while true; do
    clear
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "\033[1;32m       🎯 HIGH-VISIBILITY SOLID BORDERS DEMO        \033[0m"
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "Active Style: \033[1;33m$STYLE_NAME\033[0m (Border: \033[1;37m${BORDER_SIZE}px\033[0m, Color: \033[0;36m$COLOR\033[0m)"
    echo -e "Left-click and drag across any area of your screen."
    echo -e "Press \033[1;31mESC\033[0m or right-click anytime to cancel.\n"
    echo -e "\033[0;37mAwaiting selection...\033[0m\n"

    SELECTION=$(slop -f "%x %y %w %h %g" -b "$BORDER_SIZE" -c "$COLOR" 2>/dev/null || true)

    if [ -z "$SELECTION" ]; then
        echo -e "\033[1;31m[!] Selection cancelled by user.\033[0m\n"
    else
        read -r X Y W H GEO <<< "$SELECTION"
        echo -e "\033[1;32m====================================================\033[0m"
        echo -e "\033[1;32m ✔ REGION SELECTED SUCCESSFULLY:                    \033[0m"
        echo -e "\033[1;32m====================================================\033[0m"
        echo -e "  📍 Origin X (Horizontal) : \033[1;37m${X} px\033[0m"
        echo -e "  📍 Origin Y (Vertical)   : \033[1;37m${Y} px\033[0m"
        echo -e "  📐 Width                 : \033[1;37m${W} px\033[0m"
        echo -e "  📐 Height                : \033[1;37m${H} px\033[0m"
        echo -e "  📦 Geometry              : \033[1;33m${GEO}\033[0m"
        echo -e "----------------------------------------------------"
        echo -e "  JSON Output              :"
        echo -e "  \033[0;36m{\"x\": $X, \"y\": $Y, \"width\": $W, \"height\": $H}\033[0m\n"

        if command -v import &>/dev/null; then
            import -window root -crop "${GEO}" "$OUTPUT_IMG" 2>/dev/null || true
            if [ -f "$OUTPUT_IMG" ]; then
                echo -e "  📸 Cropped image saved to:"
                echo -e "  \033[0;35m$OUTPUT_IMG\033[0m\n"
            fi
        fi
    fi

    echo -e "\033[1;36m----------------------------------------------------\033[0m"
    echo -e "  [y] Try again with current style"
    echo -e "  [c] Change border style / thickness"
    echo -e "  [n] Exit demo"
    read -rp "Select action [y/c/n, default 'y']: " ACTION

    case "${ACTION:-y}" in
        n|N)
            echo -e "\nClosing demo session..."
            sleep 0.5
            break
            ;;
        c|C)
            select_border_style
            ;;
        *)
            continue
            ;;
    esac
done
