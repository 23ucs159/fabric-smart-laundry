from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.core.ratelimit import rate_limit
from app.models import User
from app.schemas import AskIn
from app.services.rag.assistant import SUGGESTIONS, answer

router = APIRouter(prefix="/api/assistant", tags=["Smart assistant"], dependencies=[Depends(csrf_protect)])


@router.post("/ask", dependencies=[Depends(rate_limit("assistant", "assistant_limit"))])
def ask(body: AskIn, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Only the question text reaches the assistant: no DB session, no user object, no tools.
    result = answer(body.question)
    if result["blocked"]:
        log_event(db, request, user.id, "assistant_blocked", "blocked", "prompt-injection filter")
    return result


@router.get("/suggestions")
def suggestions(user: User = Depends(get_current_user)):
    return {"suggestions": SUGGESTIONS, "llm_configured": bool(settings.llm_api_key)}
