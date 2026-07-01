from typing import Dict, List, Any
from enum import Enum


class VerdictType(str, Enum):
    GOOD = "Good"
    MINOR_DAMAGE = "Minor Damage"
    MODERATE_DAMAGE = "Moderate Damage"
    SEVERE_DAMAGE = "Severe Damage / Scrap"


class SeverityType(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


class Grader:
    @staticmethod
    def grade_inspection(detections: List[Dict], category: str) -> Dict[str, Any]:
        """
        Map detections to verdict, confidence, severity, and recommendation.
        """
        if not detections:
            return {
                "verdict": VerdictType.GOOD,
                "confidence": 100.0,
                "severity": SeverityType.NONE,
                "recommendation": "Resellable as-is",
                "damage_regions": [],
            }

        max_confidence = max([d.get("confidence", 0) for d in detections], default=0)
        damage_confidence = max_confidence * 100

        verdict, severity, recommendation = Grader._map_confidence_to_verdict(
            damage_confidence, category
        )

        return {
            "verdict": verdict,
            "confidence": damage_confidence,
            "severity": severity,
            "recommendation": recommendation,
            "damage_regions": detections,
        }

    @staticmethod
    def _map_confidence_to_verdict(confidence: float, category: str) -> tuple:
        """
        Map damage confidence percentage to verdict, severity, and recommendation.
        """
        if confidence < 15:
            return (
                VerdictType.GOOD,
                SeverityType.NONE,
                "Resellable as-is",
            )
        elif confidence < 45:
            recommendation = f"Refurbish and re-list ({category} category)"
            return (
                VerdictType.MINOR_DAMAGE,
                SeverityType.MINOR,
                recommendation,
            )
        elif confidence < 75:
            recommendation = f"Sell as parts / deep discount ({category} category)"
            return (
                VerdictType.MODERATE_DAMAGE,
                SeverityType.MODERATE,
                recommendation,
            )
        else:
            recommendation = f"Write off or dispose ({category} category)"
            return (
                VerdictType.SEVERE_DAMAGE,
                SeverityType.SEVERE,
                recommendation,
            )
