# -*- coding: utf-8 -*-
"""
database.py — Version propre et stable
"""

import sqlite3
import os
import uuid
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR   = os.path.join(BASE_DIR, "data")
DB_FILE  = os.path.join(DB_DIR, "voxtext.db")



# ─────────────────────────────────────────
# CONNEXION
# ─────────────────────────────────────────
def init_db():
    with get_connection() as conn:

        # TABLE USERS (complète)
        conn.execute("""...""")

        # TABLE TRANSCRIPTIONS
        conn.execute("""...""")

        # 🔥 MIGRATIONS EXISTANTES
        try:
            conn.execute("ALTER TABLE users ADD COLUMN device_fingerprint TEXT")
        except:
            pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_seen TEXT")
        except:
            pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN downloads INTEGER DEFAULT 0")
        except:
            pass

        # ✅ NOUVELLES MIGRATIONS — ajoutez ici
        try:
            conn.execute("ALTER TABLE users ADD COLUMN password TEXT")
        except:
            pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
        except:
            pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN verify_token TEXT")
        except:
            pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        except:
            pass


def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────
# INIT DB + MIGRATIONS
# ─────────────────────────────────────────

def init_db():
    with get_connection() as conn:

        # TABLE USERS (complète)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            plan TEXT,
            pro_expires TEXT,
            created_at TEXT,
            device_fingerprint TEXT,
            last_seen TEXT,
            downloads INTEGER DEFAULT 0
        )
        """)

        # TABLE TRANSCRIPTIONS
        conn.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            filename TEXT,
            language TEXT,
            duration_sec REAL,
            char_count INTEGER,
            status TEXT,
            error_msg TEXT,
            created_at TEXT
        )
        """)

        # 🔥 MIGRATIONS (sécurisées)
        try:
            conn.execute("ALTER TABLE users ADD COLUMN device_fingerprint TEXT")
        except:
            pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_seen TEXT")
        except:
            pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN downloads INTEGER DEFAULT 0")
        except:
            pass


# ─────────────────────────────────────────
# USERS
# ─────────────────────────────────────────

def get_or_create_user(email):
    init_db()

    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if user:
            return dict(user)

        user_id = str(uuid.uuid4())
        fingerprint = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn.execute("""
            INSERT INTO users (
                id, email, plan, pro_expires,
                created_at, device_fingerprint, last_seen, downloads
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            email,
            "free",
            None,
            now,
            fingerprint,
            now,
            0
        ))

        return {
            "id": user_id,
            "email": email,
            "plan": "free",
            "pro_expires": None,
            "device_fingerprint": fingerprint,
            "last_seen": now,
            "downloads": 0
        }


def increment_download(email):
    with get_connection() as conn:
        conn.execute("""
            UPDATE users
            SET downloads = downloads + 1,
                last_seen = ?
            WHERE email = ?
        """, (datetime.now().isoformat(), email))


def activate_pro(email, duration_days=30):
    expiry = (datetime.now() + timedelta(days=duration_days)).isoformat()

    with get_connection() as conn:
        conn.execute("""
            UPDATE users
            SET plan='pro', pro_expires=?
            WHERE email=?
        """, (expiry, email))


def is_pro(email):
    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

    if not user:
        return False

    if user["plan"] != "pro":
        return False

    if user["pro_expires"]:
        return datetime.fromisoformat(user["pro_expires"]) > datetime.now()

    return True


# ─────────────────────────────────────────
# TRANSCRIPTIONS
# ─────────────────────────────────────────

def record_transcription(
    user_id,
    filename="",
    language="auto",
    duration_sec=0.0,
    char_count=0,
    status="success",
    error_msg=""
):
    init_db()

    trans_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO transcriptions
            (id, user_id, filename, language,
             duration_sec, char_count, status, error_msg, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trans_id, user_id, filename, language,
            duration_sec, char_count, status, error_msg, now
        ))

    return trans_id


def get_transcription_history(user_id, limit=50):
    init_db()

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM transcriptions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()

    return [dict(r) for r in rows]


# ─────────────────────────────────────────
# STATS
# ─────────────────────────────────────────

def get_stats(email):
    return {
        "member_since": "2026",
        "total_trans": 0
    }