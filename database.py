# -*- coding: utf-8 -*-
import os
import uuid
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

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
        conn.commit()

def get_stats(email):
    return {
        "member_since": "2026",
        "total_trans": 0
    }

# Appel init au démarrage
init_db()
