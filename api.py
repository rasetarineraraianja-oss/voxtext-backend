from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from backend.main import register, RegisterRequest, LoginRequest, login, ForgotPasswordRequest, forgot_password, \
    get_user, AccessRequest, check_access, activate_pro_route, ResetPasswordRequest, reset_password

# ... vos autres imports

app = FastAPI(title="VoxText API", version="1.0.0")  # ← décommentez ça


# Puis enregistrez vos fonctions comme routes :
@app.post("/register")
def route_register(data: RegisterRequest):

    return register(data)

@app.post("/login")
def route_login(data: LoginRequest):
    return login(data)

@app.post("/forgot-password")
def route_forgot(data: ForgotPasswordRequest):
    return forgot_password(data)

@app.post("/reset-password")
def route_reset(data: ResetPasswordRequest):
    return reset_password(data)

@app.get("/user/{email}")
def route_get_user(email: str):
    return get_user(email)

@app.post("/check-access")
def route_check_access(data: AccessRequest):
    return check_access(data)

@app.get("/activate-pro/{email}")
def route_activate_pro(email: str):
    return activate_pro_route(email)

@app.get("/")
def root():
    return {"status": "VoxText API OK"}