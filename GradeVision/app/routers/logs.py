from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.inspection import Inspection
from app.schemas.inspection import InspectionLogEntry, DashboardStats

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[InspectionLogEntry])
def get_inspection_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == int(current_user["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    inspections = (
        db.query(Inspection)
        .filter(Inspection.inspector_id == user.id)
        .order_by(Inspection.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return inspections


@router.get("/{inspection_id}")
def get_inspection_detail(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == int(current_user["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()

    if not inspection or inspection.inspector_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    return inspection


@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == int(current_user["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    inspections = db.query(Inspection).filter(Inspection.inspector_id == user.id).all()

    today = datetime.utcnow().date()
    today_inspections = db.query(Inspection).filter(
        Inspection.inspector_id == user.id,
        func.date(Inspection.created_at) == today,
    ).count()

    verdicts = {}
    for inspection in inspections:
        verdict = inspection.verdict.value
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

    avg_confidence = 0
    if inspections:
        avg_confidence = sum([i.confidence for i in inspections]) / len(inspections)

    return DashboardStats(
        total_inspections=len(inspections),
        good_count=verdicts.get("Good", 0),
        minor_damage_count=verdicts.get("Minor Damage", 0),
        moderate_damage_count=verdicts.get("Moderate Damage", 0),
        severe_damage_count=verdicts.get("Severe Damage / Scrap", 0),
        today_inspections=today_inspections,
        average_confidence=round(avg_confidence, 2),
    )
