# -*- coding: utf-8 -*-
"""
page_auth.py — Page de connexion / inscription de VoxText.
"""

import re
import os
import tkinter as tk
import requests

from constants import API_URL, ACCENT, ACCENT2, SUCCESS, ERROR
from ui_helpers import pill_btn, make_entry_row


class AuthPage:
    """Gère l'affichage et la logique de la page de connexion."""

    def __init__(self, parent, theme, on_login_success):
        """
        parent           : frame conteneur tkinter
        theme            : dict de couleurs actif
        on_login_success : callable(email) appelé après connexion réussie
        """
        self._t              = theme
        self._on_success     = on_login_success
        self.show_password   = False

        self.frame = self._build(parent)

    # ─────────────────────────────────────────
    # CONSTRUCTION
    # ─────────────────────────────────────────
    def _build(self, parent):
        T    = self._t
        page = tk.Frame(parent, bg=T["BG"])

        container = tk.Frame(page, bg=T["BG"])
        container.place(relx=0.5, rely=0.5, anchor="center")

        outer = tk.Frame(container, bg=T["BORDER"])
        outer.pack()

        card = tk.Frame(outer, bg=T["CARD"], padx=30, pady=30)
        card.pack(padx=1, pady=1)

        tk.Label(card, text="🔐 Connexion",
                 bg=T["CARD"], fg=T["TEXT"],
                 font=("Helvetica", 18, "bold")).pack(pady=(0, 20))

        # Champ email
        self.login_email = tk.StringVar()
        self.login_email.trace_add("write", self._validate_email)
        email_outer, _ = make_entry_row(card, T, "✉", self.login_email)
        email_outer.pack(fill="x", pady=5)

        # Champ mot de passe
        self.login_pass = tk.StringVar()
        pass_outer = tk.Frame(card, bg=T["CARD"],
                              highlightbackground=T["BORDER"],
                              highlightthickness=1)
        pass_outer.pack(fill="x", pady=5)

        tk.Label(pass_outer, text="🔒",
                 bg=T["CARD"], fg=T["MUTED"]).pack(side="left", padx=8)

        self.pass_entry = tk.Entry(
            pass_outer, textvariable=self.login_pass,
            show="*", bd=0,
            bg=T["CARD"], fg=T["TEXT"],
            insertbackground=T["TEXT"],
        )
        self.pass_entry.pack(side="left", fill="x", expand=True, padx=5, pady=8)

        self.eye_btn = tk.Label(pass_outer, text="👁",
                                bg=T["CARD"], fg=T["MUTED"], cursor="hand2")
        self.eye_btn.pack(side="right", padx=8)
        self.eye_btn.bind("<Button-1>", self._toggle_password)

        # Statut
        self.login_status = tk.Label(card, text="", fg=ERROR,
                                     bg=T["CARD"], font=("Helvetica", 9))
        self.login_status.pack(pady=(10, 5))

        # Boutons
        btn_row = tk.Frame(card, bg=T["CARD"])
        btn_row.pack(pady=10)

        pill_btn(btn_row, "Se connecter", self._login,
                 bg=ACCENT, w=140).pack(side="left", padx=5)
        pill_btn(btn_row, "Créer compte", self._register,
                 bg=ACCENT2, w=140).pack(side="left", padx=5)
        pill_btn(card,"Mot de passe oublié", self.forgot_password, bg=T["BORDER"],
            w=200
        ).pack(pady=5)

        self.pass_entry.bind("<Return>", lambda e: self._login())

        return page

    # ─────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────

    def forgot_password(self):
        import requests

        email = self.login_email.get().strip()

        res = requests.post(
            f"{API_URL}/forgot-password",
            json={"email": email}
        ).json()

        if res.get("error"):
            self.login_status.config(text="Email introuvable ❌", fg=ERROR)
            return

        print("RESET LINK:", res.get("reset_link"))

        self.login_status.config(
            text="Lien envoyé (voir console)",
            fg=SUCCESS
        )

    # ─────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────
    def _validate_email(self, *args):
        email   = self.login_email.get()
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not email:
            self.login_status.config(text="")
        elif re.match(pattern, email):
            self.login_status.config(text="✔ Email valide", fg=SUCCESS)
        else:
            self.login_status.config(text="✖ Email invalide", fg=ERROR)

    def _toggle_password(self, event=None):
        self.show_password = not self.show_password
        if self.show_password:
            self.pass_entry.config(show="")
            self.eye_btn.config(text="🙈")
        else:
            self.pass_entry.config(show="*")
            self.eye_btn.config(text="👁")

    # ─────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────

    def _login(self):
        email = self.login_email.get().strip()
        password = self.login_pass.get().strip()

        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            self.login_status.config(text="Email invalide ❌", fg=ERROR)
            return

        self.login_status.config(text="Connexion...", fg=ACCENT)
        self.frame.update()

        try:
            res = requests.post(
                f"{API_URL}/login",
                json={"email": email, "password": password},
                timeout=10,
            ).json()

            # 🔥 gestion erreurs PRO
            if res.get("error"):
                err = res["error"]

                if err == "email_not_verified":
                    self.login_status.config(text="Vérifiez votre email 📧", fg=ERROR)

                elif err == "invalid_password":
                    self.login_status.config(text="Mot de passe incorrect ❌", fg=ERROR)

                elif err == "user_not_found":
                    self.login_status.config(text="Utilisateur introuvable ❌", fg=ERROR)

                else:
                    self.login_status.config(text="Erreur ❌", fg=ERROR)

                return

            # ✅ SUCCESS
            with open("session.txt", "w") as f:
                f.write(email)

            self.login_status.config(text="✔ Connexion réussie", fg=SUCCESS)
            # ✅ SUCCESS
            with open("session.txt", "w") as f:
                f.write(email)
            
            import billing
            billing.set_email(email)  # ← ajoute cette ligne
            
            self.login_status.config(text="✔ Connexion réussie", fg=SUCCESS)
            self._on_success(email)
            
        except requests.exceptions.ConnectionError:
            self.login_status.config(text="Serveur inaccessible ❌", fg=ERROR)

        except Exception as e:
            self.login_status.config(text=f"Erreur: {e}", fg=ERROR)


    def _register(self):
        email    = self.login_email.get()
        password = self.login_pass.get()

        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            self.login_status.config(text="Email invalide ❌", fg=ERROR)
            return

        try:
            res = requests.post(
                f"{API_URL}/register",
                json={"email": email, "password": password},
                timeout=10,
            ).json()

            if "error" in res:
                self.login_status.config(text=res["error"], fg=ERROR)
            else:
                self.login_status.config(text="Compte créé ✔", fg=SUCCESS)
        except Exception as e:
            self.login_status.config(text=f"Erreur: {e}", fg=ERROR)
