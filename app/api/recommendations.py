from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.api.fabric import get_owned
from app.models import User, WashingHistory
from app.schemas import SelectModeIn
from app.services.analytics import iso
from app.services.recommendation import load_rules, recommend

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"], dependencies=[Depends(csrf_protect)])


@router.get("/fabrics")
def fabrics(user: User = Depends(get_current_user)):
    return [{"key": k, "name": v["display"]} for k, v in load_rules().items()]


@router.get("/lookup")
def lookup(fabric: str, has_dryer: bool | None = None, prefer_gentle: bool = False,
           user: User = Depends(get_current_user)):
    """Rule-based lookup (no image): confidence is treated as 1.0 because the user chose the fabric."""
    try:
        return recommend(fabric, 1.0, {"has_dryer": has_dryer, "prefer_gentle": prefer_gentle or None})
    except ValueError:
        raise HTTPException(404, "Unsupported fabric type.")


@router.get("/analysis/{analysis_id}")
def for_analysis(analysis_id: int, has_dryer: bool | None = None, prefer_gentle: bool = False,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = get_owned(db, user, analysis_id)
    return recommend(a.predicted_fabric, a.confidence, {"has_dryer": has_dryer, "prefer_gentle": prefer_gentle or None})


@router.post("/select", status_code=201)
def select_mode(body: SelectModeIn, request: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    a = get_owned(db, user, body.analysis_id)
    if body.mode not in load_rules()[a.predicted_fabric]["wash_modes"]:
        raise HTTPException(400, "That washing mode is not valid for this fabric.")
    row = WashingHistory(user_id=user.id, fabric_analysis_id=a.id, selected_washing_mode=body.mode)
    db.add(row)
    db.commit()
    log_event(db, request, user.id, "settings_change", detail=f"wash mode selected for analysis={a.id}")
    return {"id": row.id, "mode": row.selected_washing_mode}


@router.get("/selections")
def selections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(WashingHistory).filter_by(user_id=user.id).order_by(WashingHistory.created_at.desc()).limit(10).all())
    return [{"id": r.id, "analysis_id": r.fabric_analysis_id, "mode": r.selected_washing_mode, "created_at": iso(r.created_at)}
            for r in rows]
