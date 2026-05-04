# -*- coding: utf-8 -*-
"""
app.py — Classe principale VoxTextApp.
CORRECTIONS :
  - refresh_user() corrigé (self.get_user_api)
  - _start_badge_auto_refresh() ajouté
  - _get_badge() relit toujours l'API
"""

import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import requests
from PIL import Image, ImageTk

import billing
import database
from constants import (
    THEMES, API_URL,
    ACCENT, SUCCESS, ERROR, PRO_COLOR, DISABLED_COLOR, WHITE,
)
from ui_helpers import pill_btn, make_card, make_entry_row
from page_auth         import AuthPage
from page_transcribe   import TranscribePage
from page_download     import DownloadPage
from page_player       import PlayerPage
from page_history      import HistoryPage
from page_subscription import SubscriptionPage


class VoxTextApp:

    def __init__(self, root):
        self.root = root

        self.user_email = None
        try:
            with open("session.txt", "r") as f:
                self.user_email = f.read().strip()
        except Exception:
            pass

        self.icons = {}
        self._load_icons()
        self._i18n_widgets = []
        self.current_lang  = "fr"

        self.root.title("VoxText — Transcription IA")
        self.root.geometry("980x800")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        self._theme_name = tk.StringVar(value="light")
        self._t          = THEMES[self._theme_name.get()]
        self.root.configure(bg=self._t["BG"])

        self.audio_path     = tk.StringVar()
        self.active_tab     = tk.StringVar(value="transcribe")
        self.pages          = {}
        self._page_objs     = {}
        self._lockable_btns = []

        if self.auto_login():
            self._on_login(self.user_email)
        else:
            self._build()

    # ── Icônes ──────────────────────────────────────────────────
    def _load_icons(self):
        base  = "assets"
        files = {"YouTube":"youtube.png","SoundCloud":"soundcloud.png",
                 "Vimeo":"vimeo.png","Spotify":"spotify.png"}
        for name, filename in files.items():
            path = os.path.join(base, filename)
            if not os.path.exists(path):
                continue
            try:
                img = Image.open(path).resize((48,48), Image.LANCZOS)
                self.icons[name] = ImageTk.PhotoImage(img)
            except Exception:
                pass

    # ── Thème ────────────────────────────────────────────────────
    def _toggle_theme(self):
        new = "light" if self._theme_name.get() == "dark" else "dark"
        self._theme_name.set(new)
        self._t = THEMES[new]
        self.root.configure(bg=self._t["BG"])
        for w in self.root.winfo_children():
            w.destroy()
        self._build()
        self._show_tab(self.active_tab.get())

    # ── I18n ─────────────────────────────────────────────────────
    def register_i18n(self, widget, key, attr="text"):
        self._i18n_widgets.append((widget, key, attr))

    def tr(self, key):
        from translations import TRANSLATIONS
        return TRANSLATIONS.get(self.current_lang, {}).get(key, key)

    # ── Auto-login ───────────────────────────────────────────────
    def auto_login(self):
        if not os.path.exists("session.txt"):
            return False
        try:
            with open("session.txt", "r") as f:
                email = f.read().strip()
            if not email:
                return False
            try:
                res = requests.get(f"https://voxtext-backend-r6l8.onrender.com/user/{email}")
                if res.status_code != 200:
                    return False
                print("STATUS:", res.status_code)
                print("TEXT:", res.text)
                try:
                    data = res.json()
                except Exception as e:
                    print("❌ ERREUR JSON:", e)
                    print("RESPONSE:", res.text)
                    return
            except Exception as e:
                print("❌ ERREUR API:", e)
                messagebox.showerror("Erreur", "Impossible de contacter le serveur")
                return False
            if data and data.get("email"):
                self.user_email = email
                return True
        except Exception as e:
            print("❌ AUTO LOGIN ERROR:", e)
        return False

    # ── Build ────────────────────────────────────────────────────
    def _build(self):
        if not self.user_email:
            container = tk.Frame(self.root, bg=self._t["BG"])
            container.pack(fill="both", expand=True)
            auth = AuthPage(container, self._t, on_login_success=self._on_login)
            auth.frame.pack(fill="both", expand=True)
            return

        self._build_header()
        self._build_tabs()

        self.container = tk.Frame(self.root, bg=self._t["BG"])
        self.container.pack(fill="both", expand=True, padx=24, pady=(0,24))

        self._build_pages()
        self._show_tab("transcribe")

        # ✅ Rafraîchissement automatique du badge toutes les 10s
        self._start_badge_auto_refresh()

    # ✅ Rafraîchissement automatique
    def _start_badge_auto_refresh(self):
        """Rafraîchit le badge toutes les 10s — détecte l'activation Pro."""
        def refresh():
            try:
                self._update_header_badge()
            except Exception:
                pass
            try:
                self.root.after(10_000, refresh)
            except Exception:
                pass
        self.root.after(5_000, refresh)

    # ── Tabs i18n ────────────────────────────────────────────────
    def _update_tabs_i18n(self):
        mapping = {
            "transcribe":   ("📝", "tab_transcribe"),
            "download":     ("⬇",  "tab_download"),
            "player":       ("🎵", "tab_player"),
            "history":      ("📜", "tab_history"),
            "subscription": ("💳", "tab_subscription"),
        }
        for key, btn in self.tab_btns.items():
            icon, label_key = mapping[key]
            btn.config(text=f"{icon}  {self.tr(label_key)}")

    # ── Header ───────────────────────────────────────────────────
    def _build_header(self):
        T   = self._t
        hdr = tk.Frame(self.root, bg=T["CARD"], height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Frame(hdr, bg=ACCENT, height=3).pack(fill="x", side="top")

        inner = tk.Frame(hdr, bg=T["CARD"])
        inner.pack(fill="both", expand=True, padx=24)

        left = tk.Frame(inner, bg=T["CARD"])
        left.pack(side="left", fill="y")

        try:
            logo_img = Image.open("logo.png").convert("RGBA").resize((48,48))
            self._header_logo = ImageTk.PhotoImage(logo_img)
            logo_lbl = tk.Label(left, image=self._header_logo,
                                bg=T["CARD"], cursor="hand2")
            logo_lbl.pack(side="left", padx=(0,10))
        except Exception:
            logo_lbl = tk.Label(left, text="🎙", bg=T["CARD"],
                                font=("Helvetica",22), cursor="hand2")
            logo_lbl.pack(side="left", padx=(0,8))

        logo_lbl.bind("<Button-1>", lambda e: self._show_about())
        logo_lbl.bind("<Button-3>", lambda e: self._show_terms())

        tk.Label(left, text="VoxText", bg=T["CARD"], fg=T["TEXT"],
                 font=("Helvetica",18,"bold")).pack(side="left")
        tk.Label(left, text="  Transcription IA", bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica",11)).pack(side="left", pady=4)

        right = tk.Frame(inner, bg=T["CARD"])
        right.pack(side="right", fill="y")

        # Langue
        lang_btn = tk.Label(
            right, text=f"🌍 {self.current_lang.upper()}",
            bg=T["BORDER"], fg=T["TEXT2"],
            font=("Helvetica",9,"bold"), padx=10, pady=4, cursor="hand2")
        lang_btn.pack(side="right", padx=(0,8))

        def toggle_lang(event=None):
            new_lang = "en" if self.current_lang == "fr" else "fr"
            self.current_lang = new_lang
            lang_btn.config(text=f"🌍 {new_lang.upper()}")
            for page_obj in self._page_objs.values():
                if hasattr(page_obj, "set_language"):
                    page_obj.set_language(new_lang)
            self._update_tabs_i18n()
            logout_btn.config(text=f"⎋ {self.tr('logout')}")
            theme_tip = self.tr("theme_light") if self._theme_name.get()=="dark" else self.tr("theme_dark")
            toggle_btn.config(text=f"{theme_icon}  {theme_tip}")
            self._update_header_badge()

        lang_btn.bind("<Button-1>", toggle_lang)

        is_dark    = self._theme_name.get() == "dark"
        theme_icon = "☀️" if is_dark else "🌙"
        theme_tip  = self.tr("theme_light") if is_dark else self.tr("theme_dark")
        toggle_btn = tk.Label(
            right, text=f"{theme_icon}  {theme_tip}",
            bg=T["BORDER"], fg=T["TEXT2"],
            font=("Helvetica",9,"bold"), padx=10, pady=4, cursor="hand2")
        toggle_btn.pack(side="right", padx=(0,12))
        toggle_btn.bind("<Button-1>", lambda e: self._toggle_theme())

        # ✅ Badge calculé depuis l'API
        badge_text, badge_color = self._get_badge()
        self.header_plan_badge = tk.Label(
            right, text=badge_text,
            bg=badge_color, fg=WHITE,
            font=("Helvetica",9,"bold"), padx=10, pady=4, cursor="hand2")
        self.header_plan_badge.pack(side="right", padx=(0,8))
        self.header_plan_badge.bind("<Button-1>",
                                    lambda e: self._show_tab("subscription"))

        logout_btn = tk.Label(
            right, text=f"⎋ {self.tr('logout')}",
            bg=ERROR, fg=WHITE,
            font=("Helvetica",9,"bold"), padx=10, pady=4, cursor="hand2")
        logout_btn.pack(side="right", padx=(0,8))
        logout_btn.bind("<Button-1>", lambda e: self.confirm_logout())

    # ── Tabs ─────────────────────────────────────────────────────
    def _build_tabs(self):
        T       = self._t
        tab_bar = tk.Frame(self.root, bg=T["BG"])
        tab_bar.pack(fill="x", padx=24, pady=(16,0))

        self.tab_btns = {}
        tabs = [
            ("transcribe",   "📝", "tab_transcribe"),
            ("download",     "⬇",  "tab_download"),
            ("player",       "🎵", "tab_player"),
            ("history",      "📜", "tab_history"),
            ("subscription", "💳", "tab_subscription"),
        ]
        for key, icon, label_key in tabs:
            text = f"{icon}  {self.tr(label_key)}"
            btn  = tk.Label(tab_bar, text=text,
                            bg=T["BG"], fg=T["MUTED"],
                            font=("Helvetica",11), padx=16, pady=8, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, k=key: self._show_tab(k))
            btn.bind("<Enter>",    lambda e, b=btn: b.config(fg=T["TEXT"]))
            btn.bind("<Leave>",    lambda e, b=btn, k=key:
                b.config(fg=T["TEXT"] if self.active_tab.get()==k else T["MUTED"]))
            self.tab_btns[key] = btn

        tk.Frame(self.root, bg=T["BORDER"], height=1).pack(fill="x", padx=24, pady=(8,0))

    def _show_tab(self, key):
        self.active_tab.set(key)
        for k, page in self.pages.items():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        T = self._t
        for k, btn in self.tab_btns.items():
            btn.config(fg=T["TEXT"] if k==key else T["MUTED"],
                       font=("Helvetica",11,"bold" if k==key else "normal"))
        if key == "history":
            self._page_objs["history"].refresh()
        # ✅ Rafraîchir le badge à chaque changement d'onglet
        self._update_header_badge()

    # ── Pages ────────────────────────────────────────────────────
    def _build_pages(self):
        c = self.container

        tp = TranscribePage(c, self._t, self.audio_path,
            get_user_fn=self.get_user_api, is_pro_fn=self.is_user_pro,
            lock_buttons_fn=self._lock_buttons,
            update_badge_fn=self._update_header_badge,
            show_tab_fn=self._show_tab)
        self.pages["transcribe"]      = tp.frame
        self._page_objs["transcribe"] = tp
        self._lockable_btns.append((tp.btn_transcribe, SUCCESS))

        dp = DownloadPage(c, self._t, self.icons, self._lock_buttons, self.user_email)
        self.pages["download"]      = dp.frame
        self._page_objs["download"] = dp
        self._lockable_btns.append((dp.btn_download, "#4ecdc4"))

        pp = PlayerPage(c, self._t, self.audio_path)
        self.pages["player"]      = pp.frame
        self._page_objs["player"] = pp

        hp = HistoryPage(c, self._t, self.user_email)
        self.pages["history"]      = hp.frame
        self._page_objs["history"] = hp

        sp = SubscriptionPage(c, self._t,
            get_user_fn=self.get_user_api, is_pro_fn=self.is_user_pro,
            update_badge_fn=self._update_header_badge)
        self.pages["subscription"]      = sp.frame
        self._page_objs["subscription"] = sp

    def _on_done(self, text):
    self._transcribing = False
    self._set_progress(1.0)
    self.text_output.config(fg=self._t["TEXT"])
    self.text_output.delete("1.0", "end")

    for line in text.split("\n"):
        if line.startswith("[") and "]" in line:
            bracket_end = line.index("]") + 1
            self.text_output.insert("end", line[:bracket_end], "timestamp")
            self.text_output.insert("end", line[bracket_end:] + "\n")
        else:
            self.text_output.insert("end", line + "\n")

    self.trans_status.config(text=self.tr("done"), fg=SUCCESS)

    user = self.get_user()
    plan = user.get("plan", "free") if user else "free"
    rem = billing.remaining_free()

    if plan == "free" and rem == 0:
        messagebox.showinfo(
            "Dernier essai gratuit utilisé",
            "🎉 Transcription terminée !\n\n"
            "Vous avez utilisé tous vos essais gratuits.\n"
            "Passez en Pro (4,99 €/mois) pour continuer.",
        )
        self.show_tab("subscription")
      
    # ── API ──────────────────────────────────────────────────────
    def get_user_api(self):
        """Relit toujours l'API — pas de cache."""
        if not self.user_email:
            return None
        try:
            res = requests.get(f"{API_URL}/user/{self.user_email}", timeout=5)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[API] get_user erreur : {e}", flush=True)
            return None

    def is_user_pro(self):
        """Vérifie si l'utilisateur a un plan Pro actif."""
        if not self.user_email:
            return False
        user = self.get_user_api()
        if not user or user.get("plan") != "pro":
            return False
        expires = user.get("pro_expires")
        if not expires:
            return False
        try:
            return datetime.now() <= datetime.fromisoformat(expires)
        except Exception:
            return False

    # ── Badge ────────────────────────────────────────────────────
    def _get_badge(self):
        """Retourne (texte, couleur) du badge — relit toujours l'API."""
        try:
            user = self.get_user_api()
            plan = user.get("plan", "free") if user else "free"
            if plan == "pro":
                expires = user.get("pro_expires", "") if user else ""
                if expires:
                    try:
                        if datetime.now() <= datetime.fromisoformat(expires):
                            return "⭐ PRO", PRO_COLOR
                    except Exception:
                        pass
        except Exception:
            pass
        rem  = billing.remaining_free()
        text = self.tr("free_badge").format(rem=rem, total=billing.FREE_LIMIT)
        return text, ACCENT if rem > 0 else ERROR

    def _update_header_badge(self):
        """Met à jour badge + bannière transcription."""
        text, color = self._get_badge()
        if hasattr(self, "header_plan_badge"):
            self.header_plan_badge.config(text=text, bg=color)
        tp = self._page_objs.get("transcribe")
        if tp and hasattr(tp, "_update_trial_banner"):
            tp._update_trial_banner()
        # ✅ Recharger la page abonnement si elle est visible
        if self.active_tab.get() == "subscription":
            sp = self._page_objs.get("subscription")
            if sp and hasattr(sp, "reload"):
                sp.reload()

    # ── Lock boutons ─────────────────────────────────────────────
    def _lock_buttons(self, locked=True):
    for btn, original_bg in self._lockable_btns:
        if btn is None:
            continue
        try:
            btn._disabled = locked
            if locked:
                btn._draw(DISABLED_COLOR)
                btn.config(cursor="arrow")
            else:
                btn._draw(original_bg)
                btn.config(cursor="hand2")
        except Exception:
            pass

    # ── Auth ─────────────────────────────────────────────────────
    def _on_login(self, email):
        self.user_email = email
        for w in self.root.winfo_children():
            w.destroy()
        self._build()


    def logout(self):
        import os

        print("Déconnexion...")

        # reset utilisateur
        self.user_email = None

        # supprimer session
        if os.path.exists("session.txt"):
            os.remove("session.txt")

        # nettoyer UI
        for widget in self.root.winfo_children():
            widget.destroy()

        # reconstruire écran login
        self._build()

    from tkinter import messagebox

    def confirm_logout(self):
        if messagebox.askyesno("Déconnexion", "Voulez-vous vraiment vous déconnecter ?"):
            self.logout()


    # ✅ refresh_user corrigé (utilisait get_user_api sans self)
    def refresh_user(self):
        data = self.get_user_api()
        if data:
            self.user_plan = data.get("plan", "free")
            print(f"[refresh_user] plan = {self.user_plan}", flush=True)

    # ── À propos ─────────────────────────────────────────────────
    def _show_about(self):
        T   = self._t
        win = tk.Toplevel(self.root)
        win.title("À propos — VoxText")
        win.geometry("420x400")
        win.configure(bg=T["BG"])
        win.resizable(False, False)
        win.grab_set()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        win.geometry(f"420x400+{(sw-420)//2}+{(sh-400)//2}")

        hdr = tk.Frame(win, bg=ACCENT, height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        try:
            logo_img = Image.open("logo.png").convert("RGBA").resize((64,64))
            self._about_logo = ImageTk.PhotoImage(logo_img)
            tk.Label(hdr, image=self._about_logo, bg=ACCENT).pack(side="left", padx=16)
        except Exception:
            tk.Label(hdr, text="🎙", bg=ACCENT,
                     font=("Helvetica",32)).pack(side="left", padx=16)

        tf = tk.Frame(hdr, bg=ACCENT)
        tf.pack(side="left", fill="y", pady=12)
        tk.Label(tf, text="VoxText", bg=ACCENT, fg=WHITE,
                 font=("Helvetica",18,"bold")).pack(anchor="w")
        tk.Label(tf, text="Transcription IA", bg=ACCENT, fg="#d0d0ff",
                 font=("Helvetica",10)).pack(anchor="w")

        body = tk.Frame(win, bg=T["BG"], padx=24, pady=20)
        body.pack(fill="both", expand=True)

        try:
            stats        = database.get_stats(self.user_email)
            member_since = stats.get("member_since","—")
            total_trans  = stats.get("total_trans",0)
        except Exception:
            member_since = "—"
            total_trans  = 0

        for label, value in [
            ("Version","1.0.0"),("Modèle IA","Whisper (OpenAI)"),
            ("Framework","Python / Tkinter"),("Auteur","Barson"),
            ("Année","2026"),("Contact","contact@voxtext.app"),
            ("Membre depuis",member_since),("Transcriptions",str(total_trans)),
        ]:
            row = tk.Frame(body, bg=T["BG"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{label} :", bg=T["BG"], fg=T["MUTED"],
                     font=("Helvetica",9), width=14, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=T["BG"], fg=T["TEXT"],
                     font=("Helvetica",9,"bold")).pack(side="left")

        tk.Frame(body, bg=T["BORDER"], height=1).pack(fill="x", pady=10)
        btn_row = tk.Frame(body, bg=T["BG"])
        btn_row.pack()
        pill_btn(btn_row, "📋  Conditions",
                 lambda: [win.destroy(), self._show_terms()],
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=140, h=32, fsize=9).pack(side="left", padx=6)
        pill_btn(btn_row, "✖  Fermer", win.destroy,
                 bg=ACCENT, hover="#8b84ff",
                 w=110, h=32, fsize=9).pack(side="left", padx=6)

    def _show_terms(self):
        T   = self._t
        win = tk.Toplevel(self.root)
        win.title("Conditions d'utilisation")
        win.geometry("520x560")
        win.configure(bg=T["BG"])
        win.resizable(False, True)
        win.grab_set()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        win.geometry(f"520x560+{(sw-520)//2}+{(sh-560)//2}")

        hdr = tk.Frame(win, bg=T["BORDER"], height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  Conditions d'utilisation",
                 bg=T["BORDER"], fg=T["TEXT"],
                 font=("Helvetica",13,"bold")).pack(side="left", padx=20)

        outer     = tk.Frame(win, bg=T["BG"])
        outer.pack(fill="both", expand=True, padx=20, pady=10)
        canvas    = tk.Canvas(outer, bg=T["BG"], highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body   = tk.Frame(canvas, bg=T["BG"])
        win_id = canvas.create_window((0,0), window=body, anchor="nw")
        body.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1*(e.delta//120),"units"))

        sections = [
            ("1. Utilisation",
             "VoxText est un outil de transcription audio basé sur Whisper (OpenAI). "
             "L'application est fournie à des fins personnelles et professionnelles."),
            ("2. Confidentialité",
             "Vos fichiers audio sont traités localement. Aucune donnée audio "
             "n'est envoyée vers des serveurs externes."),
            ("3. Propriété intellectuelle",
             "VoxText utilise Whisper sous licence MIT. "
             "L'interface est la propriété de Barson © 2026."),
            ("4. Abonnement",
             f"Le plan gratuit inclut {billing.FREE_LIMIT} transcriptions. "
             f"Le plan Pro ({billing.PRO_PRICE:.2f} €/mois) est illimité. "
             "Annulation possible à tout moment."),
            ("5. Responsabilité",
             "VoxText ne garantit pas la précision à 100% des transcriptions. "
             "L'utilisateur est responsable de l'usage des transcriptions."),
            ("6. Droit applicable","Conditions soumises au droit français."),
        ]

        for title, text in sections:
            tk.Label(body, text=title, bg=T["BG"], fg=T["TEXT"],
                     font=("Helvetica",10,"bold"), anchor="w").pack(fill="x", pady=(14,4))
            tk.Frame(body, bg=ACCENT, height=2).pack(fill="x", pady=(0,6))
            tk.Label(body, text=text, bg=T["BG"], fg=T["MUTED"],
                     font=("Helvetica",9), justify="left",
                     anchor="w", wraplength=440).pack(fill="x", anchor="w")

        btn_frame = tk.Frame(win, bg=T["BG"])
        btn_frame.pack(pady=10)
        pill_btn(btn_frame, "✖  Fermer", win.destroy,
                 bg=ACCENT, hover="#8b84ff", w=120, h=32, fsize=9).pack()
