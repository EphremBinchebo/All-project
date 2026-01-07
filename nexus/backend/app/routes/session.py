from fastapi import APIRouter
from app.services.session import SessionService

router = APIRouter(prefix="/api/session", tags=["Session"])

@router.get("")
def get_session():
    return SessionService().detect()
