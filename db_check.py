# -*- coding: utf-8 -*-
"""
db_check.py — Diagnostic et migration de la base de données.

Exécutez : python db_check.py
"""

from database import get_connection


def check_and_migrate():
    print("=" * 60)
    print("DIAGNOSTIC BASE DE DONNÉES")
    print("=" * 60)

    with get_connection() as conn:

        # ── 1. Afficher la structure réelle de la table users ──
        print("\n📋 Structure actuelle de la table users :")
        cols = conn.execute("PRAGMA table_info(users)").fetchall()
        col_names = []
        for col in cols:
            print(f"   col {col['cid']} : {col['name']} ({col['type']}) "
                  f"{'NOT NULL' if col['notnull'] else 'nullable'} "
                  f"default={col['dflt_value']!r}")
            col_names.append(col["name"])

        # ── 2. Vérifier les colonnes manquantes ──
        print("\n🔍 Vérification des colonnes requises :")
        required = {
            "pro_expires":       "TEXT",
            "payment_provider":  "TEXT DEFAULT ''",
            "used_trials":       "INTEGER DEFAULT 0",
        }

        missing = []
        for col, col_type in required.items():
            if col in col_names:
                print(f"   ✔  {col} — présente")
            else:
                print(f"   ✖  {col} — MANQUANTE → sera ajoutée")
                missing.append((col, col_type))

        # ── 3. Ajouter les colonnes manquantes ──
        if missing:
            print("\n🔧 Ajout des colonnes manquantes...")
            for col, col_type in missing:
                try:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                    print(f"   ✔  {col} ajoutée")
                except Exception as e:
                    print(f"   ✖  Erreur pour {col} : {e}")
        else:
            print("\n✔ Toutes les colonnes sont présentes.")

        # ── 4. Afficher les utilisateurs ──
        print("\n👥 Utilisateurs actuels :")
        users = conn.execute(
            "SELECT email, plan, pro_expires, payment_provider FROM users"
        ).fetchall()

        if not users:
            print("   (aucun utilisateur)")
        for u in users:
            print(f"   📧 {u['email']}")
            print(f"      plan            = {u['plan']!r}")
            print(f"      pro_expires     = {u['pro_expires']!r}")
            print(f"      payment_provider= {u.get('payment_provider', 'N/A')!r}")

    print("\n" + "=" * 60)
    print("✔ Diagnostic terminé.")
    print("=" * 60)


if __name__ == "__main__":
    check_and_migrate()