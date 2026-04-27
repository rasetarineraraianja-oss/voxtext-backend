# -*- coding: utf-8 -*-
"""
ui_helpers.py — Composants UI réutilisables (boutons pill, cartes, champs).
"""

import tkinter as tk
from constants import ACCENT, WHITE, DISABLED_COLOR


def pill_btn(parent, text, command, bg=ACCENT, hover="#8b84ff",
             fg=WHITE, w=180, h=40, fsize=10, radius=12):
    """Bouton arrondi (pill) avec effet hover, protection double-clic,
    et support de .config(text=...) pour l'i18n dynamique."""

    c = tk.Canvas(parent, width=w, height=h,
                  bg=parent["bg"], highlightthickness=0, cursor="hand2")

    _clicking   = [False]
    c._disabled = False
    c._label    = text          # label courant
    c._current_bg = bg          # couleur courante (pour redessiner après config)

    def draw(color):
        c._current_bg = color
        c.delete("all")
        r = radius
        c.create_arc(0,     0,     r*2, r*2, start=90,  extent=90, fill=color, outline=color)
        c.create_arc(w-r*2, 0,     w,   r*2, start=0,   extent=90, fill=color, outline=color)
        c.create_arc(0,     h-r*2, r*2, h,   start=180, extent=90, fill=color, outline=color)
        c.create_arc(w-r*2, h-r*2, w,   h,   start=270, extent=90, fill=color, outline=color)
        c.create_rectangle(r, 0,   w-r, h,   fill=color, outline=color)
        c.create_rectangle(0, r,   w,   h-r, fill=color, outline=color)
        c.create_text(w//2, h//2,
                      text=c._label,
                      fill=fg,
                      font=("Helvetica", fsize, "bold"))

    # ── Surcharge de .config() pour accepter text= ──────────────────────────
    _tk_config = c.config  # garde l'original Tkinter

    def _config(**kw):
        if "text" in kw:
            c._label = kw.pop("text")
            draw(c._current_bg)   # redessine avec le nouveau label
        if kw:
            _tk_config(**kw)      # passe le reste à Tkinter

    c.config = _config
    # ────────────────────────────────────────────────────────────────────────

    def on_click(e):
        if _clicking[0] or c._disabled:
            return
        _clicking[0] = True
        command()
        c.after(500, lambda: _clicking.__setitem__(0, False))

    def on_enter(e):
        if not c._disabled:
            draw(hover)

    def on_leave(e):
        draw(DISABLED_COLOR if c._disabled else bg)

    draw(bg)
    c.bind("<Enter>",    on_enter)
    c.bind("<Leave>",    on_leave)
    c.bind("<Button-1>", on_click)
    c._bg    = bg
    c._hover = hover
    c._draw  = draw
    return c


def make_card(parent, theme, padx=20, pady=20):
    """Retourne (outer_frame, inner_frame) formant une carte avec bordure."""
    outer = tk.Frame(parent, bg=theme["BORDER"])
    inner = tk.Frame(outer, bg=theme["CARD"], padx=padx, pady=pady)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    return outer, inner


def make_entry_row(parent, theme, icon, textvariable, width=42):
    """Retourne (outer_frame, entry_widget) — champ de saisie stylisé."""
    entry_outer = tk.Frame(parent, bg=theme["BORDER"])
    entry_inner = tk.Frame(entry_outer, bg=theme["INPUT"], padx=10)
    entry_inner.pack(fill="x", padx=1, pady=1)
    tk.Label(entry_inner, text=icon, bg=theme["INPUT"],
             font=("Helvetica", 12)).pack(side="left", padx=(0, 6))
    e = tk.Entry(
        entry_inner, textvariable=textvariable,
        bg=theme["INPUT"], fg=theme["TEXT2"],
        insertbackground=theme["TEXT"],
        relief="flat", font=("Helvetica", 10), width=width,
    )
    e.pack(side="left", fill="x", expand=True, ipady=8)
    return entry_outer, e