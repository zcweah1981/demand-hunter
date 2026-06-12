from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import clue_pool
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/clues", tags=["clues"])


@router.get("")
def clue_list(
    limit: int = 100,
    status: str = "",
    clue_type: str = "",
    source: str = "",
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return clue_pool.list_clues(
        db,
        limit=max(1, min(500, limit)),
        status=status,
        clue_type=clue_type,
        source=source,
    )


@router.post("/llm-analysis")
def clue_llm_analysis(
    payload: dict,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return clue_pool.llm_analysis_for_clue(db, str(payload.get("clue_id") or ""))
