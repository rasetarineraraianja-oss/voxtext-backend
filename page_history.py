# -*- coding: utf-8 -*-
"""
page_history.py — Page historique & statistiques de VoxText.
"""

import tkinter as tk
from tkinter import ttk

import database
from constants import ACCENT, SUCCESS, ERROR, WHITE
from ui_helpers import pill_btn, make_card


class HistoryPage:
    """Affiche l'historique des transcriptions et les statistiques utilisateur."""

    def __init__(self, parent, theme, user_email):
        self._t          = theme
        self.user_email  = user_email
        self._stat_cards = {}
        self.current_lang = "fr"

        self.frame = self._build(parent)

    # ─────────────────────────────────────────
    # BUILD
    # ─────────────────────────────────────────
    def _build(self, parent):
        T    = self._t
        page = tk.Frame(parent, bg=T["BG"])

        tk.Label(page, text=self.tr("history_title"),
                 bg=T["BG"], fg=T["TEXT"],
                 font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(20, 4))
        tk.Label(page, text="Suivi de votre activité enregistrée localement.",
                 bg=T["BG"], fg=T["MUTED"],
                 font=("Helvetica", 10)).pack(anchor="w", pady=(0, 12))

        # ── Cartes statistiques ──
        stats_row = tk.Frame(page, bg=T["BG"])
        stats_row.pack(fill="x", pady=(0, 12))

        for key, icon, label in [
            ("total_trans",     "🎙", "Transcriptions"),
            ("total_downloads", "⬇", "Téléchargements"),
            ("total_sessions",  "💻", "Sessions"),
            ("member_since",    "📅", "Membre depuis"),
        ]:
            outer = tk.Frame(stats_row, bg=T["BORDER"])
            outer.pack(side="left", fill="both", expand=True, padx=(0, 8))
            inner = tk.Frame(outer, bg=T["CARD"], padx=16, pady=14)
            inner.pack(fill="both", expand=True, padx=1, pady=1)
            tk.Label(inner, text=icon, bg=T["CARD"],
                     font=("Helvetica", 20)).pack(anchor="w")
            val_lbl = tk.Label(inner, text="—",
                               bg=T["CARD"], fg=T["TEXT"],
                               font=("Helvetica", 18, "bold"))
            val_lbl.pack(anchor="w", pady=(2, 0))
            tk.Label(inner, text=label, bg=T["CARD"], fg=T["MUTED"],
                     font=("Helvetica", 8)).pack(anchor="w")
            self._stat_cards[key] = val_lbl

        # ── Tableau ──
        outer_tbl, card_tbl = make_card(page, T, padx=12, pady=12)
        outer_tbl.pack(fill="both", expand=True)

        tbl_header = tk.Frame(card_tbl, bg=T["CARD"])
        tbl_header.pack(fill="x", pady=(0, 10))

        tk.Label(tbl_header, text="TRANSCRIPTIONS RÉCENTES",
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(side="left")

        pill_btn(tbl_header, "🔄  Actualiser", self.refresh,
                 bg=ACCENT, hover="#8b84ff", w=120, h=30, fsize=8).pack(side="right")

        # Style Treeview
        style = ttk.Style()
        style.theme_use("default")
        style.configure("VT.Treeview",
                        background=T["INPUT"],
                        foreground=T["TEXT2"],
                        fieldbackground=T["INPUT"],
                        rowheight=28,
                        font=("Helvetica", 9))
        style.configure("VT.Treeview.Heading",
                        background=T["BORDER"],
                        foreground=T["TEXT"],
                        font=("Helvetica", 9, "bold"),
                        relief="flat")
        style.map("VT.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", WHITE)])

        cols = ("Date", "Fichier", "Langue", "Caractères", "Statut")
        self.tree = ttk.Treeview(card_tbl, columns=cols,
                                 show="headings", height=14,
                                 style="VT.Treeview")

        widths  = {"Date": 140, "Fichier": 260, "Langue": 80,
                   "Caractères": 100, "Statut": 70}
        anchors = {"Date": "center", "Fichier": "w", "Langue": "center",
                   "Caractères": "center", "Statut": "center"}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor=anchors[col])

        scroll_y = tk.Scrollbar(card_tbl, orient="vertical",
                                command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure("success", foreground=SUCCESS)
        self.tree.tag_configure("error",   foreground=ERROR)

        return page

    def tr(self, key):
        from translations import TRANSLATIONS
        return TRANSLATIONS.get(self.current_lang, {}).get(key, key)

    def set_language(self, lang):
        self.current_lang = lang

        # 🔥 vider contenu seulement
        for w in self.frame.winfo_children():
            w.destroy()

        # 🔄 reconstruire à l’intérieur
        new_content = self._build(self.frame)

        new_content.pack(fill="both", expand=True)

    # ─────────────────────────────────────────
    # REFRESH
    # ─────────────────────────────────────────
    def refresh(self):
        """Recharge statistiques et tableau depuis la base de données."""
        # Stats
        try:
            stats = database.get_stats(self.user_email)
            self._stat_cards["total_trans"].config(
                text=str(stats.get("total_trans", 0)))
            self._stat_cards["total_downloads"].config(
                text=str(stats.get("total_downloads", 0)))
            self._stat_cards["total_sessions"].config(
                text=str(stats.get("total_sessions", 0)))
            self._stat_cards["member_since"].config(
                text=stats.get("member_since", "—"))
        except Exception as e:
            print("Erreur stats:", e)

        # Tableau
        try:
            for row in self.tree.get_children():
                self.tree.delete(row)

            history = database.get_transcription_history(
                self.user_email, limit=100)

            for h in history:
                date_str = h.get("created_at", "")[:16].replace("T", "  ")
                fname    = h.get("filename") or "—"
                lang     = h.get("language") or "auto"
                chars    = str(h.get("char_count", "")) if h.get("char_count") else "—"
                ok       = h.get("status") == "success"
                self.tree.insert(
                    "", "end",
                    values=(date_str, fname, lang, chars, "✔" if ok else "✖"),
                    tags=("success" if ok else "error",),
                )
        except Exception as e:
            print("Erreur historique:", e)