from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

# from ..config import settings
# from ..models import User

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from ..config import settings
from ..db import get_db
from ..models import User
from .oauth import oauth2_scheme 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()

JWT_SECRET = "CHANGE_ME_LOCAL_DEV_SECRET"  # move to .env later
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = 60 * 24  # 24 hours

# def hash_password(pw: str) -> str:
#     return pwd_context.hash(pw)

def hash_password(pw: str) -> str:
    # bcrypt has a 72-byte limit
    if len(pw.encode("utf-8")) > 72:
        pw = pw.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(pw)


def verify_password(pw: str, pw_hash: str) -> bool:
    return pwd_context.verify(pw, pw_hash)

def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

# def get_current_user(db: Session, creds: HTTPAuthorizationCredentials = Depends(bearer)) -> User:
#     token = creds.credentials
#     try:
#         payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
#         user_id = payload.get("sub")
#         if not user_id:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
#     except JWTError:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

#     u = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
#     if not u:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
#     return u
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),   # ✅ THIS IS THE FIX
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception

    return user