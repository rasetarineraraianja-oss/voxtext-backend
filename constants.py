# -*- coding: utf-8 -*-
"""
constants.py — Couleurs, thèmes et constantes globales de VoxText.
"""

THEMES = {
    "dark": {
        "BG":     "#0d0d14",
        "CARD":   "#16161f",
        "BORDER": "#2a2a3a",
        "INPUT":  "#1e1e2e",
        "TEXT":   "#e8e8f0",
        "TEXT2":  "#a0a0c0",
        "MUTED":  "#5a5a7a",
    },
    "light": {
        "BG":     "#f0f0f8",
        "CARD":   "#ffffff",
        "BORDER": "#d0d0e0",
        "INPUT":  "#f8f8ff",
        "TEXT":   "#1a1a2e",
        "TEXT2":  "#4a4a6a",
        "MUTED":  "#8888aa",
    },
}

ACCENT          = "#6c63ff"
ACCENT2         = "#4ecdc4"
SUCCESS         = "#1db954"
ERROR           = "#e25555"
WARN            = "#f5c518"
WHITE           = "#ffffff"
GOLD            = "#f5c518"
PRO_COLOR       = "#a78bfa"
DISABLED_COLOR  = "#444455"

FONT_SIZE_MIN     = 8
FONT_SIZE_MAX     = 28
FONT_SIZE_DEFAULT = 11

FORMATS_SUPPORTES = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac")

API_URL = "https://voxtext-backend-r6l8.onrender.com"