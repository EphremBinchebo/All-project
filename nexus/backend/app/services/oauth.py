from fastapi.security import OAuth2PasswordBearer

# Token endpoint path (must match your login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
