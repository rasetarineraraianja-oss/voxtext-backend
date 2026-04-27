# -*- coding: utf-8 -*-
"""
api.py — Serveur FastAPI de VoxText.

Lancement : uvicorn api:app --reload
"""

import uuid
import bcrypt
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
import stripe
from starlette.responses import JSONResponse
from database import get_connection, activate_pro as db_activate_pro

# =============================================================
# APP
# =============================================================
app = FastAPI(title="VoxText API", version="1.0.0")

# =============================================================
# STRIPE WEBHOOK
# =============================================================
ENDPOINT_SECRET = "whsec_2f0d49755e804edb2ebe863b259b21659360426bc5030653ddeb95232ea012d4"   # ← remplacez par votre clé Stripe

# =============================================================
# EMAIL
# =============================================================
from pydantic import BaseModel

class ForgotPasswordRequest(BaseModel):
    email: str


def forgot_password(data: ForgotPasswordRequest):
    email = data.email.strip().lower()

    if not email:
        return {"error": "missing_email"}

    from database import get_connection
    import uuid

    token = str(uuid.uuid4())

    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if not user:
            return {"error": "user_not_found"}

        conn.execute(
            "UPDATE users SET reset_token = ? WHERE email = ?",
            (token, email)
        )

    link = f"https://voxtext-backend-r6l8.onrender.com/reset-password?token={token}"

    print("RESET LINK:", link)  # dev

    return {"status": "ok", "reset_link": link}

from pydantic import BaseModel

class ResetPasswordRequest(BaseModel):
    token: str
    password: str


def reset_password(data: ResetPasswordRequest):
    import bcrypt
    from database import get_connection

    token = data.token
    new_password = data.password

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE reset_token = ?",
            (token,)
        ).fetchone()

        if not user:
            return {"error": "invalid_token"}

        conn.execute("""
            UPDATE users
            SET password = ?, reset_token = NULL
            WHERE reset_token = ?
        """, (hashed, token))

    return {"status": "password_updated"}

def send_verification_email(to_email, link):
    sender = "tonemail@gmail.com"
    password = "APP_PASSWORD"  # ⚠️ mot de passe application

    subject = "Vérification VoxText"
    body = f"Clique ici pour activer ton compte:\n{link}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)





# =============================================================
# SCHÉMAS
# =============================================================
class AuthData(BaseModel):
    email: str
    password: str


# =============================================================
# ROUTES AUTH
# =============================================================
class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AccessRequest(BaseModel):
    email: str


def register(data: RegisterRequest):
    try:
        # 🔥 Nettoyage
        email = data.email.strip().lower()
        password = data.password.strip()

        if not email or not password:
            return {"error": "missing_fields"}

        # 🔐 Hash password
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # 🧠 Fingerprint
        device_fp = str(uuid.uuid4())

        # 🔑 Token vérification email
        verify_token = str(uuid.uuid4())

        now = datetime.now().isoformat()

        with get_connection() as conn:
            # 🔍 Vérifier doublon
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if existing:
                return {
                    "error": "email_exists",
                    "message": "Compte déjà existant"
                }

            # ✅ INSERT COMPLET
            conn.execute("""
                INSERT INTO users (
                    id,
                    email,
                    password,
                    plan,
                    created_at,
                    device_fingerprint,
                    last_seen,
                    is_verified,
                    verify_token
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                email,
                hashed,
                "free",
                now,
                device_fp,
                now,
                0,               # 🔥 email non vérifié
                verify_token
            ))

        # 📧 Lien de vérification (dev)
        verify_link = f"http://127.0.0.1:8000/verify?token={verify_token}"
        print("VERIFY LINK:", verify_link)

        return {
            "status": "ok",
            "message": "Compte créé. Vérifiez votre email.",
            "verify_link": verify_link  # 🔥 utile en dev
        }

    except Exception as e:
        return {"error": str(e)}



def login(data: LoginRequest):
    """Authentifie un utilisateur et retourne ses infos."""
    try:
        # 🔥 Nettoyage
        email = data.email.strip().lower()
        password = data.password.strip()

        if not email or not password:
            return {"error": "missing_fields"}

        with get_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

        # ❌ user inexistant
        if not user:
            return {"error": "user_not_found"}

        # ❌ pas de password (ancien compte)
        if not user["password"]:
            return {"error": "no_password"}

        # ❌ email non vérifié 🔥
        if "is_verified" in user.keys() and user["is_verified"] == 0:
            return {
                "error": "email_not_verified",
                "message": "Veuillez vérifier votre email"
            }

        # ❌ mauvais password
        if not bcrypt.checkpw(password.encode(), user["password"].encode()):
            return {"error": "invalid_password"}

        # 🔄 update last_seen
        now = datetime.now().isoformat()
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_seen = ? WHERE email = ?",
                (now, email)
            )

        # ✅ succès
        return {
            "status": "ok",
            "email": email,
            "plan": user["plan"],
            "pro_expires": user["pro_expires"]
            if "pro_expires" in user.keys() else None,
        }

    except Exception as e:
        return {"error": str(e)}


# =============================================================
# ROUTES UTILISATEUR
# =============================================================

def get_user(email: str):
    """Retourne les informations d'un utilisateur depuis la DB."""
    email = email.strip().lower()

    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, email, plan, pro_expires, created_at "
            "FROM users WHERE email = ?",
            (email,)
        ).fetchone()

    if not user:
        return {"error": "not_found"}

    return {
        "email":       user["email"],
        "plan":        user["plan"],
        "pro_expires": user["pro_expires"],
        "created_at":  user["created_at"],
    }



def activate_pro_route(email: str):
    """
    Active le plan Pro pour un utilisateur (simulation de paiement).
    En production, utilisez le webhook Stripe à la place.
    """
    email = email.strip().lower()

    with get_connection() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

    if not user:
        return {"error": "user_not_found"}

    expiry = datetime.now() + timedelta(days=30)
    db_activate_pro(email)              # délègue à database.py

    return {
        "status":  "pro_activated",
        "email":   email,
        "expires": expiry.isoformat(),
    }


# =============================================================
# ROUTE VÉRIFICATION D'ACCÈS
# =============================================================

def check_access(data: AccessRequest):
    import billing

    email = data.email.strip().lower()

    with get_connection() as conn:
        user = conn.execute(
            "SELECT plan, pro_expires FROM users WHERE email = ?", (email,)
        ).fetchone()

    if not user:
        return {"error": "user_not_found"}

    # PRO
    if user["plan"] == "pro":
        expires = user["pro_expires"]
        if expires:
            try:
                if datetime.now() <= datetime.fromisoformat(expires):
                    return {"status": "ok", "access": "full"}
            except Exception:
                pass

        # downgrade si expiré
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET plan = 'free' WHERE email = ?", (email,)
            )

    # FREE
    remaining = billing.remaining_free()
    if remaining <= 0:
        return {"error": "limit_reached"}

    return {
        "status": "ok",
        "access": "limited",
        "remaining": remaining
    }

