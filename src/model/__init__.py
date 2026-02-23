"""Model module for MedGemma integration and clinical validation."""

from src.model.confidence import (
    Classification,
    ConfidenceScore,
    extract_confidence,
    classify_prediction,
    filter_low_confidence,
)

__all__ = [
    "Classification",
    "ConfidenceScore",
    "extract_confidence",
    "classify_prediction",
    "filter_low_confidence",
]
