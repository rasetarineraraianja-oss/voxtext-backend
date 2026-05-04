# -*- coding: utf-8 -*-
"""
billing.py — Version corrigée avec compteur d'essais via API Render
"""

from datetime import datetime, timedelta
import requests

FREE_LIMIT = 3
PRO_PRICE  = 4.99

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
API_URL = "https://voxtext-backend-r6l8.onrender.com"

_email       = ""
_plan        = "free"
_pro_expires = None
_usage       = 0  # cache local, mis à jour depuis l'API


# ─────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────
def set_email(email):
    global _email
    _email = email
    _sync_from_api()


def get_email():
    return _email


# ─────────────────────────────────────────
# SYNC DEPUIS L'API
# ─────────────────────────────────────────
def _sync_from_api():
    global _plan, _pro_expires, _usage
    if not _email:
        return
    try:
        res = requests.get(f"{API_URL}/user/{_email}", timeout=5)
        data = res.json()
        _plan        = data.get("plan", "free")
        _pro_expires = data.get("pro_expires")
        _usage       = data.get("used_trials", 0)
    except Exception as e:
        print(f"[billing] sync erreur : {e}")


# ─────────────────────────────────────────
# PLAN
# ─────────────────────────────────────────
def get_plan():
    global _plan, _pro_expires
    if _plan == "pro" and _pro_expires:
        try:
            if datetime.now() > datetime.fromisoformat(_pro_expires):
                _plan        = "free"
                _pro_expires = None
        except Exception:
            pass
    return _plan


# ─────────────────────────────────────────
# QUOTA
# ─────────────────────────────────────────
def can_transcribe():
    _sync_from_api()
    if get_plan() == "pro":
        return True
    return _usage < FREE_LIMIT


def remaining_free():
    if get_plan() == "pro":
        return FREE_LIMIT
    return max(0, FREE_LIMIT - _usage)


# ─────────────────────────────────────────
# ENREGISTREMENT TRANSCRIPTION
# ─────────────────────────────────────────
def record_transcription(filename="", language="auto",
                         duration_sec=0.0, char_count=0):
    global _usage
    _usage += 1

    # Incrémenter used_trials dans l'API
    if _email:
        try:
            requests.post(f"{API_URL}/increment-trials",
                          json={"email": _email}, timeout=5)
        except Exception as e:
            print(f"[billing] increment-trials erreur : {e}")


def record_transcription_error(filename="", error_msg=""):
    pass


# ─────────────────────────────────────────
# TÉLÉCHARGEMENTS
# ─────────────────────────────────────────
def record_download(url=None, fmt=None, status=None, error_msg=None):
    try:
        print(f"[DOWNLOAD] url={url} | fmt={fmt} | status={status} | error={error_msg}")
        with open("downloads.log", "a", encoding="utf-8") as f:
            f.write(f"{url} | {fmt} | {status} | {error_msg}\n")
    except Exception as e:
        print("Erreur record_download:", e)


# ─────────────────────────────────────────
# PRO
# ─────────────────────────────────────────
def activate_pro(email):
    global _plan, _pro_expires, _email
    if not email or "@" not in email:
        return False
    _plan        = "pro"
    _email       = email
    _pro_expires = (datetime.now() + timedelta(days=30)).isoformat()
    return True


def cancel_pro():
    global _plan, _pro_expires
    _plan        = "free"
    _pro_expires = None


def get_pro_expiry_str():
    if _pro_expires:
        try:
            return datetime.fromisoformat(_pro_expires).strftime("%d/%m/%Y")
        except Exception:
            return ""
    return ""


# ─────────────────────────────────────────
# HISTORIQUE
# ─────────────────────────────────────────
def get_history(limit=50):
    return []


# ─────────────────────────────────────────
# RÉSUMÉ
# ─────────────────────────────────────────
def billing_summary():
    plan = get_plan()
    rem  = remaining_free()
    return {
        "plan":      plan,
        "used":      _usage,
        "remaining": rem if plan == "free" else "∞",
        "limit":     FREE_LIMIT if plan == "free" else "∞",
        "expiry":    get_pro_expiry_str(),
        "email":     get_email(),
        "price":     PRO_PRICE,
    }
