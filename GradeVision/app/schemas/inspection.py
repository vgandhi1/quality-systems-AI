from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class DamageRegion(BaseModel):
    label: str
    confidence: float
    bbox: List[float]


class InspectionResult(BaseModel):
    inspection_id: str
    product_category: str
    verdict: str
    confidence: float
    severity: str
    recommendation: str
    damage_regions: Optional[List[DamageRegion]] = None
    result_image_b64: Optional[str] = None
    inspector_id: int
    inspector_name: str
    timestamp: datetime


class InspectionLogEntry(BaseModel):
    id: str
    product_category: str
    verdict: str
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_inspections: int
    good_count: int
    minor_damage_count: int
    moderate_damage_count: int
    severe_damage_count: int
    today_inspections: int
    average_confidence: float
