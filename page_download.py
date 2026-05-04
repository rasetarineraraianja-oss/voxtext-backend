# -*- coding: utf-8 -*-
"""
page_download.py — Page de téléchargement de médias de VoxText.
"""
import os
import shutil
import threading
import tkinter as tk
from tkinter import messagebox
import database as db
import billing
from constants import ACCENT, ACCENT2, SUCCESS, ERROR, WHITE
from ui_helpers import pill_btn, make_card, make_entry_row

FFMPEG_OK = shutil.which("ffmpeg") is not None


class DownloadPage:
    def __init__(self, root, theme, icons, lock_buttons_fn, user_email):
        self.root = root
        self.user_email = user_email
        self._t           = theme
        self.current_lang = "fr"
        self._icons       = icons
        self.lock_buttons = lock_buttons_fn

        self.dl_url      = tk.StringVar()
        self.dl_fmt      = tk.StringVar(value="mp3")
        self.dl_fmt_btns = {}
        self.btn_download = None

        self.frame = self._build(self.root)


    def tr(self, key):
        from translations import TRANSLATIONS
        return TRANSLATIONS.get(self.current_lang, {}).get(key, key)

    def set_language(self, lang):
        self.current_lang = lang

        # 🔥 vider contenu seulement
        for w in self.frame.winfo_children():
            w.destroy()

        # 🔄 reconstruire DANS le même frame
        new_content = self._build(self.frame)

        # 🔥 pack contenu
        new_content.pack(fill="both", expand=True)

    # ─────────────────────────────────────────
    # BUILD
    # ─────────────────────────────────────────
    def _build(self, parent):
        T    = self._t
        page = tk.Frame(parent, bg=T["BG"])

        # ── Carte 1 : saisie URL + format + bouton ──
        outer, card = make_card(page, T)
        outer.pack(fill="x", pady=(16, 0))

        tk.Label(card, text=self.tr("media_link_title"),
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(anchor="w", pady=(0, 8))

        url_row = tk.Frame(card, bg=T["CARD"])
        url_row.pack(fill="x")

        entry_outer, _ = make_entry_row(url_row, T, "🔗", self.dl_url)
        entry_outer.pack(side="left", fill="x", expand=True, padx=(0, 12))

        # Formats
        fmt_row = tk.Frame(card, bg=T["CARD"])
        fmt_row.pack(fill="x", pady=(12, 0))

        tk.Label(fmt_row, text=self.tr("format_label"),
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 9)).pack(side="left", padx=(0, 10))

        for fmt, color in [("mp3", SUCCESS), ("mp4", ERROR), ("wav", ACCENT)]:
            b = tk.Label(fmt_row, text=fmt.upper(),
                         bg=T["BORDER"], fg=T["TEXT2"],
                         font=("Helvetica", 9, "bold"),
                         padx=10, pady=4, cursor="hand2")
            b.pack(side="left", padx=4)
            b.bind("<Button-1>", lambda e, f=fmt, c=color: self._select_fmt(f, c))
            self.dl_fmt_btns[fmt] = (b, color)

        self._select_fmt("mp3", SUCCESS)
        # Bouton télécharger
        action_row = tk.Frame(card, bg=T["CARD"])
        action_row.pack(fill="x", pady=(14, 0))
        
        self.btn_download = pill_btn(
            action_row, self.tr("download_btn"), self.download,
            bg=ACCENT2, hover="#3ab8b0", w=200, h=42, fsize=11,
        )
        self.btn_download.pack(side="left")
        
        self.dl_status = tk.Label(action_row, text="",
                                  bg=T["CARD"], fg=T["MUTED"],
                                  font=("Helvetica", 9))
        self.dl_status.pack(side="left", padx=16)
        
        # ── Barre de progression ──
        prog_outer = tk.Frame(card, bg=T["BORDER"], height=3)
        prog_outer.pack(fill="x", pady=(10, 0))
        self.dl_prog = tk.Frame(prog_outer, bg=ACCENT2, height=3)
        self.dl_prog.place(x=0, y=0, relheight=1, relwidth=0)

        # ── Carte 2 : plateformes supportées ──
        # Les logos sont répartis uniformément sur toute la largeur
        outer2, card2 = make_card(page, T)
        outer2.pack(fill="x", pady=(12, 0))

        tk.Label(card2, text=self.tr("supported_platforms"),
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(anchor="w", pady=(0, 12))

        platforms = [
            ("YouTube",    "youtube.com",    "#FF0000"),
            ("SoundCloud", "soundcloud.com", "#FF5500"),
            ("Vimeo",      "vimeo.com",      "#1AB7EA"),
            ("Spotify",    "spotify.com",    "#1DB954"),
        ]

        # Filtrer uniquement les plateformes dont l'icône est disponible
        available = [(n, d, c) for n, d, c in platforms if n in self._icons]

        if available:
            pl_row = tk.Frame(card2, bg=T["CARD"])
            pl_row.pack(fill="x")

            for name, domain, accent_color in available:
                # Chaque colonne prend une part égale de la largeur
                col = tk.Frame(pl_row, bg=T["CARD"])
                col.pack(side="left", fill="x", expand=True, padx=4)

                # Cadre avec bordure fine (simulée par un Frame extérieur coloré)
                pill = tk.Frame(col, bg=T["BORDER"], padx=1, pady=1)
                pill.pack(fill="x")

                inner = tk.Frame(pill, bg=T["INPUT"], padx=8, pady=10)
                inner.pack(fill="x")

                # Logo centré
                lbl_img = tk.Label(inner, image=self._icons[name], bg=T["INPUT"])
                lbl_img.image = self._icons[name]
                lbl_img.pack()

                # Nom de la plateforme
                lbl_name = tk.Label(
                    inner,
                    text=name,
                    bg=T["INPUT"],
                    fg=T["TEXT2"] if "TEXT2" in T else T["MUTED"],
                    font=("Helvetica", 8, "bold"),
                )
                lbl_name.pack(pady=(6, 0))

                # Domaine en sous-titre discret
                lbl_domain = tk.Label(
                    inner,
                    text=domain,
                    bg=T["INPUT"],
                    fg=T["MUTED"],
                    font=("Helvetica", 7),
                )
                lbl_domain.pack()

                # Effet hover : bordure colorée
                widgets_hover = [inner, lbl_img, lbl_name, lbl_domain]

                def _on_enter(e, p=pill, c=accent_color):
                    p.config(bg=c)

                def _on_leave(e, p=pill):
                    p.config(bg=T["BORDER"])

                for w in widgets_hover:
                    w.bind("<Enter>", _on_enter)
                    w.bind("<Leave>", _on_leave)

        # ── Carte 3 : Instructions d'utilisation ──
        outer3, card3 = make_card(page, T)
        outer3.pack(fill="x", pady=(12, 0))

        tk.Label(card3, text=self.tr("how_to_use"),
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(anchor="w", pady=(0, 10))

        steps = [
            ("1", self.tr("step1_title"), self.tr("step1_desc")),
            ("2", self.tr("step2_title"), self.tr("step2_desc")),
            ("3", self.tr("step3_title"), self.tr("step3_desc")),
            ("4", self.tr("step4_title"), self.tr("step4_desc")),
        ]

        for num, title, desc in steps:
            step_row = tk.Frame(card3, bg=T["CARD"])
            step_row.pack(fill="x", pady=(0, 10))

            # Numéro dans un carré coloré
            tk.Label(
                step_row,
                text=num,
                bg=ACCENT,
                fg=WHITE,
                font=("Helvetica", 9, "bold"),
                width=2,
                pady=3,
            ).pack(side="left", padx=(0, 14))

            txt_col = tk.Frame(step_row, bg=T["CARD"])
            txt_col.pack(side="left", fill="x", expand=True)

            tk.Label(
                txt_col,
                text=title,
                bg=T["CARD"],
                fg=T.get("TEXT", WHITE),
                font=("Helvetica", 9, "bold"),
                anchor="w",
            ).pack(anchor="w")

            tk.Label(
                txt_col,
                text=desc,
                bg=T["CARD"],
                fg=T["MUTED"],
                font=("Helvetica", 8),
                anchor="w",
                justify="left",
                wraplength=480,
            ).pack(anchor="w")

        # ── Carte 4 : Avertissements ──
        outer4, card4 = make_card(page, T)
        outer4.pack(fill="x", pady=(12, 16))

        tk.Label(card4, text=self.tr("warnings_title"),
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(anchor="w", pady=(0, 10))

        warnings = [
            (self.tr("warn1_title"), ERROR, self.tr("warn1_text")),
            (self.tr("warn2_title"), ACCENT2, self.tr("warn2_text")),
        ]

        for warn_title, color, text in warnings:
            # Cadre avec bordure gauche colorée
            warn_wrap = tk.Frame(card4, bg=T["CARD"])
            warn_wrap.pack(fill="x", pady=(0, 10))

            # Barre colorée à gauche
            tk.Frame(warn_wrap, bg=color, width=4).pack(side="left", fill="y")

            warn_inner = tk.Frame(warn_wrap, bg=T["INPUT"], padx=12, pady=10)
            warn_inner.pack(side="left", fill="x", expand=True)

            tk.Label(
                warn_inner,
                text=warn_title,
                bg=T["INPUT"],
                fg=color,
                font=("Helvetica", 9, "bold"),
                anchor="w",
            ).pack(anchor="w", pady=(0, 4))

            tk.Label(
                warn_inner,
                text=text,
                bg=T["INPUT"],
                fg=T["MUTED"],
                font=("Helvetica", 8),
                anchor="w",
                justify="left",
                wraplength=500,
            ).pack(anchor="w")

        return page
    # ─────────────────────────────────────────
    # progress bar
    # ─────────────────────────────────────────
    
    def _set_dl_progress(self, value, status=None):
        value = max(0.0, min(1.0, float(value)))
        try:
            self.dl_prog.place(x=0, y=0, relheight=1, relwidth=value)
            if status:
                self.dl_status.config(text=status, fg=ACCENT)
            else:
                self.dl_status.config(text=f"⏳ {int(value * 100)}%", fg=ACCENT)
        except Exception:
            pass
    
    def _queue_dl_progress(self, value, status=None):
        self.frame.after(0, lambda v=value, s=status: self._set_dl_progress(v, s))

    # ─────────────────────────────────────────
    # FORMAT
    # ─────────────────────────────────────────
    def _select_fmt(self, fmt, color):
        self.dl_fmt.set(fmt)
        T = self._t
        for f, (b, c) in self.dl_fmt_btns.items():
            b.config(
                bg=c     if f == fmt else T["BORDER"],
                fg=WHITE if f == fmt else T["TEXT2"],
            )

    # ─────────────────────────────────────────
    # TÉLÉCHARGEMENT
    # ─────────────────────────────────────────
    def download(self):
        print("STEP 1: start download")
        email = self.user_email
        print("STEP 2: email =", email)
        user = db.get_or_create_user(email)
        print("STEP 3: user =", user)
        if user["plan"] == "free" and user["downloads"] >= 3:
            messagebox.showwarning("Offre gratuite", "Vous avez atteint la limite gratuite.")
            return
    
        url = self.dl_url.get().strip()
        print("STEP 4: before real download")
        if not url:
            messagebox.showwarning(self.tr("missing_url"), self.tr("missing_url_msg"))
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showerror(self.tr("invalid_url"), self.tr("invalid_url_msg"))
            return
    
        fmt = self.dl_fmt.get()
        if fmt in ("mp3", "wav") and not FFMPEG_OK:
            messagebox.showerror(
                "FFmpeg manquant",
                f"La conversion en {fmt.upper()} nécessite FFmpeg.\n\nhttps://ffmpeg.org/download.html",
            )
            return
        if fmt == "mp4" and not FFMPEG_OK:
            messagebox.showerror(
                "FFmpeg manquant",
                "Le téléchargement MP4 HD nécessite FFmpeg.\n\nhttps://ffmpeg.org/download.html",
            )
            return
    
        self.lock_buttons(True)
        self.dl_status.config(text=self.tr("downloading"), fg=ACCENT)
        self.frame.after(0, lambda: self._set_dl_progress(0.0, "⏳  Démarrage..."))
    
        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = downloaded / total
                    speed = d.get("speed", 0) or 0
                    speed_str = f"{speed/1024:.0f} KB/s" if speed else ""
                    self._queue_dl_progress(pct * 0.9, f"⏳ {int(pct*100)}%  {speed_str}")
            elif d["status"] == "finished":
                self._queue_dl_progress(0.95, "⏳  Conversion...")
    
        def run():
            try:
                import yt_dlp
                out_dir = os.path.join(os.path.expanduser("~"), "Downloads", "VoxText")
                os.makedirs(out_dir, exist_ok=True)
    
                opts = self._build_opts(fmt, out_dir)
                opts["progress_hooks"] = [progress_hook]
                opts["quiet"] = True
    
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
    
                billing.record_download(url=url, fmt=fmt, status="success")
    
                self.frame.after(0, lambda: self._set_dl_progress(1.0, self.tr("download_done")))
                self.frame.after(0, lambda: self.dl_status.config(
                    text=self.tr("download_done"), fg=SUCCESS))
                self.frame.after(0, lambda: messagebox.showinfo(
                    "Téléchargement terminé",
                    f"{self.tr('file_saved_in')} :\n{out_dir}",
                ))
                self.frame.after(0, lambda: self.lock_buttons(False))
    
            except ImportError:
                billing.record_download(url=url, fmt=fmt, status="error",
                                        error_msg="yt-dlp non installé")
                self.frame.after(0, lambda: self._set_dl_progress(0.0))
                self.frame.after(0, lambda: self.dl_status.config(
                    text=self.tr("ytdlp_missing_short"), fg=ERROR))
                self.frame.after(0, lambda: messagebox.showerror(
                    self.tr("ytdlp_missing"), self.tr("ytdlp_install_msg")))
                self.frame.after(0, lambda: self.lock_buttons(False))
    
            except Exception as e:
                msg = str(e)
                billing.record_download(url=url, fmt=fmt, status="error", error_msg=msg)
                titre, detail = self._classify_error(msg)
                self.frame.after(0, lambda: self._set_dl_progress(0.0))
                self.frame.after(0, lambda: self.dl_status.config(
                    text=f"✖  {titre}", fg=ERROR))
                self.frame.after(0, lambda t=titre, d=detail:
                    messagebox.showerror(t, d))
                self.frame.after(0, lambda: self.lock_buttons(False))
    
        threading.Thread(target=run, daemon=True).start()

    def _build_opts(self, fmt, out_dir):
        """Construit les options yt-dlp selon le format choisi."""
        tpl = os.path.join(out_dir, "%(title)s.%(ext)s")

        if fmt == "mp3":
            return {
                "format": "bestaudio/best",
                "outtmpl": tpl,
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

        elif fmt == "mp4":
            if FFMPEG_OK:
                return {
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]",
                    "outtmpl": tpl,
                    "quiet": True,
                    "merge_output_format": "mp4",
                    "postprocessors": [{
                        "key": "FFmpegVideoRemuxer",
                        "preferedformat": "mp4",
                    }],
                }
            else:
                return {
                    "format": "best[ext=mp4]/best",
                    "outtmpl": tpl,
                    "quiet": True,
                }

        elif fmt == "wav":
            return {
                "format": "bestaudio/best",
                "outtmpl": tpl,
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }],
            }

        else:
            return {"format": "best[ext=mp4]/best", "outtmpl": tpl, "quiet": True}

    @staticmethod
    def _classify_error(msg):
        """Retourne (titre, détail) selon le type d'erreur yt-dlp."""
        m = msg.lower()
        if "ffmpeg" in m:
            return (
                "FFmpeg manquant",
                "FFmpeg est requis pour fusionner audio et vidéo.\n\n"
                "Téléchargez-le sur :\nhttps://ffmpeg.org/download.html\n\n"
                "Puis ajoutez-le au PATH système.",
            )
        if "unsupported url" in m:
            return "URL non supportée", "Ce lien n'est pas pris en charge par yt-dlp."
        if "private" in m:
            return "Vidéo privée", "Cette vidéo est privée ou nécessite une connexion."
        if "copyright" in m:
            return "Contenu protégé", "Ce contenu est bloqué pour des raisons de droits d'auteur."
        if any(x in m for x in ("network", "connection", "timeout")):
            return "Erreur réseau", "Vérifiez votre connexion internet et réessayez."
        if "404" in msg or "not found" in m:
            return "Contenu introuvable", "La vidéo ou la page est introuvable (404)."
        return "Erreur de téléchargement", f"Erreur inattendue :\n\n{msg}"
