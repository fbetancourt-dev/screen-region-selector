#!/usr/bin/env bash
# ==============================================================================
# Screen Region Selector - Snagit-Style Shaded Tints Demo
# Author: Francisco Betancourt (@fbetancourt-dev)
# License: MIT
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_IMG="$SCRIPT_DIR/capture_tint_demo.png"

CURRENT_TINT_NAME="Classic Cyan (Sky Blue)"
COLOR_RGB="0.0,0.7,1.0"
OPACITY="0.35"
CURRENT_RGBA="${COLOR_RGB},${OPACITY}"

select_tint_palette() {
    clear
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "\033[1;32m      🎨 SNAGIT SHADED TINT GALLERY (PALETTE)       \033[0m"
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "Choose your preferred shading tint:\n"
    echo -e "  \033[1;36m1)\033[0m Classic Cyan (Sky Blue)        - \033[0;36mSnagit & macOS Default\033[0m"
    echo -e "  \033[1;35m2)\033[0m Electric Violet (Cyberpunk)    - \033[0;35mHigh Contrast\033[0m"
    echo -e "  \033[1;33m3)\033[0m Neon Amber (Golden Warmth)     - \033[0;33mBest for Dark Editors\033[0m"
    echo -e "  \033[1;32m4)\033[0m Emerald Green (Matrix)         - \033[0;32mCrisp Tech Look\033[0m"
    echo -e "  \033[1;31m5)\033[0m Crimson Coral (Snagit Red)     - \033[0;31mAttention Grabber\033[0m"
    echo -e "  \033[1;37m6)\033[0m Frost Charcoal (Dark Smoke)    - \033[0;37mSubtle Minimalist\033[0m"
    echo -e "  \033[1;34m7)\033[0m Custom RGB Input               - \033[0;34mDefine your own\033[0m"
    echo -e "----------------------------------------------------"
    read -rp "Select tint [1-7, default '1']: " TINT_CHOICE

    case "${TINT_CHOICE:-1}" in
        2)
            COLOR_RGB="0.7,0.2,1.0"
            CURRENT_TINT_NAME="Electric Violet"
            ;;
        3)
            COLOR_RGB="1.0,0.6,0.0"
            CURRENT_TINT_NAME="Neon Amber"
            ;;
        4)
            COLOR_RGB="0.0,0.9,0.3"
            CURRENT_TINT_NAME="Emerald Green"
            ;;
        5)
            COLOR_RGB="1.0,0.2,0.3"
            CURRENT_TINT_NAME="Crimson Coral"
            ;;
        6)
            COLOR_RGB="0.08,0.08,0.12"
            CURRENT_TINT_NAME="Frost Charcoal"
            ;;
        7)
            echo -e "\nEnter RGB values between 0.0 and 1.0 (e.g. 0.5,0.8,0.2):"
            read -rp "RGB: " CUSTOM_RGB
            COLOR_RGB="${CUSTOM_RGB:-0.0,0.7,1.0}"
            CURRENT_TINT_NAME="Custom RGB ($COLOR_RGB)"
            ;;
        *)
            COLOR_RGB="0.0,0.7,1.0"
            CURRENT_TINT_NAME="Classic Cyan"
            ;;
    esac

    echo -e "\nSelect opacity level:"
    echo -e "  \033[1;37m1)\033[0m Soft (20% Opacity)     - Very light tint"
    echo -e "  \033[1;37m2)\033[0m Balanced (35% Opacity) - Standard Snagit style [Default]"
    echo -e "  \033[1;37m3)\033[0m Bold (50% Opacity)     - Heavy visible shading"
    read -rp "Select opacity [1-3, default '2']: " OP_CHOICE

    case "${OP_CHOICE:-2}" in
        1) OPACITY="0.20" ;;
        3) OPACITY="0.50" ;;
        *) OPACITY="0.35" ;;
    esac

    CURRENT_RGBA="${COLOR_RGB},${OPACITY}"
}

select_tint_palette

while true; do
    clear
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "\033[1;32m      🎯 SNAGIT SHADED REGION SELECTOR DEMO         \033[0m"
    echo -e "\033[1;36m====================================================\033[0m"
    echo -e "Active Tint: \033[1;33m$CURRENT_TINT_NAME\033[0m (RGBA: \033[0;36m$CURRENT_RGBA\033[0m)"
    echo -e "Left-click and drag across any screen area."
    echo -e "Press \033[1;31mESC\033[0m or right-click anytime to cancel.\n"
    echo -e "\033[0;37mAwaiting selection...\033[0m\n"

    SELECTION=$(slop -f "%x %y %w %h %g" -l -c "$CURRENT_RGBA" 2>/dev/null || true)

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
    echo -e "  [y] Try again with this tint"
    echo -e "  [c] Choose another tint / opacity"
    echo -e "  [n] Exit demo"
    read -rp "Select action [y/c/n, default 'y']: " ACTION

    case "${ACTION:-y}" in
        n|N)
            echo -e "\nClosing demo session..."
            sleep 0.5
            break
            ;;
        c|C)
            select_tint_palette
            ;;
        *)
            continue
            ;;
    esac
done
