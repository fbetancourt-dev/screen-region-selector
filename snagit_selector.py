#!/usr/bin/env python3
"""
Snagit-Style Interactive Screen Region Selector (Tkinter Native)
Displays fullscreen crosshairs, dynamic dimension badge, and high-visibility selection rectangle.
Outputs JSON coordinates to stdout on release: {"x": X, "y": Y, "width": W, "height": H, "geometry": "WxH+X+Y"}
Author: Francisco Betancourt (@fbetancourt-dev)
License: MIT
"""

import sys
import json
import tkinter as tk

class SnagitSelector:
    def __init__(self, border_color="#00E5FF", border_width=4, bg_alpha=0.30):
        self.border_color = border_color
        self.border_width = border_width
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.badge_bg_id = None
        self.badge_text_id = None
        self.cross_h_id = None
        self.cross_v_id = None
        self.result = None

        self.root = tk.Tk()
        self.root.title("Screen Region Selector")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", bg_alpha)
        self.root.config(cursor="crosshair")

        self.canvas = tk.Canvas(
            self.root,
            cursor="crosshair",
            bg="#101018",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Motion>", self.on_hover)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Escape>", lambda e: self.cancel())
        self.root.bind("<Button-3>", lambda e: self.cancel())

    def on_hover(self, event):
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        if self.cross_h_id:
            self.canvas.coords(self.cross_h_id, 0, event.y, w, event.y)
        else:
            self.cross_h_id = self.canvas.create_line(0, event.y, w, event.y, fill="#FF5252", dash=(4, 4), width=1)

        if self.cross_v_id:
            self.canvas.coords(self.cross_v_id, event.x, 0, event.x, h)
        else:
            self.cross_v_id = self.canvas.create_line(event.x, 0, event.x, h, fill="#FF5252", dash=(4, 4), width=1)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline=self.border_color,
            width=self.border_width
        )

        self.badge_bg_id = self.canvas.create_rectangle(0, 0, 0, 0, fill="#000000", outline=self.border_color, width=1)
        self.badge_text_id = self.canvas.create_text(0, 0, text="", fill="#FFFFFF", font=("Monospace", 10, "bold"))

    def on_drag(self, event):
        if not self.rect_id:
            return

        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

        w = self.root.winfo_width()
        h = self.root.winfo_height()
        if self.cross_h_id:
            self.canvas.coords(self.cross_h_id, 0, cur_y, w, cur_y)
        if self.cross_v_id:
            self.canvas.coords(self.cross_v_id, cur_x, 0, cur_x, h)

        box_w = abs(cur_x - self.start_x)
        box_h = abs(cur_y - self.start_y)
        dim_str = f" {box_w} x {box_h} px "

        badge_x = cur_x + 15
        badge_y = cur_y + 20
        if badge_x + 90 > w:
            badge_x = cur_x - 100
        if badge_y + 30 > h:
            badge_y = cur_y - 30

        self.canvas.itemconfigure(self.badge_text_id, text=dim_str)
        bbox = self.canvas.bbox(self.badge_text_id)
        if bbox:
            pad = 4
            self.canvas.coords(self.badge_bg_id, bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad)
            self.canvas.coords(self.badge_text_id, (bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2)
            self.canvas.tag_raise(self.badge_bg_id)
            self.canvas.tag_raise(self.badge_text_id)

    def on_release(self, event):
        if self.start_x is None:
            self.cancel()
            return

        x1 = min(self.start_x, event.x)
        x2 = max(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        y2 = max(self.start_y, event.y)
        w = x2 - x1
        h = y2 - y1

        if w >= 4 and h >= 4:
            self.result = {
                "x": x1,
                "y": y1,
                "width": w,
                "height": h,
                "geometry": f"{w}x{h}+{x1}+{y1}"
            }
        self.root.destroy()

    def cancel(self):
        self.result = None
        self.root.destroy()

    def get_selection(self):
        self.root.mainloop()
        return self.result

def main():
    selector = SnagitSelector(border_color="#00E5FF", border_width=4)
    res = selector.get_selection()
    if res:
        print(json.dumps(res))
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
