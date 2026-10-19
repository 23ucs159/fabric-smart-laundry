import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.models import FabricAnalysis, User
from app.services.analytics import serialize_analysis

router = APIRouter(prefix="/api/history", tags=["History"], dependencies=[Depends(csrf_protect)])


@router.get("")
def history(fabric: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(FabricAnalysis).filter(FabricAnalysis.user_id == user.id)
    if fabric:
        q = q.filter(FabricAnalysis.predicted_fabric == fabric.lower())
    total = q.count()
    rows = q.order_by(FabricAnalysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [serialize_analysis(r) for r in rows], "total": total, "page": page,
            "pages": max(1, math.ceil(total / page_size))}
