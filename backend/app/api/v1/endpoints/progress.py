from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import mvp_progress
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/progress", tags=["progress"])

@router.get("")
def list_progress(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return mvp_progress.list_projects(db)

@router.get("/{project_id}")
def get_progress(project_id:int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row=mvp_progress.get_project(db, project_id)
    if not row: raise HTTPException(404,"project not found")
    return row

@router.post("/from-card/{card_id}")
def create_from_card(card_id:int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    try: return mvp_progress.get_project(db, mvp_progress.create_project_from_card(db, card_id).id)
    except ValueError as e: raise HTTPException(400, str(e))

@router.post("/{project_id}/prd")
def save_prd(project_id:int, payload:dict, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        p=mvp_progress.save_prd(db, project_id, str(payload.get('content') or ''))
        return mvp_progress.get_project(db,p.id)
    except ValueError as e: raise HTTPException(400, str(e))

@router.post("/{project_id}/validate")
def validate(project_id:int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        mvp_progress.validate_project(db, project_id)
        return mvp_progress.get_project(db, project_id)
    except ValueError as e: raise HTTPException(400, str(e))

@router.post("/{project_id}/verify-next")
def verify_next(project_id:int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    try: return mvp_progress.run_next_validation_round(db, project_id)
    except ValueError as e: raise HTTPException(400, str(e))

@router.post("/{project_id}/auto-validation")
def set_auto_validation(project_id:int, payload:dict, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        return mvp_progress.update_auto_validation(db, project_id, bool(payload.get('enabled')), str(payload.get('schedule') or 'weekly'), int(payload.get('hour') or 9), int(payload.get('minute') or 0), int(payload.get('weekday') or 1))
    except ValueError as e: raise HTTPException(400, str(e))
