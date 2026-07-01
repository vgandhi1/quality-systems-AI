from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.core.database import Base


class VerdictEnum(str, enum.Enum):
    GOOD = "Good"
    MINOR_DAMAGE = "Minor Damage"
    MODERATE_DAMAGE = "Moderate Damage"
    SEVERE_DAMAGE = "Severe Damage / Scrap"


class SeverityEnum(str, enum.Enum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_category = Column(String, nullable=False)
    verdict = Column(Enum(VerdictEnum), nullable=False)
    confidence = Column(Float, nullable=False)
    severity = Column(Enum(SeverityEnum), nullable=False)
    recommendation = Column(String, nullable=False)
    damage_regions = Column(JSON, nullable=True)
    result_image_path = Column(String, nullable=True)
    raw_image_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspector = relationship("User", back_populates="inspections")
