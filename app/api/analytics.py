from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.models import User
from app.services import analytics as svc

router = APIRouter(prefix="/api/analytics", tags=["Analytics"], dependencies=[Depends(csrf_protect)])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return svc.summary(db, user.id)


@router.get("/charts")
def charts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return svc.charts(db, user.id)
