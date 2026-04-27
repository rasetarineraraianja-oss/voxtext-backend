# -*- coding: utf-8 -*-
"""
page_transcribe.py - Page de transcription audio de VoxText.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import self

import billing
from constants import (
    ACCENT, ACCENT2, SUCCESS, ERROR, WHITE,
    FONT_SIZE_MIN, FONT_SIZE_MAX, FONT_SIZE_DEFAULT,
    FORMATS_SUPPORTES,
)
from ui_helpers import pill_btn, make_card, make_entry_row

try:
    from transcriber_debug import transcribe as do_transcribe
    WHISPER_OK = True
except Exception as e:
    print("Erreur chargement whisper:", e)
    WHISPER_OK = False

    def do_transcribe(path, language=None, hint="", progress_callback=None):
        return "Whisper non installe. Executez : pip install faster-whisper"


class TranscribePage:
    """Page de transcription audio."""

    def __init__(self, parent, theme, audio_path_var,
                 get_user_fn, is_pro_fn,
                 lock_buttons_fn, update_badge_fn, show_tab_fn):
        self._t = theme
        self._i18n_widgets = []
        self.current_lang = "en"  # ou "fr"
        self.audio_path = audio_path_var
        self.get_user = get_user_fn
        self.is_pro = is_pro_fn
        self.lock_buttons = lock_buttons_fn
        self.update_badge = update_badge_fn
        self.show_tab = show_tab_fn

        self._transcribing = False
        self._font_size = FONT_SIZE_DEFAULT
        self._progress_value = 0.0
        self.language_var = tk.StringVar(value="auto")
        self.hint_var = tk.StringVar()
        self.lang_btns = {}
        self.btn_transcribe = None

        self.frame = self._build(parent)


    def tr(self, key):
        from translations import TRANSLATIONS
        return TRANSLATIONS.get(self.current_lang, {}).get(key, key)

    def register_i18n(self, widget, key, attr="text"):
        self._i18n_widgets.append((widget, key, attr))

    def refresh_i18n(self):
        for widget, key, attr in self._i18n_widgets:
            try:
                if attr == "text":
                    widget.config(text=self.tr(key))
            except Exception:
                pass

        # 👇 AJOUTE ICI

    def set_language(self, lang):
        self.current_lang = lang

        # Widgets enregistrés via register_i18n (Labels, etc.)
        for widget, key, attr in self._i18n_widgets:
            try:
                if attr == "text":
                    widget.config(text=self.tr(key))
            except Exception:
                pass

        # Browse et Transcribe — pill_btn (Canvas), mis à jour explicitement
        if hasattr(self, "btn_browse"):
            self.btn_browse.config(text=self.tr("browse"))
        if hasattr(self, "btn_transcribe"):
            self.btn_transcribe.config(text=self.tr("transcribe"))

        # Recrée Copy / Clear / titre / zoom avec la bonne langue
        self._update_buttons()
        self._update_trial_banner()

        # Placeholder du champ hint
        placeholder = self.tr("placeholder")
        self.hint_entry.delete(0, "end")
        self.hint_entry.insert(0, placeholder)
        self.hint_entry.config(fg=self._t["MUTED"])

        # Zone de texte
        self.text_output.delete("1.0", "end")
        self.text_output.insert("1.0", self.tr("warning_text"))

    def _build(self, parent):
        T = self._t
        page = tk.Frame(parent, bg=T["BG"])

        outer, card = make_card(page, T)
        outer.pack(fill="x", pady=(16, 0))

        lbl = tk.Label(
            card,
            text=self.tr("audio_file"),
            bg=T["CARD"],
            fg=T["MUTED"],
            font=("Helvetica", 8, "bold"),
        )
        lbl.pack(anchor="w", pady=(0, 8))
        self.register_i18n(lbl, "audio_file")
        file_row = tk.Frame(card, bg=T["CARD"])
        file_row.pack(fill="x")

        entry_outer, _ = make_entry_row(file_row, T, "🎵", self.audio_path)
        entry_outer.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.btn_browse = pill_btn(
            file_row,
            self.tr("browse"),
            self._choose_file,
            bg=ACCENT,
            hover="#8b84ff",
            w=140,
            h=38,
        )
        self.btn_browse.pack(side="left")

        lang_row = tk.Frame(card, bg=T["CARD"])
        lang_row.pack(fill="x", pady=(12, 0))

        tk.Label(
            lang_row,
            text=self.tr("language"),
            bg=T["CARD"],
            fg=T["MUTED"],
            font=("Helvetica", 9),
        ).pack(side="left", padx=(0, 10))

        for code, label in [("fr", "🇫🇷 Français"), ("en", "🇬🇧 English"), ("auto", "🌐 Auto")]:
            btn = tk.Label(
                lang_row,
                text=label,
                bg=T["BORDER"],
                fg=T["TEXT2"],
                font=("Helvetica", 8, "bold"),
                padx=8,
                pady=4,
                cursor="hand2",
            )
            btn.pack(side="left", padx=4)
            btn.bind("<Button-1>", lambda e, c=code: self._select_lang(c))
            self.lang_btns[code] = btn

        self._select_lang("auto")

        hint_row = tk.Frame(card, bg=T["CARD"])
        hint_row.pack(fill="x", pady=(8, 0))

        tk.Label(
            hint_row,
            text=self.tr("title_artist"),
            bg=T["CARD"],
            fg=T["MUTED"],
            font=("Helvetica", 9),
        ).pack(side="left", padx=(0, 10))

        hint_outer, self.hint_entry = make_entry_row(hint_row, T, "🎵", self.hint_var, width=30)
        hint_outer.pack(side="left", fill="x", expand=True)

        placeholder = self.tr("placeholder")
        self.hint_entry.insert(0, placeholder)
        self.hint_entry.config(fg=T["MUTED"])
        self.hint_entry.bind("<FocusIn>", lambda e: self._clear_placeholder(placeholder))
        self.hint_entry.bind("<FocusOut>", lambda e: self._restore_placeholder(placeholder))

        self.trial_banner = tk.Frame(card, bg=T["CARD"])
        self.trial_banner.pack(fill="x", pady=(12, 0))
        self._update_trial_banner()

        action_row = tk.Frame(card, bg=T["CARD"])
        action_row.pack(fill="x", pady=(14, 0))

        self.btn_transcribe = pill_btn(
            action_row,
            self.tr("transcribe"),
            self.transcribe,
            bg=SUCCESS,
            hover="#17a349",
            w=200,
            h=42,
            fsize=11,
        )
        self.btn_transcribe.pack(side="left")
        self.register_i18n(self.btn_transcribe, "transcribe")

        self.trans_status = tk.Label(
            action_row,
            text="",
            bg=T["CARD"],
            fg=T["MUTED"],
            font=("Helvetica", 9),
        )
        self.trans_status.pack(side="left", padx=16)

        prog_outer = tk.Frame(card, bg=T["BORDER"], height=3)
        prog_outer.pack(fill="x", pady=(10, 0))
        self.trans_prog = tk.Frame(prog_outer, bg=ACCENT, height=3)
        self.trans_prog.place(x=0, y=0, relheight=1, relwidth=0)

        outer2, card2 = make_card(page, T, padx=16, pady=16)
        outer2.pack(fill="both", expand=True, pady=(12, 0))

        txt_header = tk.Frame(card2, bg=T["CARD"])
        txt_header.pack(fill="x", pady=(0, 10))
        self.btn_copy_parent = txt_header
        self.btn_clear_parent = txt_header

        tk.Label(
            txt_header,
            text=self.tr("transcription_title"),
            bg=T["CARD"],
            fg=T["MUTED"],
            font=("Helvetica", 8, "bold"),
        ).pack(side="left")

        zoom_frame = tk.Frame(txt_header, bg=T["CARD"])
        zoom_frame.pack(side="right", padx=(8, 0))

        pill_btn(
            zoom_frame,
            "−",
            self._zoom_out,
            bg=T["BORDER"],
            hover="#3a3a55",
            fg=T["TEXT2"],
            w=30,
            h=28,
            fsize=12,
        ).pack(side="left", padx=(0, 4))

        self.zoom_label = tk.Label(
            zoom_frame,
            text=f"{self._font_size}px",
            bg=T["CARD"],
            fg=T["MUTED"],
            font=("Helvetica", 8),
            width=4,
        )
        self.zoom_label.pack(side="left")
        self.zoom_label.bind("<Button-1>", lambda e: self._zoom_reset())

        pill_btn(
            zoom_frame,
            "+",
            self._zoom_in,
            bg=T["BORDER"],
            hover="#3a3a55",
            fg=T["TEXT2"],
            w=30,
            h=28,
            fsize=12,
        ).pack(side="left", padx=(4, 8))

        btn_copy = pill_btn(
            txt_header,
            self.tr("copy"),
            self._copy_text,
            bg=T["BORDER"],
            hover="#3a3a55",
            fg=T["TEXT2"],
            w=90,
            h=28,
            fsize=8,
        )
        btn_copy.pack(side="right", padx=(8, 0))

        self.register_i18n(btn_copy, "copy")


        btn_clear = pill_btn(
            txt_header,
            self.tr("clear"),
            self._clear_text,
            bg=T["BORDER"],
            hover="#3a3a55",
            fg=T["TEXT2"],
            w=80,
            h=28,
            fsize=8,
        )
        btn_clear.pack(side="right")

        self.register_i18n(btn_clear, "clear")

        txt_frame = tk.Frame(card2, bg=T["CARD"])
        txt_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(txt_frame)
        scrollbar.pack(side="right", fill="y")

        self.text_output = tk.Text(
            txt_frame,
            bg=T["INPUT"],
            fg=T["MUTED"],
            font=("Helvetica", self._font_size),
            relief="flat",
            insertbackground=T["TEXT"],
            selectbackground=ACCENT,
            wrap="word",
            padx=12,
            pady=12,
            spacing1=4,
            spacing2=2,
            spacing3=6,
            yscrollcommand=scrollbar.set,
        )
        self.text_output.pack(fill="both", expand=True)
        scrollbar.config(command=self.text_output.yview)

        self.text_output.tag_config(
            "timestamp",
            foreground=ACCENT2,
            font=("Helvetica", self._font_size, "bold"),
        )

        placeholder_text = self.tr("warning_text")

        self.text_output.insert("1.0", placeholder_text)
        page.bind_all("<Control-equal>", lambda e: self._zoom_in())
        page.bind_all("<Control-minus>", lambda e: self._zoom_out())
        page.bind_all("<Control-0>", lambda e: self._zoom_reset())
        self.text_output.bind("<Control-MouseWheel>", self._on_ctrl_scroll)

        return page


    def _update_buttons_i18n(self):
        # 🔄 browse
        if hasattr(self, "btn_browse"):
            self.btn_browse.destroy()

        self.btn_browse = pill_btn(
            self.btn_browse_parent,
            self.tr("browse"),
            self._choose_file,
            bg=ACCENT,
            hover="#8b84ff",
            w=140,
            h=38,
        )
        self.btn_browse.pack(side="left")


    def _choose_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac")]
        )
        if path:
            self.audio_path.set(path)



    def _update_buttons(self):
        for widget in self.btn_copy_parent.winfo_children():
            widget.destroy()

        # Recrée le titre
        tk.Label(
            self.btn_copy_parent,
            text=self.tr("transcription_title"),
            bg=self._t["CARD"],
            fg=self._t["MUTED"],
            font=("Helvetica", 8, "bold"),
        ).pack(side="left")

        # Recrée le zoom frame
        zoom_frame = tk.Frame(self.btn_copy_parent, bg=self._t["CARD"])
        zoom_frame.pack(side="right", padx=(8, 0))

        pill_btn(
            zoom_frame, "−", self._zoom_out,
            bg=self._t["BORDER"], hover="#3a3a55",
            fg=self._t["TEXT2"], w=30, h=28, fsize=12,
        ).pack(side="left", padx=(0, 4))

        self.zoom_label = tk.Label(
            zoom_frame, text=f"{self._font_size}px",
            bg=self._t["CARD"], fg=self._t["MUTED"],
            font=("Helvetica", 8), width=4,
        )
        self.zoom_label.pack(side="left")
        self.zoom_label.bind("<Button-1>", lambda e: self._zoom_reset())

        pill_btn(
            zoom_frame, "+", self._zoom_in,
            bg=self._t["BORDER"], hover="#3a3a55",
            fg=self._t["TEXT2"], w=30, h=28, fsize=12,
        ).pack(side="left", padx=(4, 8))

        # Recrée Copy et Clear avec la bonne langue
        self.btn_copy = pill_btn(
            self.btn_copy_parent, self.tr("copy"), self._copy_text,
            bg=self._t["BORDER"], hover="#3a3a55",
            fg=self._t["TEXT2"], w=90, h=28, fsize=8,
        )
        self.btn_copy.pack(side="right", padx=(8, 0))

        self.btn_clear = pill_btn(
            self.btn_copy_parent, self.tr("clear"), self._clear_text,
            bg=self._t["BORDER"], hover="#3a3a55",
            fg=self._t["TEXT2"], w=80, h=28, fsize=8,
        )
        self.btn_clear.pack(side="right")


    def _select_lang(self, code):
        self.language_var.set(code)
        T = self._t
        for current_code, btn in self.lang_btns.items():
            btn.config(
                bg=ACCENT if current_code == code else T["BORDER"],
                fg=WHITE if current_code == code else T["TEXT2"],
            )

    def _clear_placeholder(self, placeholder):
        if self.hint_var.get() == placeholder:
            self.hint_entry.delete(0, "end")
            self.hint_entry.config(fg=self._t["TEXT"])

    def _restore_placeholder(self, placeholder):
        if not self.hint_var.get():
            self.hint_entry.insert(0, placeholder)
            self.hint_entry.config(fg=self._t["MUTED"])

    def _update_trial_banner(self):
        for widget in self.trial_banner.winfo_children():
            widget.destroy()

        T = self._t
        user = self.get_user()
        plan = user.get("plan", "free") if user else "free"

        # ✅ PRO = illimité
        if plan == "pro":
            tk.Label(
                self.trial_banner,
                text="⭐ PRO actif — illimité",
                bg="#a78bfa",
                fg=WHITE,
                font=("Helvetica", 9, "bold"),
                padx=10,
                pady=5,
            ).pack(side="left")
            return

        # ❌ FREE seulement
        rem = billing.remaining_free()
        total = billing.FREE_LIMIT
        used = total - rem

        color = SUCCESS if rem > 0 else ERROR

        msg = f"{used}/{total} essais utilisés" if rem > 0 else "Quota atteint"

        tk.Label(
            self.trial_banner,
            text=msg,
            bg=color,
            fg=WHITE,
            font=("Helvetica", 9, "bold"),
            padx=10,
            pady=5,
        ).pack(side="left")

    def _zoom_in(self):
        if self._font_size < FONT_SIZE_MAX:
            self._font_size += 1
            self._update_font()

    def _zoom_out(self):
        if self._font_size > FONT_SIZE_MIN:
            self._font_size -= 1
            self._update_font()

    def _zoom_reset(self):
        self._font_size = FONT_SIZE_DEFAULT
        self._update_font()

    def _update_font(self):
        self.text_output.config(font=("Helvetica", self._font_size))
        self.zoom_label.config(text=f"{self._font_size}px")

    def _on_ctrl_scroll(self, event):
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _copy_text(self):
        text = self.text_output.get("1.0", "end").strip()
        if text:
            self.text_output.clipboard_clear()
            self.text_output.clipboard_append(text)
            self.trans_status.config(text=self.tr("copied"), fg=SUCCESS)
            self.frame.after(2000, lambda: self.trans_status.config(text=""))

    def _clear_text(self):
        self.text_output.delete("1.0", "end")

    def _set_progress(self, value, status=None):
        # 🔒 sécuriser la valeur entre 0 et 1
        value = max(0.0, min(1.0, float(value)))
        self._progress_value = value

        # 📊 mettre à jour la barre
        self.trans_prog.place(x=0, y=0, relheight=1, relwidth=value)

        # 📝 mettre à jour le texte
        if status is not None:
            self.trans_status.config(text=status, fg=ACCENT)
        else:
            percent = int(value * 100)
            self.trans_status.config(
                text=self.tr("progress_percent").format(p=percent),
                fg=ACCENT
            )

    def _queue_progress(self, value, status=None):
        self.frame.after(0, lambda v=value, s=status: self._set_progress(v, s))

    def transcribe(self):

        email = self.get_user().get("email")  # adapte selon ton code

        import requests

        res = requests.post(
            "http://127.0.0.1:8000/check-access",
            json={"email": email}
        ).json()

        if res.get("error") == "limit_reached":
            self.show_tab("subscription")  # ✅ correct dans ton app
            return
        # ✅ Empêcher un double-clic pendant une transcription en cours
        if self._transcribing:
            return

        user = self.get_user()
        plan = user.get("plan", "free") if user else "free"

        if plan != "pro":
            if not billing.can_transcribe():
                messagebox.showwarning(
                    self.tr("quota_exceeded_title"),
                    f"Vous avez utilisé vos {billing.FREE_LIMIT} transcriptions gratuites.\n\n"
                    "Passez en plan Pro (4,99 €/mois) pour des transcriptions illimitées !",
                )
                self.show_tab("subscription")
                return

        self.update_badge()

        path = self.audio_path.get().strip()
        if not path:
            messagebox.showwarning(self.tr("no_file"), self.tr("select_file"))
            return
        if not os.path.exists(path):
            messagebox.showerror(self.tr("file_not_found"), f"Le fichier est introuvable :\n{path}")
            return
        if not path.lower().endswith(FORMATS_SUPPORTES):
            messagebox.showerror(
                self.tr("unsupported_format"),
                f"Formats acceptés : {', '.join(FORMATS_SUPPORTES)}",
            )
            return
        if os.path.getsize(path) == 0:
            messagebox.showerror(self.tr("empty_file"), "Le fichier audio sélectionné est vide.")
            return

        lang = self.language_var.get()
        lang = None if lang == "auto" else lang

        hint = self.hint_var.get().strip()
        if hint in ("ex: Titre - Artiste", "ex: Aline - Christophe"):
            hint = ""

        self._transcribing = True
        self.lock_buttons(True)
        self._set_progress(0.0, "⏳  Préparation...")

        filename = os.path.basename(path)

        def run():
            try:
                from faster_whisper import WhisperModel

                # ✅ Mise à jour statut chargement modèle
                self.frame.after(0, lambda: self._set_progress(0.05, "⏳  Chargement du modèle..."))
                model = WhisperModel("base", device="cpu", compute_type="int8")

                self.frame.after(0, lambda: self._set_progress(0.10, "⏳  Analyse en cours..."))
                segments, info = model.transcribe(path, language=lang)

                # ✅ Éviter division par zéro si durée inconnue
                total = info.duration if info.duration else 1

                full_text = ""

                for segment in segments:
                    full_text += segment.text + "\n"

                    # ✅ Progression réelle entre 10% et 100%
                    progress = min(0.10 + (segment.end / total) * 0.90, 1.0)

                    # ✅ Capture de variable locale pour éviter le bug de closure en lambda
                    self.frame.after(0, lambda p=progress: self._set_progress(p))

                    if plan != "pro":
                        billing.record_transcription(
                            filename=filename,
                            language=lang or "auto",
                            char_count=len(full_text),
                        )

                # ✅ Capture full_text dans la lambda pour éviter bug de closure
                self.frame.after(0, lambda t=full_text: self._on_done(t))
                self.frame.after(0, self.update_badge)
                self.frame.after(0, lambda: self.lock_buttons(False))

            except Exception as e:
                msg = str(e)

                billing.record_transcription_error(
                    filename=filename,
                    error_msg=msg,
                )

                # ✅ Capture msg dans la lambda
                self.frame.after(0, lambda m=msg: self._on_error(f"Erreur : {m}"))
                self.frame.after(0, lambda: self.lock_buttons(False))

        # ✅ CORRECTION PRINCIPALE : lancement dans un thread séparé
        threading.Thread(target=run, daemon=True).start()

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

        self.trans_status.config(text= self.tr("done"), fg=SUCCESS)

        user = self.get_user()
        plan = user.get("plan", "free") if user else "free"
        rem = billing.remaining_free()

        if plan == "free" and rem == 0:
            messagebox.showinfo(
                self.tr("last_trial_title"),
                "🎉 Transcription terminée !\n\n"
                "Vous avez utilisé tous vos essais gratuits.\n"
                "Passez en Pro (4,99 €/mois) pour continuer.",
            )
            self.show_tab("subscription")

    def _on_error(self, err):
        self._transcribing = False
        self._progress_value = 0.0
        self.trans_status.config(text=f"✖  {err}", fg=ERROR)
        self.trans_prog.place(relwidth=0)