import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.core.ratelimit import rate_limit
from app.models import EtlRun, User
from app.services.etl.pipeline import run_pipeline

router = APIRouter(prefix="/api/etl", tags=["Data engineering"], dependencies=[Depends(csrf_protect)])
SOURCES = {"baseline": "fabric_records.csv", "messy": "messy_fabric_records.csv"}


@router.get("/report")
def report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = db.query(EtlRun).order_by(EtlRun.id.desc()).first()
    if not run:
        return {"available": False}
    data = json.loads(run.report_json)
    data["available"], data["run_id"] = True, run.id
    return data


@router.post("/run", dependencies=[Depends(rate_limit("upload", "upload_limit"))])
def run(request: Request, source: str = "baseline", db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    if source not in SOURCES:
        raise HTTPException(400, f"source must be one of {sorted(SOURCES)}")
    rep = run_pipeline(settings.raw_dir / SOURCES[source], db=db)
    log_event(db, request, user.id, "etl_run", detail=SOURCES[source])
    rep["available"] = True
    return rep
