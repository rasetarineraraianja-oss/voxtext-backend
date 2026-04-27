# -*- coding: utf-8 -*-
"""
page_player.py — Page lecteur audio de VoxText.
"""

import os
import time as _time
import tkinter as tk
from tkinter import filedialog

from constants import ACCENT, SUCCESS, ERROR, WARN, WHITE, FORMATS_SUPPORTES
from ui_helpers import pill_btn, make_card, make_entry_row


class PlayerPage:
    """Lecteur audio avec playlist, barre de progression et contrôle du volume."""

    def __init__(self, parent, theme, audio_path_var):
        self._t          = theme
        self.audio_path  = audio_path_var

        # État lecteur
        self._playlist       = []
        self._playlist_index = 0
        self._player_paused  = False
        self._volume         = 0.8
        self._seek_job       = None
        self._seek_rel       = 0.0
        self._track_length   = 0
        self._seek_offset    = 0.0
        self._play_start     = 0.0

        self.frame = self._build(parent)

    # ─────────────────────────────────────────
    # BUILD
    # ─────────────────────────────────────────
    def _build(self, parent):
        T    = self._t
        page = tk.Frame(parent, bg=T["BG"])

        # ── Fichier ──
        outer0, card0 = make_card(page, T, padx=16, pady=14)
        outer0.pack(fill="x", pady=(16, 0))

        tk.Label(card0, text="FICHIER AUDIO",
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(anchor="w")

        file_row = tk.Frame(card0, bg=T["CARD"])
        file_row.pack(fill="x", pady=(8, 0))

        entry_outer, _ = make_entry_row(file_row, T, "🎵", self.audio_path)
        entry_outer.pack(side="left", fill="x", expand=True, padx=(0, 12))

        pill_btn(file_row, "📂  Ouvrir", self._choose_file,
                 bg=ACCENT, hover="#8b84ff", w=130, h=38).pack(side="left")

        self.player_lbl = tk.Label(card0, text="Aucun fichier chargé",
                                   bg=T["CARD"], fg=T["MUTED"],
                                   font=("Helvetica", 9))
        self.player_lbl.pack(anchor="w", pady=(8, 0))

        # ── Barre de temps ──
        outer1, card1 = make_card(page, T, padx=16, pady=12)
        outer1.pack(fill="x", pady=(10, 0))

        time_row = tk.Frame(card1, bg=T["CARD"])
        time_row.pack(fill="x", pady=(0, 6))

        self.player_time_cur = tk.Label(time_row, text="0:00",
                                        bg=T["CARD"], fg=T["TEXT2"],
                                        font=("Helvetica", 8))
        self.player_time_cur.pack(side="left")

        self.player_time_tot = tk.Label(time_row, text="0:00",
                                        bg=T["CARD"], fg=T["MUTED"],
                                        font=("Helvetica", 8))
        self.player_time_tot.pack(side="right")

        prog_bg = tk.Frame(card1, bg=T["BORDER"], height=6)
        prog_bg.pack(fill="x")
        self.seek_canvas = tk.Canvas(prog_bg, height=6, bg=T["BORDER"],
                                     highlightthickness=0, cursor="hand2")
        self.seek_canvas.pack(fill="x", padx=1, pady=1)
        self.seek_canvas.bind("<Button-1>", self._on_seek_click)

        # ── Contrôles ──
        outer2, ctrl = make_card(page, T, padx=16, pady=14)
        outer2.pack(fill="x", pady=(10, 0))

        ctrl_center = tk.Frame(ctrl, bg=T["CARD"])
        ctrl_center.pack(expand=True)

        pill_btn(ctrl_center, "⏮  Préc.", self.prev,
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=100, h=40, fsize=9).pack(side="left", padx=4)
        pill_btn(ctrl_center, "⏪ -10s",  self.rewind,
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=90,  h=40, fsize=9).pack(side="left", padx=4)
        pill_btn(ctrl_center, "▶  Play",  self.play,
                 bg=SUCCESS, hover="#17a349", w=120, h=44, fsize=11).pack(side="left", padx=4)
        pill_btn(ctrl_center, "⏸  Pause", self.pause,
                 bg=WARN, hover="#d4a800", fg="#1a1a00",
                 w=120, h=44, fsize=11).pack(side="left", padx=4)
        pill_btn(ctrl_center, "⏹  Stop",  self.stop,
                 bg=ERROR, hover="#c94444", w=110, h=44, fsize=11).pack(side="left", padx=4)
        pill_btn(ctrl_center, "+10s ⏩",  self.forward,
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=90,  h=40, fsize=9).pack(side="left", padx=4)
        pill_btn(ctrl_center, "Suiv. ⏭", self.next,
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=100, h=40, fsize=9).pack(side="left", padx=4)

        # ── Volume ──
        outer3, vol_card = make_card(page, T, padx=16, pady=12)
        outer3.pack(fill="x", pady=(10, 0))

        vol_row = tk.Frame(vol_card, bg=T["CARD"])
        vol_row.pack(fill="x")

        tk.Label(vol_row, text="🔊  Volume",
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 9, "bold")).pack(side="left", padx=(0, 12))

        self.vol_slider = tk.Scale(
            vol_row, from_=0, to=100, orient="horizontal", length=260,
            bg=T["CARD"], fg=T["TEXT2"], troughcolor=T["BORDER"],
            highlightthickness=0, activebackground=ACCENT, sliderrelief="flat",
            command=self._on_volume_change,
        )
        self.vol_slider.set(int(self._volume * 100))
        self.vol_slider.pack(side="left")

        self.vol_label = tk.Label(vol_row, text=f"{int(self._volume*100)}%",
                                  bg=T["CARD"], fg=T["TEXT2"],
                                  font=("Helvetica", 9), width=4)
        self.vol_label.pack(side="left", padx=8)

        pill_btn(vol_row, "🔇 Mute", self._mute,
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=80, h=30, fsize=8).pack(side="left", padx=4)
        pill_btn(vol_row, "🔊 Max",  self._max_vol,
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=80, h=30, fsize=8).pack(side="left", padx=4)

        # ── Playlist ──
        outer4, pl_card = make_card(page, T, padx=16, pady=12)
        outer4.pack(fill="both", expand=True, pady=(10, 0))

        pl_header = tk.Frame(pl_card, bg=T["CARD"])
        pl_header.pack(fill="x", pady=(0, 8))

        tk.Label(pl_header, text="PLAYLIST",
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(side="left")

        pill_btn(pl_header, "➕  Ajouter", self._playlist_add,
                 bg=ACCENT, hover="#8b84ff", w=110, h=28, fsize=8
                 ).pack(side="right", padx=(4, 0))
        pill_btn(pl_header, "🗑  Vider", self._playlist_clear,
                 bg=T["BORDER"], hover="#3a3a55",
                 fg=T["TEXT2"], w=90, h=28, fsize=8).pack(side="right", padx=4)

        pl_frame = tk.Frame(pl_card, bg=T["CARD"])
        pl_frame.pack(fill="both", expand=True)

        pl_scroll = tk.Scrollbar(pl_frame)
        pl_scroll.pack(side="right", fill="y")

        self.playlist_box = tk.Listbox(
            pl_frame,
            bg=T["INPUT"], fg=T["TEXT2"],
            selectbackground=ACCENT, selectforeground=WHITE,
            font=("Helvetica", 9), relief="flat",
            activestyle="none", borderwidth=0,
            yscrollcommand=pl_scroll.set,
        )
        self.playlist_box.pack(fill="both", expand=True)
        pl_scroll.config(command=self.playlist_box.yview)
        self.playlist_box.bind("<Double-Button-1>", self._on_double_click)

        self.player_status = tk.Label(pl_card, text="",
                                      bg=T["CARD"], fg=T["MUTED"],
                                      font=("Helvetica", 9))
        self.player_status.pack(anchor="w", pady=(6, 0))

        return page

    # ─────────────────────────────────────────
    # MIXER
    # ─────────────────────────────────────────
    def _get_mixer(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return pygame.mixer
        except ImportError:
            self.player_status.config(
                text="✖  pygame non installé : pip install pygame", fg=ERROR)
            return None

    # ─────────────────────────────────────────
    # SEEK BAR
    # ─────────────────────────────────────────
    def _draw_seek(self, rel):
        w = self.seek_canvas.winfo_width()
        h = self.seek_canvas.winfo_height()
        if w < 2:
            return
        self.seek_canvas.delete("all")
        self.seek_canvas.create_rectangle(0, 0, w, h,
                                          fill=self._t["BORDER"], outline="")
        filled = int(w * rel)
        if filled > 0:
            self.seek_canvas.create_rectangle(0, 0, filled, h,
                                              fill=ACCENT, outline="")
        kx = max(4, min(filled, w - 4))
        self.seek_canvas.create_oval(kx - 5, 0, kx + 5, h,
                                     fill=WHITE, outline="")

    def _update_seek_bar(self):
        try:
            import pygame
            mixer = pygame.mixer
            if not mixer.get_init() or not mixer.music.get_busy():
                return
            elapsed = _time.time() - self._play_start
            pos_s   = self._seek_offset + elapsed
            if self._track_length > 0:
                rel = min(pos_s / self._track_length, 1.0)
                self._seek_rel = rel
                self._draw_seek(rel)
            self.player_time_cur.config(text=self._fmt_time(pos_s))
            self._seek_job = self.frame.after(500, self._update_seek_bar)
        except Exception:
            pass

    def _stop_seek_updater(self):
        if self._seek_job:
            self.frame.after_cancel(self._seek_job)
            self._seek_job = None

    def _on_seek_click(self, event):
        w = self.seek_canvas.winfo_width()
        if w < 2 or self._track_length <= 0:
            return
        rel      = event.x / w
        target_s = rel * self._track_length
        try:
            import pygame
            pygame.mixer.music.set_pos(target_s)
            self._seek_rel = rel
            self._draw_seek(rel)
            self.player_time_cur.config(text=self._fmt_time(target_s))
        except Exception as e:
            self.player_status.config(text=f"✖  {e}", fg=ERROR)

    # ─────────────────────────────────────────
    # TRACK
    # ─────────────────────────────────────────
    def _load_track(self, path):
        try:
            mixer = self._get_mixer()
            if not mixer:
                return
            mixer.music.load(path)
            mixer.music.set_volume(self._volume)
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(path)
                self._track_length = audio.info.length if audio else 0
            except Exception:
                self._track_length = 0
            self.audio_path.set(path)
            self.player_lbl.config(text=f"♪  {os.path.basename(path)}", fg=SUCCESS)
            self.player_time_tot.config(text=self._fmt_time(self._track_length))
            self.player_time_cur.config(text="0:00")
            self._draw_seek(0)
        except Exception as e:
            self.player_status.config(text=f"✖  {e}", fg=ERROR)

    def _play_current(self):
        if not self._playlist:
            return
        path = self._playlist[self._playlist_index]
        self._seek_offset = 0.0
        self._play_start  = _time.time()
        self._load_track(path)
        mixer = self._get_mixer()
        if mixer:
            mixer.music.play()
            self._player_paused = False
            self._stop_seek_updater()
            self._update_seek_bar()
            self.player_status.config(
                text=f"▶  {os.path.basename(path)}", fg=SUCCESS)
        self._refresh_playlist_box()

    # ─────────────────────────────────────────
    # PLAYLIST
    # ─────────────────────────────────────────
    def _refresh_playlist_box(self):
        self.playlist_box.delete(0, "end")
        for i, p in enumerate(self._playlist):
            prefix = "▶ " if i == self._playlist_index else "   "
            self.playlist_box.insert("end", f"{prefix}{os.path.basename(p)}")
        if self._playlist:
            self.playlist_box.selection_clear(0, "end")
            self.playlist_box.selection_set(self._playlist_index)
            self.playlist_box.see(self._playlist_index)

    def _playlist_add(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac")]
        )
        for p in paths:
            if p not in self._playlist:
                self._playlist.append(p)
        self._refresh_playlist_box()

    def _playlist_clear(self):
        self.stop()
        self._playlist.clear()
        self._playlist_index = 0
        self._refresh_playlist_box()
        self.player_lbl.config(text="Aucun fichier chargé", fg=self._t["MUTED"])
        self.player_time_cur.config(text="0:00")
        self.player_time_tot.config(text="0:00")
        self._draw_seek(0)

    def _on_double_click(self, event):
        sel = self.playlist_box.curselection()
        if sel:
            self._playlist_index = sel[0]
            self._play_current()

    # ─────────────────────────────────────────
    # VOLUME
    # ─────────────────────────────────────────
    def _on_volume_change(self, val):
        self._volume = int(val) / 100.0
        self.vol_label.config(text=f"{int(val)}%")
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self._volume)
        except Exception:
            pass

    def _mute(self):
        self.vol_slider.set(0)

    def _max_vol(self):
        self.vol_slider.set(100)

    # ─────────────────────────────────────────
    # CONTRÔLES PUBLICS
    # ─────────────────────────────────────────
    def open_file(self):
        """Ouvre un fichier via dialogue et l'ajoute à la playlist."""
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac")]
        )
        if path:
            self.audio_path.set(path)
            if path not in self._playlist:
                self._playlist.append(path)
                self._playlist_index = len(self._playlist) - 1
            else:
                self._playlist_index = self._playlist.index(path)
            self._load_track(path)
            self._refresh_playlist_box()

    def _choose_file(self):
        self.open_file()

    def play(self):
        path = self.audio_path.get().strip()
        if not path:
            return
        if path not in self._playlist:
            self._playlist.append(path)
            self._playlist_index = len(self._playlist) - 1
            self._refresh_playlist_box()
        else:
            self._playlist_index = self._playlist.index(path)
        self._seek_offset = 0.0
        self._play_current()

    def pause(self):
        try:
            import pygame
            if pygame.mixer.get_init():
                if pygame.mixer.music.get_busy() and not self._player_paused:
                    pygame.mixer.music.pause()
                    self._player_paused = True
                    self.player_status.config(text="⏸  En pause", fg=WARN)
                else:
                    pygame.mixer.music.unpause()
                    self._player_paused = False
                    self.player_status.config(text="▶  Lecture reprise", fg=SUCCESS)
                    self._stop_seek_updater()
                    self._update_seek_bar()
        except Exception:
            pass

    def stop(self):
        self._stop_seek_updater()
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._player_paused = False
        self.player_status.config(text="⏹  Arrêté", fg=self._t["MUTED"])
        self.player_time_cur.config(text="0:00")
        self._draw_seek(0)

    def prev(self):
        if not self._playlist:
            return
        self._playlist_index = (self._playlist_index - 1) % len(self._playlist)
        self._play_current()

    def next(self):
        if not self._playlist:
            return
        self._playlist_index = (self._playlist_index + 1) % len(self._playlist)
        self._play_current()

    def rewind(self):
        self._seek_relative(-10.0, "⏪  -10s")

    def forward(self):
        self._seek_relative(+10.0, "⏩  +10s")

    def _seek_relative(self, delta, label):
        try:
            if not self._playlist:
                return
            mixer = self._get_mixer()
            if not mixer or not mixer.music.get_busy():
                return
            elapsed = _time.time() - self._play_start
            pos_s   = self._seek_offset + elapsed
            total   = self._track_length
            target  = max(0.0, pos_s + delta)
            if total > 0:
                target = min(target, total - 1.0)
            path = self._playlist[self._playlist_index]
            self._stop_seek_updater()
            mixer.music.load(path)
            mixer.music.play(start=target)
            self._seek_offset   = target
            self._play_start    = _time.time()
            self._player_paused = False
            self._draw_seek(target / max(total, 1))
            self.player_time_cur.config(text=self._fmt_time(target))
            self.player_status.config(text=label, fg=SUCCESS)
            self._update_seek_bar()
        except Exception as e:
            self.player_status.config(text=f"✖ {e}", fg=ERROR)

    # ─────────────────────────────────────────
    # UTILS
    # ─────────────────────────────────────────
    @staticmethod
    def _fmt_time(seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60}:{seconds % 60:02d}"