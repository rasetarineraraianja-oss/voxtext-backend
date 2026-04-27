# -*- coding: utf-8 -*-
"""
success_page_fix.py
Remplacez votre route /payment-success dans api.py par ceci.
Affiche une vraie page HTML au lieu d'un JSON que le navigateur ne sait pas afficher.
"""

from fastapi.responses import HTMLResponse

@app.get("/payment-success", response_class=HTMLResponse)
def payment_success(session_id: str = "", email: str = "", provider: str = "stripe"):
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paiement réussi — VoxText</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Helvetica Neue', sans-serif;
            background: #0d0d14;
            color: #e8e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        .card {{
            background: #16161f;
            border: 1px solid #2a2a3a;
            border-radius: 16px;
            padding: 48px 56px;
            text-align: center;
            max-width: 480px;
            width: 90%;
        }}
        .icon {{ font-size: 64px; margin-bottom: 24px; }}
        h1 {{
            font-size: 26px;
            font-weight: 700;
            color: #1db954;
            margin-bottom: 12px;
        }}
        p {{
            color: #a0a0c0;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 8px;
        }}
        .email {{
            background: #1e1e2e;
            border-radius: 8px;
            padding: 10px 18px;
            color: #6c63ff;
            font-weight: bold;
            margin: 16px 0;
            display: inline-block;
        }}
        .badge {{
            background: #a78bfa;
            color: white;
            border-radius: 20px;
            padding: 6px 18px;
            font-size: 13px;
            font-weight: bold;
            display: inline-block;
            margin: 20px 0 8px;
        }}
        .hint {{
            color: #5a5a7a;
            font-size: 13px;
            margin-top: 24px;
        }}
        .close-hint {{
            margin-top: 32px;
            padding: 12px 28px;
            background: #6c63ff;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close-hint:hover {{ background: #8b84ff; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🎉</div>
        <h1>Paiement réussi !</h1>
        <p>Merci pour votre abonnement <strong>VoxText Pro</strong>.</p>

        {"<div class='email'>✉ " + email + "</div>" if email else ""}

        <div class="badge">⭐ Plan Pro activé</div>

        <p>Votre accès illimité aux transcriptions est maintenant actif.</p>

        <p class="hint">
            Retournez dans l'application VoxText.<br>
            Votre plan Pro sera mis à jour automatiquement.
        </p>

        <br>
        <button class="close-hint" onclick="window.close()">
            Fermer cette page
        </button>
    </div>
</body>
</html>
""")


@app.get("/payment-cancelled", response_class=HTMLResponse)
def payment_cancelled(provider: str = ""):
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Paiement annulé — VoxText</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Helvetica Neue', sans-serif;
            background: #0d0d14;
            color: #e8e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .card {
            background: #16161f;
            border: 1px solid #2a2a3a;
            border-radius: 16px;
            padding: 48px 56px;
            text-align: center;
            max-width: 480px;
            width: 90%;
        }
        .icon { font-size: 56px; margin-bottom: 20px; }
        h1 { font-size: 22px; color: #f5c518; margin-bottom: 12px; }
        p { color: #a0a0c0; font-size: 15px; line-height: 1.6; }
        button {
            margin-top: 28px;
            padding: 12px 28px;
            background: #6c63ff;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { background: #8b84ff; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">↩</div>
        <h1>Paiement annulé</h1>
        <p>Vous êtes resté sur le plan gratuit.<br>
           Vous pouvez retourner dans VoxText et réessayer à tout moment.</p>
        <button onclick="window.close()">Fermer cette page</button>
    </div>
</body>
</html>
""")