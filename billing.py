# -*- coding: utf-8 -*-
"""
billing.py — Version corrigée compatible API + database local
"""

from datetime import datetime, timedelta

import database as db

FREE_LIMIT = 3
PRO_PRICE  = 4.99

# état local simple
_usage       = 0
_plan        = "free"
_pro_expires = None
_email       = ""


# ─────────────────────────────────────────
# TÉLÉCHARGEMENTS
# ─────────────────────────────────────────

def record_download(url=None, fmt=None, status=None, error_msg=None):
    """Enregistre un téléchargement dans le log."""
    try:
        print(f"[DOWNLOAD] url={url} | fmt={fmt} | status={status} | error={error_msg}")
        with open("downloads.log", "a", encoding="utf-8") as f:
            f.write(f"{url} | {fmt} | {status} | {error_msg}\n")
    except Exception as e:
        print("Erreur record_download:", e)


# ─────────────────────────────────────────
# PLAN
# ─────────────────────────────────────────

def get_plan():
    global _plan, _pro_expires

    if _plan == "pro" and _pro_expires:
        if datetime.now() > _pro_expires:
            _plan        = "free"
            _pro_expires = None

    return _plan


# ─────────────────────────────────────────
# QUOTA
# ─────────────────────────────────────────

def can_transcribe():
    if get_plan() == "pro":
        return True
    return _usage < FREE_LIMIT


def record_transcription(
    filename="",
    language="auto",
    duration_sec=0.0,
    char_count=0,
):
    """Incrémente le compteur et enregistre en DB."""
    global _usage

    _usage += 1

    try:
        db.record_transcription(
            user_id="local_user",
            filename=filename,
            language=language,
            char_count=char_count,
            status="success",
        )
    except Exception as e:
        print("Erreur DB record_transcription:", e)


def record_transcription_error(filename="", error_msg=""):
    """Enregistre une erreur de transcription en DB."""
    try:
        db.record_transcription(
            user_id="local_user",
            filename=filename,
            language="auto",
            char_count=0,
            status="error",
        )
    except Exception as e:
        print("Erreur DB record_transcription_error:", e)


def remaining_free():
    if get_plan() == "pro":
        return FREE_LIMIT
    return max(0, FREE_LIMIT - _usage)


# ─────────────────────────────────────────
# PRO
# ─────────────────────────────────────────

def activate_pro(email):
    global _plan, _pro_expires, _email

    if not email or "@" not in email:
        return False

    _plan        = "pro"
    _email       = email
    _pro_expires = datetime.now() + timedelta(days=30)
    return True


def cancel_pro():
    global _plan, _pro_expires
    _plan        = "free"
    _pro_expires = None


def get_pro_expiry_str():
    if _pro_expires:
        return _pro_expires.strftime("%d/%m/%Y")
    return ""


def get_email():
    return _email


# ─────────────────────────────────────────
# HISTORIQUE
# ─────────────────────────────────────────

def get_history(limit=50):
    return db.get_transcription_history("local_user", limit)


# ─────────────────────────────────────────
# RÉSUMÉ
# ─────────────────────────────────────────

def billing_summary():
    plan = get_plan()
    used = _usage
    rem  = remaining_free()

    return {
        "plan":      plan,
        "used":      used,
        "remaining": rem if plan == "free" else "∞",
        "limit":     FREE_LIMIT if plan == "free" else "∞",
        "expiry":    get_pro_expiry_str(),
        "email":     get_email(),
        "price":     PRO_PRICE,
    }