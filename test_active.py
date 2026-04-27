# -*- coding: utf-8 -*-
"""
test_activate.py — Test manuel d'activation Pro.

Exécutez : python test_activate.py test2@gmail.com

Cela simule exactement ce que fait le webhook Stripe.
Si ça marche ici mais pas via webhook → le problème est dans le webhook.
Si ça ne marche pas ici → le problème est dans la DB.
"""

import sys
from datetime import datetime, timedelta
from database import get_connection


def activate_pro(email: str, provider: str = "test"):
    email  = email.strip().lower()
    expiry = (datetime.now() + timedelta(days=31)).isoformat()

    print(f"\n🔧 Tentative d'activation Pro pour : {email!r}")
    print(f"   expiry = {expiry[:10]}")

    with get_connection() as conn:
        # Vérifier que l'user existe
        user = conn.execute(
            "SELECT email, plan FROM users WHERE email=?", (email,)
        ).fetchone()

        if not user:
            print(f"   ✖ ERREUR : Aucun utilisateur avec email={email!r}")
            print("   → Vérifiez l'email exact dans la DB")
            return False

        print(f"   ✔ User trouvé : plan actuel = {user['plan']!r}")

        # Tentative UPDATE
        rows = conn.execute(
            """UPDATE users
               SET plan='pro', pro_expires=?, payment_provider=?, used_trials=0
               WHERE email=?""",
            (expiry, provider, email)
        ).rowcount

        print(f"   rows affectées = {rows}")

        if rows == 0:
            print("   ✖ UPDATE n'a affecté aucune ligne !")
            return False

    # Vérification post-update
    with get_connection() as conn:
        user = conn.execute(
            "SELECT email, plan, pro_expires FROM users WHERE email=?", (email,)
        ).fetchone()
        print(f"\n✔ État après UPDATE :")
        print(f"   email       = {user['email']}")
        print(f"   plan        = {user['plan']}")
        print(f"   pro_expires = {user['pro_expires']}")

        if user["plan"] == "pro":
            print("\n🎉 Activation réussie !")
            return True
        else:
            print("\n✖ Échec — plan toujours 'free' après UPDATE")
            return False


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "test3@gmail.com"
    activate_pro(email)