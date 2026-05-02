# -*- coding: utf-8 -*-
import os
import uuid
import bcrypt
from datetime import datetime, timedelta

import stripe
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection

# =============================================================
# CONFIGURATION
# =============================================================
stripe.api_key        = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51T4yleGjzNL4AeaeqolgABR4i3K8ytKTzu0C8pslkBmMIiE9QeCwTED2dY1wP3zioGkijJQDLj0fd8XznqV1jq9V00zpDaJv8c")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_2f0d49755e804edb2ebe863b259b21659360426bc5030653ddeb95232ea012d4")
STRIPE_PRICE_ID       = os.environ.get("STRIPE_PRICE_ID", "price_1TRpIAGjzNL4AeaeEDsVb9i2")

PAYPAL_CLIENT_ID     = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_PLAN_ID       = os.environ.get("PAYPAL_PLAN_ID", "")
PAYPAL_BASE_URL      = "https://api-m.paypal.com"

APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://voxtext-backend-r6l8.onrender.com")
PRO_PRICE    = 4.99

# =============================================================
# APP
# =============================================================
app = FastAPI(title="VoxText API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================
# SCHEMAS
# =============================================================
class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AccessRequest(BaseModel):
    email: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

# =============================================================
# HEALTH CHECK
# =============================================================
@app.get("/")
def root():
    return {"status": "VoxText API OK", "version": "2.0.0"}

@app.post("/increment-trials")
def route_increment_trials(data: dict):
    email = data.get("email", "").strip().lower()
    if not email:
        return {"error": "missing_email"}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET used_trials = used_trials + 1 WHERE email=%s
            """, (email,))
        conn.commit()
    return {"status": "ok"}

@app.head("/")
def head_root():
    return Response(status_code=200)

# =============================================================
# AUTH
# =============================================================
@app.post("/register")
def route_register(data: RegisterRequest):
    email    = data.email.strip().lower()
    password = data.password.strip()

    if not email or not password:
        return {"error": "missing_fields"}

    hashed       = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    verify_token = str(uuid.uuid4())
    now          = datetime.now().isoformat()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                return {"error": "email_exists"}
            cur.execute("""
                INSERT INTO users
                    (id, email, password, plan, created_at,
                     device_fingerprint, last_seen, is_verified, verify_token)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (str(uuid.uuid4()), email, hashed, "free", now,
                  str(uuid.uuid4()), now, 1, verify_token))
        conn.commit()

    return {"status": "ok", "message": "Compte créé."}


@app.post("/login")
def route_login(data: LoginRequest):
    email    = data.email.strip().lower()
    password = data.password.strip()

    if not email or not password:
        return {"error": "missing_fields"}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()

    if not user:
        return {"error": "user_not_found"}
    if not user["password"]:
        return {"error": "no_password"}
    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return {"error": "invalid_password"}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET last_seen=%s WHERE email=%s",
                        (datetime.now().isoformat(), email))
        conn.commit()

    return {
        "status":      "ok",
        "email":       email,
        "plan":        user["plan"],
        "pro_expires": user["pro_expires"],
    }


@app.post("/forgot-password")
def route_forgot(data: ForgotPasswordRequest):
    email = data.email.strip().lower()
    token = str(uuid.uuid4())
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if not cur.fetchone():
                return {"error": "user_not_found"}
            cur.execute("UPDATE users SET reset_token=%s WHERE email=%s", (token, email))
        conn.commit()
    link = f"{APP_BASE_URL}/reset-password?token={token}"
    return {"status": "ok", "reset_link": link}


@app.post("/reset-password")
def route_reset(data: ResetPasswordRequest):
    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE reset_token=%s", (data.token,))
            user = cur.fetchone()
            if not user:
                return {"error": "invalid_token"}
            cur.execute(
                "UPDATE users SET password=%s, reset_token=NULL WHERE reset_token=%s",
                (hashed, data.token))
        conn.commit()
    return {"status": "password_updated"}

@app.get("/user/{email}")
def route_get_user(email: str):
    email = email.strip().lower()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, plan, pro_expires, created_at, used_trials FROM users WHERE email=%s",
                (email,))
            user = cur.fetchone()
    if not user:
        return {"error": "not_found"}
    return {
        "email":       user["email"],
        "plan":        user["plan"],
        "pro_expires": user["pro_expires"],
        "created_at":  user["created_at"],
        "used_trials": user["used_trials"] or 0,
    }

@app.post("/increment-trials")
def route_increment_trials(data: dict):
    email = data.get("email", "").strip().lower()
    if not email:
        return {"error": "missing_email"}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET used_trials = used_trials + 1 WHERE email=%s",
                (email,))
        conn.commit()
    return {"status": "ok"}

@app.post("/check-access")
def route_check_access(data: AccessRequest):
    email = data.email.strip().lower()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT plan, pro_expires FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
    if not user:
        return {"error": "user_not_found"}
    if user["plan"] == "pro":
        try:
            if datetime.now() <= datetime.fromisoformat(user["pro_expires"]):
                return {"status": "ok", "access": "full"}
        except Exception:
            pass
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET plan='free' WHERE email=%s", (email,))
            conn.commit()
    return {"status": "ok", "access": "limited"}


@app.get("/activate-pro/{email}")
def route_activate_pro(email: str):
    email = email.strip().lower()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if not cur.fetchone():
                return {"error": "user_not_found"}
    _activate_pro(email, "manual")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT plan, pro_expires FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
    return {
        "status":      "pro_activated",
        "email":       email,
        "plan":        user["plan"],
        "pro_expires": user["pro_expires"],
    }


# =============================================================
# STRIPE — SESSION DE PAIEMENT
# =============================================================
@app.post("/create-checkout-session/stripe")
def create_stripe_session(data: dict):
    email = data.get("email", "").strip().lower()
    if not email:
        return {"error": "missing_email"}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
    if not user:
        return {"error": "user_not_found"}
    if user["plan"] == "pro":
        return {"error": "already_pro"}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            customer_email=email,
            metadata={"user_email": email},
            client_reference_id=email,
            success_url=(
                f"{APP_BASE_URL}/payment-success"
                f"?provider=stripe&session_id={{CHECKOUT_SESSION_ID}}&email={email}"
            ),
            cancel_url=f"{APP_BASE_URL}/payment-cancelled?provider=stripe",
            billing_address_collection="auto",
        )
        print(f"[Stripe] Session créée pour {email}", flush=True)
        return {"status": "ok", "checkout_url": session.url, "provider": "stripe"}
    except Exception as e:
        print(f"[Stripe] ❌ {e}", flush=True)
        return {"error": str(e)}


# =============================================================
# STRIPE — WEBHOOK
# =============================================================
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET, tolerance=None)
        print(f"[Stripe] ✔ {event['type']}", flush=True)
    except Exception as e:
        print(f"[Stripe] ✖ {e}", flush=True)
        return JSONResponse(status_code=400, content={"error": str(e)})

    etype    = event["type"]
    resource = event["data"]["object"].to_dict()

    if etype in ("checkout.session.completed",
                 "invoice.payment_succeeded",
                 "invoice.payment_paid",
                 "invoice_payment.paid"):
        email = resource.get("metadata", {}).get("user_email", "")
        if not email:
            email = (resource.get("customer_email")
                     or resource.get("customer_details", {}).get("email", ""))
        if not email:
            customer_id = resource.get("customer", "")
            if customer_id:
                try:
                    customer = stripe.Customer.retrieve(customer_id)
                    email    = customer.get("email", "")
                except Exception as e:
                    print(f"[Stripe] ❌ customer : {e}", flush=True)
        print(f"[Stripe] Email : {email!r}", flush=True)
        if email:
            _activate_pro(email, "stripe")

    elif etype == "customer.subscription.deleted":
        try:
            customer = stripe.Customer.retrieve(resource.get("customer", ""))
            email    = customer.get("email", "")
            if email:
                _downgrade_to_free(email)
        except Exception as e:
            print(f"[Stripe] ❌ {e}", flush=True)

    elif etype == "invoice.payment_failed":
        print(f"[Stripe] ⚠ Paiement échoué", flush=True)

    return {"status": "ok"}


# =============================================================
# PAGES DE RETOUR HTML
# =============================================================
@app.get("/payment-success", response_class=HTMLResponse)
def payment_success(session_id: str = "", email: str = "", provider: str = "stripe"):
    email_block = f"<div class='email'>✉ {email}</div>" if email else ""
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Paiement réussi — VoxText</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family: 'Helvetica Neue', sans-serif;
            background: #0d0d14; color: #e8e8f0;
            display: flex; align-items: center;
            justify-content: center; min-height: 100vh;
        }}
        .card {{
            background: #16161f; border: 1px solid #2a2a3a;
            border-radius: 16px; padding: 48px 56px;
            text-align: center; max-width: 480px; width: 90%;
        }}
        .icon {{ font-size: 64px; margin-bottom: 24px; }}
        h1 {{ font-size: 26px; color: #1db954; margin-bottom: 12px; }}
        p {{ color: #a0a0c0; font-size: 15px; line-height: 1.6; margin-bottom: 8px; }}
        .email {{
            background: #1e1e2e; border-radius: 8px; padding: 10px 18px;
            color: #6c63ff; font-weight: bold; margin: 16px 0; display: inline-block;
        }}
        .badge {{
            background: #a78bfa; color: white; border-radius: 20px;
            padding: 6px 18px; font-size: 13px; font-weight: bold;
            display: inline-block; margin: 20px 0 8px;
        }}
        .btn {{
            display: inline-block; margin-top: 28px; padding: 14px 32px;
            background: #6c63ff; color: white; border: none;
            border-radius: 10px; font-size: 15px; font-weight: bold;
            cursor: pointer; transition: background 0.2s;
        }}
        .btn:hover {{ background: #8b84ff; }}
        #status {{ margin-top: 12px; color: #5a5a7a; font-size: 13px; }}
        #countdown {{ color: #a78bfa; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🎉</div>
        <h1>Paiement réussi !</h1>
        <p>Merci pour votre abonnement <strong>VoxText Pro</strong>.</p>
        {email_block}
        <div class="badge">⭐ Plan Pro activé</div>
        <p>Retournez dans l'application VoxText.<br>
           Votre plan Pro sera mis à jour automatiquement.</p>
        <br>
        <button class="btn" onclick="closeTab()">Fermer cette page</button>
        <div id="status">
            Fermeture automatique dans <span id="countdown">5</span>s
        </div>
    </div>
    <script>
        var n = 5;
        var timer = setInterval(function() {{
            n--;
            document.getElementById('countdown').textContent = n;
            if (n <= 0) {{ clearInterval(timer); closeTab(); }}
        }}, 1000);
        function closeTab() {{
            window.close();
            setTimeout(function() {{
                try {{ window.open('about:blank','_self').close(); }} catch(e) {{}}
                document.getElementById('status').innerHTML =
                    '👆 Fermez cet onglet avec <strong>Ctrl+W</strong>';
            }}, 200);
        }}
    </script>
</body>
</html>
""")


@app.get("/payment-cancelled", response_class=HTMLResponse)
def payment_cancelled(provider: str = ""):
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8"><title>Annulé — VoxText</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Helvetica Neue', sans-serif;
            background: #0d0d14; color: #e8e8f0;
            display: flex; align-items: center;
            justify-content: center; min-height: 100vh;
        }
        .card {
            background: #16161f; border: 1px solid #2a2a3a;
            border-radius: 16px; padding: 48px 56px;
            text-align: center; max-width: 480px; width: 90%;
        }
        .icon { font-size: 56px; margin-bottom: 20px; }
        h1 { font-size: 22px; color: #f5c518; margin-bottom: 12px; }
        p { color: #a0a0c0; font-size: 15px; line-height: 1.6; }
        .btn {
            display: inline-block; margin-top: 28px; padding: 14px 32px;
            background: #6c63ff; color: white; border: none;
            border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer;
        }
        .btn:hover { background: #8b84ff; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">↩</div>
        <h1>Paiement annulé</h1>
        <p>Vous restez sur le plan gratuit.<br>
           Retournez dans VoxText et réessayez à tout moment.</p>
        <button class="btn" onclick="window.close()">Fermer cette page</button>
    </div>
    <script>setTimeout(function() { window.close(); }, 5000);</script>
</body>
</html>
""")


# =============================================================
# PORTAIL STRIPE
# =============================================================
@app.post("/create-portal-session")
def create_portal_session(data: dict):
    email = data.get("email", "").strip().lower()
    try:
        customers = stripe.Customer.list(email=email, limit=1)
        if not customers.data:
            return {"error": "customer_not_found"}
        session = stripe.billing_portal.Session.create(
            customer=customers.data[0].id,
            return_url=APP_BASE_URL,
        )
        return {"url": session.url}
    except Exception as e:
        return {"error": str(e)}


# =============================================================
# PAYPAL
# =============================================================
async def _get_paypal_token() -> str:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{PAYPAL_BASE_URL}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        res.raise_for_status()
        return res.json()["access_token"]


@app.post("/create-checkout-session/paypal")
async def create_paypal_subscription(data: dict):
    email = data.get("email", "").strip().lower()
    if not email:
        return {"error": "missing_email"}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
    if not user:
        return {"error": "user_not_found"}
    if user["plan"] == "pro":
        return {"error": "already_pro"}
    try:
        token = await _get_paypal_token()
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{PAYPAL_BASE_URL}/v1/billing/subscriptions",
                json={
                    "plan_id":    PAYPAL_PLAN_ID,
                    "subscriber": {"email_address": email},
                    "custom_id":  email,
                    "application_context": {
                        "brand_name":          "VoxText",
                        "locale":              "fr-FR",
                        "shipping_preference": "NO_SHIPPING",
                        "user_action":         "SUBSCRIBE_NOW",
                        "return_url": f"{APP_BASE_URL}/payment-success?provider=paypal&email={email}",
                        "cancel_url": f"{APP_BASE_URL}/payment-cancelled?provider=paypal",
                    },
                },
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                timeout=15,
            )
            res.raise_for_status()
            subscription = res.json()
        approve_url = next(
            (l["href"] for l in subscription.get("links", []) if l["rel"] == "approve"), None)
        if not approve_url:
            return {"error": "no_approve_url"}
        return {"status": "ok", "checkout_url": approve_url,
                "provider": "paypal", "subscription_id": subscription.get("id")}
    except httpx.HTTPStatusError as e:
        return {"error": f"PayPal API : {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/webhook/paypal")
async def paypal_webhook(request: Request):
    try:
        event = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    etype    = event.get("event_type", "")
    resource = event.get("resource", {})
    print(f"[PayPal] {etype}", flush=True)
    if etype in ("BILLING.SUBSCRIPTION.ACTIVATED", "PAYMENT.SALE.COMPLETED"):
        email = (resource.get("subscriber", {}).get("email_address")
                 or resource.get("custom_id", ""))
        if email:
            _activate_pro(email, "paypal")
    elif etype == "BILLING.SUBSCRIPTION.RENEWED":
        email = resource.get("subscriber", {}).get("email_address", "")
        if email:
            _activate_pro(email, "paypal")
    elif etype == "BILLING.SUBSCRIPTION.CANCELLED":
        email = resource.get("subscriber", {}).get("email_address", "")
        if email:
            _downgrade_to_free(email)
    return {"status": "ok"}


# =============================================================
# HELPERS DB
# =============================================================
def _activate_pro(email: str, provider: str = ""):
    email  = email.strip().lower()
    expiry = (datetime.now() + timedelta(days=31)).isoformat()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET plan='pro', pro_expires=%s, payment_provider=%s, used_trials=0
                WHERE email=%s
            """, (expiry, provider, email))
            rows = cur.rowcount
        conn.commit()
    print(f"[DB] ✔ Pro ({provider}) → {email} | rows={rows} | expire={expiry[:10]}", flush=True)
    if rows == 0:
        print(f"[DB] ✖ Aucun user : {email!r}", flush=True)


def _downgrade_to_free(email: str):
    email = email.strip().lower()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET plan='free', pro_expires=NULL WHERE email=%s", (email,))
        conn.commit()
    print(f"[DB] Free → {email}", flush=True)
