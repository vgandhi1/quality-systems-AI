import base64
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.inspection import Inspection
from app.services.detection import YOLOv5Detector
from app.services.grader import Grader
from app.schemas.inspection import InspectionResult

router = APIRouter(prefix="/inspect", tags=["inspect"])

os.makedirs("data", exist_ok=True)


@router.post("", response_model=InspectionResult)
async def inspect_item(
    file: UploadFile = File(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == int(current_user["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        contents = await file.read()
        filename = f"inspection_{datetime.utcnow().timestamp()}.jpg"
        filepath = os.path.join("data", filename)

        with open(filepath, "wb") as f:
            f.write(contents)

        detector = YOLOv5Detector()
        detection_result = detector.detect(filepath)

        if detection_result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Detection failed: {detection_result['message']}",
            )

        detections = detection_result.get("detections", [])
        grade = Grader.grade_inspection(detections, category)

        result_image_path = detection_result.get("result_image_path", "")
        result_image_b64 = None
        if os.path.exists(result_image_path):
            with open(result_image_path, "rb") as f:
                result_image_b64 = base64.b64encode(f.read()).decode("utf-8")

        inspection = Inspection(
            inspector_id=user.id,
            product_category=category,
            verdict=grade["verdict"],
            confidence=grade["confidence"],
            severity=grade["severity"],
            recommendation=grade["recommendation"],
            damage_regions=grade["damage_regions"],
            result_image_path=result_image_path,
            raw_image_path=filepath,
        )
        db.add(inspection)
        db.commit()
        db.refresh(inspection)

        return InspectionResult(
            inspection_id=inspection.id,
            product_category=inspection.product_category,
            verdict=inspection.verdict.value,
            confidence=inspection.confidence,
            severity=inspection.severity.value,
            recommendation=inspection.recommendation,
            damage_regions=grade["damage_regions"],
            result_image_b64=result_image_b64,
            inspector_id=user.id,
            inspector_name=user.full_name,
            timestamp=inspection.created_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inspection failed: {str(e)}",
        )
