# -*- coding: utf-8 -*-
"""
main.py — Point d'entrée de VoxText.

Lance simplement la fenêtre principale.
"""

import os
import tkinter as tk
from app import VoxTextApp


if __name__ == "__main__":
    root = tk.Tk()

    icon_path = os.path.join(os.path.dirname(__file__), "logo1.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    app = VoxTextApp(root)
    root.mainloop()