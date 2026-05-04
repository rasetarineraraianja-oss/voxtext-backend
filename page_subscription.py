# -*- coding: utf-8 -*-
"""
page_subscription.py — Page abonnement VoxText : Stripe + PayPal (production)
"""

import threading
import webbrowser
import tkinter as tk
import requests

import billing
from constants import API_URL, ACCENT, SUCCESS, ERROR, WHITE, PRO_COLOR
from ui_helpers import pill_btn, make_card, make_entry_row

PAYPAL_COLOR  = "#003087"
PAYPAL_HOVER  = "#002060"


class SubscriptionPage:

    def __init__(self, parent, theme, get_user_fn, is_pro_fn, update_badge_fn):
        self._t           = theme
        self.get_user     = get_user_fn
        self.is_pro       = is_pro_fn
        self.update_badge = update_badge_fn
        self.sub_status   = None
        self._email_var   = tk.StringVar()
        self._polling     = False
        self._poll_count  = 0
        self._poll_email  = ""
        self._poll_max    = 36      # 36 × 5s = 3 min max

        self.frame = self._build(parent)

    # ─────────────────────────────────────────
    # BUILD
    # ─────────────────────────────────────────
    def _build(self, parent):
        T    = self._t
        page = tk.Frame(parent, bg=T["BG"])

        self.sub_canvas = tk.Canvas(page, bg=T["BG"], highlightthickness=0)
        sb = tk.Scrollbar(page, orient="vertical", command=self.sub_canvas.yview)
        self.sub_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.sub_canvas.pack(side="left", fill="both", expand=True)

        self.scroll_frame = tk.Frame(self.sub_canvas, bg=T["BG"])
        win_id = self.sub_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.scroll_frame.bind("<Configure>",
            lambda e: self.sub_canvas.configure(scrollregion=self.sub_canvas.bbox("all")))
        self.sub_canvas.bind("<Configure>",
            lambda e: self.sub_canvas.itemconfig(win_id, width=e.width))
        self.sub_canvas.bind_all("<MouseWheel>",
            lambda e: self.sub_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._fill()
        return page

    def _fill(self):
        T = self._t
        f = self.scroll_frame

        tk.Label(f, text="💳  Gérer mon abonnement",
                 bg=T["BG"], fg=T["TEXT"],
                 font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(20,4), padx=20)
        tk.Label(f, text="Méthode de paiement.",
                 bg=T["BG"], fg=T["MUTED"],
                 font=("Helvetica", 10)).pack(anchor="w", pady=(0,16), padx=20)

        cards = tk.Frame(f, bg=T["BG"])
        cards.pack(fill="x", padx=20)
        self._card_free(cards)
        self._card_pro(cards)

        action = tk.Frame(f, bg=T["BG"])
        action.pack(fill="x", pady=(16, 60), padx=20)
        self._activation_area(action)

    def reload(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self._fill()
        self.sub_canvas.update_idletasks()
        self.sub_canvas.configure(scrollregion=self.sub_canvas.bbox("all"))

    # ─────────────────────────────────────────
    # CARTES
    # ─────────────────────────────────────────
    def _card_free(self, parent):
        T = self._t
        user = self.get_user()
        plan = user.get("plan", "free") if user else "free"
        active = (plan == "free")

        outer = tk.Frame(parent, bg=ACCENT if active else T["BORDER"])
        outer.pack(side="left", fill="both", expand=True, padx=(0,8))
        inner = tk.Frame(outer, bg=T["CARD"], padx=20, pady=20)
        inner.pack(fill="both", expand=True, padx=2 if active else 1, pady=2 if active else 1)

        if active:
            tk.Label(inner, text="✔ PLAN ACTUEL", bg=ACCENT, fg=WHITE,
                     font=("Helvetica", 8, "bold"), padx=8, pady=3).pack(anchor="w", pady=(0,8))

        tk.Label(inner, text="🆓  Gratuit", bg=T["CARD"], fg=T["TEXT"],
                 font=("Helvetica", 14, "bold")).pack(anchor="w")
        tk.Label(inner, text="0 € / mois", bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 20, "bold")).pack(anchor="w", pady=(4,12))

        for feat in [
            f"✔  {billing.FREE_LIMIT} transcriptions d'essai",
            "✔  Lecteur audio intégré",
            "✔  Téléchargement (yt-dlp)",
            "✖  Transcriptions illimitées",
            "✖  Support prioritaire",
        ]:
            color = T["TEXT2"] if feat.startswith("✔") else T["MUTED"]
            tk.Label(inner, text=feat, bg=T["CARD"], fg=color,
                     font=("Helvetica", 9), anchor="w").pack(anchor="w", pady=2)

        if active:
            rem = billing.remaining_free()
            tk.Label(inner,
                     text=f"Essais utilisés : {billing.FREE_LIMIT-rem} / {billing.FREE_LIMIT}",
                     bg=T["CARD"], fg=T["MUTED"],
                     font=("Helvetica", 8)).pack(anchor="w", pady=(12,4))
            pb = tk.Frame(inner, bg=T["BORDER"], height=6)
            pb.pack(fill="x")
            pct = (billing.FREE_LIMIT - rem) / billing.FREE_LIMIT
            tk.Frame(pb, bg=ACCENT if rem > 0 else ERROR, height=6
                     ).place(x=0, y=0, relheight=1, relwidth=pct)

    def _card_pro(self, parent):
        T = self._t
        user = self.get_user()
        plan = user.get("plan", "free") if user else "free"
        active = (plan == "pro")

        outer = tk.Frame(parent, bg=PRO_COLOR if active else T["BORDER"])
        outer.pack(side="left", fill="both", expand=True, padx=(8,0))
        inner = tk.Frame(outer, bg=T["CARD"], padx=20, pady=20)
        inner.pack(fill="both", expand=True, padx=2 if active else 1, pady=2 if active else 1)

        if active:
            provider = user.get("payment_provider", "") if user else ""
            badge    = f"⭐ PLAN ACTUEL" + (f"  via {provider.upper()}" if provider else "")
            tk.Label(inner, text=badge, bg=PRO_COLOR, fg=WHITE,
                     font=("Helvetica", 8, "bold"), padx=8, pady=3).pack(anchor="w", pady=(0,8))

        tk.Label(inner, text="⭐  Pro", bg=T["CARD"], fg=T["TEXT"],
                 font=("Helvetica", 14, "bold")).pack(anchor="w")
        tk.Label(inner, text=f"{billing.PRO_PRICE:.2f} € / mois",
                 bg=T["CARD"], fg=PRO_COLOR,
                 font=("Helvetica", 20, "bold")).pack(anchor="w", pady=(4,12))

        for feat in [
            "✔  Transcriptions illimitées",
            "✔  Lecteur audio intégré",
            "✔  Téléchargement (yt-dlp)",
            "✔  Priorité de traitement",
            "✔  Support prioritaire",
        ]:
            tk.Label(inner, text=feat, bg=T["CARD"], fg=T["TEXT2"],
                     font=("Helvetica", 9), anchor="w").pack(anchor="w", pady=2)

        if active and user:
            expiry = user.get("pro_expires", "")
            if expiry:
                try:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(expiry).strftime("%d/%m/%Y")
                except Exception:
                    pass
                tk.Label(inner, text=f"Valide jusqu'au : {expiry}",
                         bg=T["CARD"], fg=SUCCESS,
                         font=("Helvetica", 8, "bold")).pack(anchor="w", pady=(12,2))

    # ─────────────────────────────────────────
    # ZONE ACTIVATION
    # ─────────────────────────────────────────
    def _activation_area(self, parent):
        T    = self._t
        user = self.get_user()
        plan = user.get("plan", "free") if user else "free"

        outer, card = make_card(parent, T, padx=20, pady=20)
        outer.pack(fill="x")

        if plan == "free":
            self._form_upgrade(card, T)
        else:
            self._form_pro_active(card, T, user)

    def _form_upgrade(self, card, T):
        tk.Label(card, text="CHOISISSEZ VOTRE MÉTHODE DE PAIEMENT",
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(anchor="w", pady=(0,12))

        # Email
        email_row = tk.Frame(card, bg=T["CARD"])
        email_row.pack(fill="x", pady=(0,14))

        tk.Label(email_row, text="✉  Votre email :",
                 bg=T["CARD"], fg=T["TEXT2"],
                 font=("Helvetica", 9)).pack(side="left", padx=(0,10))

        entry_outer, _ = make_entry_row(email_row, T, "✉", self._email_var, width=32)
        entry_outer.pack(side="left", fill="x", expand=True)

        # ── Boutons paiement côte à côte ──
        btn_row = tk.Frame(card, bg=T["CARD"])
        btn_row.pack(anchor="w", pady=(0,4))

        # Stripe (carte)
        self._stripe_btn = pill_btn(
            btn_row,
            f"💳  Payer par carte  {billing.PRO_PRICE:.2f} €/mois",
            lambda: self._pay("stripe"),
            bg="#635bff", hover="#7a73ff",
            w=260, h=44, fsize=10,
        )
        self._stripe_btn.pack(side="left", padx=(0,12))

        # PayPal
        self._paypal_btn = pill_btn(
            btn_row,
            f"🅿  Payer via PayPal  {billing.PRO_PRICE:.2f} €/mois",
            lambda: self._pay("paypal"),
            bg=PAYPAL_COLOR, hover=PAYPAL_HOVER,
            w=260, h=44, fsize=10,
        )
        self._paypal_btn.pack(side="left")

        # Statut + polling
        self.sub_status = tk.Label(card, text="", bg=T["CARD"], fg=T["MUTED"],
                                   font=("Helvetica", 9))
        self.sub_status.pack(anchor="w", pady=(10,0))

        self._poll_label = tk.Label(card, text="", bg=T["CARD"], fg=ACCENT,
                                    font=("Helvetica", 8, "italic"))
        self._poll_label.pack(anchor="w", pady=(2,0))

        # Badges sécurité
        badges_row = tk.Frame(card, bg=T["CARD"])
        badges_row.pack(anchor="w", pady=(10,0))
        for badge in ["🔒 SSL sécurisé", "💳 Visa / Mastercard / PayPal", "↩ Annulable à tout moment"]:
            tk.Label(badges_row, text=badge, bg=T["BORDER"], fg=T["TEXT2"],
                     font=("Helvetica", 8), padx=8, pady=4).pack(side="left", padx=(0,6))

        tk.Label(card,
                 text="Vous serez redirigé vers la page sécurisée Stripe ou PayPal.",
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8)).pack(anchor="w", pady=(8,0))

    def _form_pro_active(self, card, T, user):
        tk.Label(card, text="VOTRE ABONNEMENT PRO",
                 bg=T["CARD"], fg=T["MUTED"],
                 font=("Helvetica", 8, "bold")).pack(anchor="w", pady=(0,10))

        expiry   = user.get("pro_expires", "—") if user else "—"
        email_v  = user.get("email", "—")       if user else "—"
        provider = user.get("payment_provider", "—") if user else "—"

        if expiry and expiry != "—":
            try:
                from datetime import datetime
                expiry = datetime.fromisoformat(expiry).strftime("%d/%m/%Y")
            except Exception:
                pass

        for label, value in [
            ("✔ Statut",                  "Actif ✔"),
            ("💳 Méthode",               provider.upper() if provider != "—" else "—"),
            ("📅 Prochain renouvellement", expiry),
            ("✉ Compte",                  email_v),
        ]:
            row = tk.Frame(card, bg=T["CARD"])
            row.pack(anchor="w", pady=2)
            tk.Label(row, text=f"{label} :", bg=T["CARD"], fg=T["MUTED"],
                     font=("Helvetica", 9), width=28, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=T["CARD"], fg=T["TEXT"],
                     font=("Helvetica", 9, "bold")).pack(side="left")

        self.sub_status = tk.Label(card, text="", bg=T["CARD"], fg=T["MUTED"],
                                   font=("Helvetica", 9))
        self.sub_status.pack(anchor="w", pady=(10,6))

        tk.Label(card, text="Pour gérer ou annuler votre abonnement :",
                 bg=T["CARD"], fg=T["MUTED"], font=("Helvetica", 8)).pack(anchor="w")

        links_row = tk.Frame(card, bg=T["CARD"])
        links_row.pack(anchor="w", pady=(6,0))

        stripe_lnk = tk.Label(links_row, text="🔗  Portail Stripe",
                               bg=T["CARD"], fg="#635bff",
                               font=("Helvetica", 9, "underline"), cursor="hand2")
        stripe_lnk.pack(side="left", padx=(0,16))
        stripe_lnk.bind("<Button-1>", lambda e: self._open_portal("stripe"))

        paypal_lnk = tk.Label(links_row, text="🅿  Gérer sur PayPal",
                               bg=T["CARD"], fg=PAYPAL_COLOR,
                               font=("Helvetica", 9, "underline"), cursor="hand2")
        paypal_lnk.pack(side="left")
        paypal_lnk.bind("<Button-1>", lambda e: self._open_portal("paypal"))

    # ─────────────────────────────────────────
    # PAIEMENT
    # ─────────────────────────────────────────
    def _pay(self, provider: str):
        email = self._email_var.get().strip()
        if not email or "@" not in email:
            self.sub_status.config(text="✖  Entrez un e-mail valide.", fg=ERROR)
            return

        label = "Stripe" if provider == "stripe" else "PayPal"
        self.sub_status.config(text=f"⏳  Connexion à {label}...", fg=ACCENT)

        # Désactiver les deux boutons
        for btn in [self._stripe_btn, self._paypal_btn]:
            btn._disabled = True
            btn._draw("#888888")
        self.frame.update()

        def run():
            try:
                res  = requests.post(
                    f"{API_URL}/create-checkout-session/{provider}",
                    json={"email": email}, timeout=15,
                )
                data = res.json()

                if "error" in data:
                    msgs = {
                        "user_not_found": "Utilisateur introuvable. Créez d'abord un compte.",
                        "already_pro":    "Vous êtes déjà en plan Pro !",
                        "missing_email":  "Email manquant.",
                    }
                    msg = msgs.get(data["error"], f"Erreur : {data['error']}")
                    self.frame.after(0, lambda m=msg: self.sub_status.config(
                        text=f"✖  {m}", fg=ERROR))
                    self.frame.after(0, self._re_enable_btns)
                    return

                url = data.get("checkout_url")
                if not url:
                    self.frame.after(0, lambda: self.sub_status.config(
                        text="✖  URL de paiement introuvable.", fg=ERROR))
                    self.frame.after(0, self._re_enable_btns)
                    return

                webbrowser.open(url)
                self.frame.after(0, lambda lbl=label: self.sub_status.config(
                    text=f"✔  Page {lbl} ouverte dans votre navigateur.", fg=SUCCESS))
                self.frame.after(0, lambda: self._start_polling(email))

            except requests.exceptions.ConnectionError:
                self.frame.after(0, lambda: self.sub_status.config(
                    text="✖  Serveur inaccessible.", fg=ERROR))
                self.frame.after(0, self._re_enable_btns)
            except Exception as e:
                self.frame.after(0, lambda err=e: self.sub_status.config(
                    text=f"✖  Erreur : {err}", fg=ERROR))
                self.frame.after(0, self._re_enable_btns)

        threading.Thread(target=run, daemon=True).start()

    def _re_enable_btns(self):
        if hasattr(self, "_stripe_btn"):
            self._stripe_btn._disabled = False
            self._stripe_btn._draw("#635bff")
        if hasattr(self, "_paypal_btn"):
            self._paypal_btn._disabled = False
            self._paypal_btn._draw(PAYPAL_COLOR)

    def _open_portal(self, provider: str):
        if provider == "stripe":
            webbrowser.open("https://billing.stripe.com/p/login/test_4gMeVdae2dcc78IdPlbQY00")
        else:
            webbrowser.open("https://www.paypal.com/myaccount/autopay/")

    # ─────────────────────────────────────────
    # POLLING
    # ─────────────────────────────────────────
    def _start_polling(self, email: str):
        if self._polling:
            return
        self._polling    = True
        self._poll_count = 0
        self._poll_email = email
        if hasattr(self, "_poll_label"):
            self._poll_label.config(text="🔄  En attente de confirmation du paiement...")
        self._poll_tick()

    def _poll_tick(self):
        if not self._polling:
            return
        self._poll_count += 1
        if self._poll_count > self._poll_max:
            self._polling = False
            if hasattr(self, "_poll_label"):
                self._poll_label.config(
                    text="⚠  Délai dépassé. Redémarrez l'app si le paiement a réussi.")
            return

        def check():
            try:
                res  = requests.get(f"{API_URL}/user/{self._poll_email}", timeout=5)
                user = res.json()
                if user.get("plan") == "pro":
                    self.frame.after(0, self._on_pro_confirmed)
                else:
                    self.frame.after(5000, self._poll_tick)
            except Exception:
                self.frame.after(5000, self._poll_tick)

        threading.Thread(target=check, daemon=True).start()

    def _on_pro_confirmed(self):
        self._polling = False
        if hasattr(self, "_poll_label"):
            self._poll_label.config(text="")
        self.sub_status.config(text="🎉  Plan Pro activé avec succès !", fg=SUCCESS)
        self.update_badge()
        self.frame.after(1500, self.reload)
