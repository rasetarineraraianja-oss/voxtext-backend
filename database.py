# -*- coding: utf-8 -*-
"""
database.py — PostgreSQL version pour Render
"""

import os
import uuid
from datetime import datetime, timedelta

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False
    print("❌ psycopg2 non installé", flush=True)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


# ─────────────────────────────────────────
# CONNEXION
# ─────────────────────────────────────────
def get_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL non défini dans les variables d'environnement")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


# ─────────────────────────────────────────
# INIT DB
# ─────────────────────────────────────────
def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    password TEXT,
                    plan TEXT DEFAULT 'free',
                    pro_expires TEXT,
                    payment_provider TEXT,
                    created_at TEXT,
                    device_fingerprint TEXT,
                    last_seen TEXT,
                    downloads INTEGER DEFAULT 0,
                    used_trials INTEGER DEFAULT 0,
                    is_verified INTEGER DEFAULT 0,
                    verify_token TEXT,
                    reset_token TEXT
                )
            """)
            cur.execute("""
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id TEXT PRIMARY KEY,
                    user_email TEXT,
                    url TEXT,
                    fmt TEXT,
                    status TEXT,
                    error_msg TEXT,
                    created_at TEXT
                )
            """)
        conn.commit()
    print("✅ Base de données PostgreSQL connectée et initialisée", flush=True)


# ─────────────────────────────────────────
# USERS
# ─────────────────────────────────────────
def get_or_create_user(email):
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            if user:
                return dict(user)

            user_id     = str(uuid.uuid4())
            fingerprint = str(uuid.uuid4())
            now         = datetime.now().isoformat()

            cur.execute("""
                INSERT INTO users (
                    id, email, plan, pro_expires,
                    created_at, device_fingerprint, last_seen, downloads
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, email, "free", None, now, fingerprint, now, 0))
        conn.commit()

    return {
        "id":                 user_id,
        "email":              email,
        "plan":               "free",
        "pro_expires":        None,
        "device_fingerprint": fingerprint,
        "last_seen":          now,
        "downloads":          0,
    }


def activate_pro(email, duration_days=30):
    expiry = (datetime.now() + timedelta(days=duration_days)).isoformat()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET plan='pro', pro_expires=%s WHERE email=%s
            """, (expiry, email))
        conn.commit()


def is_pro(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT plan, pro_expires FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
    if not user:
        return False
    if user["plan"] != "pro":
        return False
    if user["pro_expires"]:
        return datetime.fromisoformat(user["pro_expires"]) > datetime.now()
    return False


def increment_download(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET downloads = downloads + 1, last_seen = %s WHERE email = %s
            """, (datetime.now().isoformat(), email))
        conn.commit()


# ─────────────────────────────────────────
# TRANSCRIPTIONS
# ─────────────────────────────────────────
def record_transcription(user_id, filename="", language="auto",
                         duration_sec=0.0, char_count=0,
                         status="success", error_msg=""):
    init_db()
    trans_id = str(uuid.uuid4())
    now      = datetime.now().isoformat()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transcriptions
                (id, user_id, filename, language,
                 duration_sec, char_count, status, error_msg, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (trans_id, user_id, filename, language,
                  duration_sec, char_count, status, error_msg, now))
        conn.commit()
    return trans_id


def get_transcription_history(user_id, limit=50):
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM transcriptions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
            rows = cur.fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────
# STATS
# ─────────────────────────────────────────
def get_stats(email):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT created_at FROM users WHERE email=%s", (email,))
                user = cur.fetchone()
                cur.execute("""
                    SELECT COUNT(*) as total FROM transcriptions
                    WHERE user_id = (SELECT id FROM users WHERE email=%s)
                """, (email,))
                result = cur.fetchone()
        return {
            "member_since": user["created_at"][:10] if user else "—",
            "total_trans":  result["total"] if result else 0,
        }
    except Exception:
        return {"member_since": "—", "total_trans": 0}


# ─────────────────────────────────────────
# INIT AU DÉMARRAGE
# ─────────────────────────────────────────
try:
    init_db()
except Exception as e:
    print(f"❌ Erreur DB au démarrage : {e}", flush=True)
