"""Confidence Extraction Module.

Extracts and normalizes confidence scores from MedGemma predictions,
enabling clinical-grade classification with uncertainty quantification.

Example:
    >>> response = "This variant is likely pathogenic (confidence: 0.92)"
    >>> score = extract_confidence(response)
    >>> print(f"Confidence: {score.confidence:.2%}")
    Confidence: 92.00%
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionClass(str, Enum):
    """Clinical variant classification categories."""

    PATHOGENIC = "pathogenic"
    LIKELY_PATHOGENIC = "likely_pathogenic"
    UNCERTAIN = "uncertain_significance"
    LIKELY_BENIGN = "likely_benign"
    BENIGN = "benign"
    UNKNOWN = "unknown"


@dataclass
class ConfidenceScore:
    """Confidence score extracted from model output.

    Attributes:
        confidence: Normalized confidence (0-1 scale).
        raw_value: Original confidence value from model.
        extraction_method: How confidence was extracted.
        is_reliable: Whether confidence meets reliability threshold.
    """

    confidence: float
    raw_value: Optional[str] = None
    extraction_method: str = "pattern"
    is_reliable: bool = True

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass
class Classification:
    """Clinical classification with confidence.

    Attributes:
        variant_id: Unique variant identifier (e.g., BRCA1:c.68_69delAG).
        prediction: Clinical classification category.
        confidence: Confidence score object.
        raw_response: Original model output.
        reasoning: Extracted reasoning/explanation (optional).
        metadata: Additional prediction metadata.
    """

    variant_id: str
    prediction: PredictionClass
    confidence: ConfidenceScore
    raw_response: str
    reasoning: Optional[str] = None
    metadata: Optional[Dict] = None

    def is_clinical_grade(self, threshold: float = 0.85) -> bool:
        """Check if classification meets clinical reliability threshold.

        Args:
            threshold: Minimum confidence for clinical use (default: 0.85).

        Returns:
            True if confidence >= threshold and reliable.
        """
        return self.confidence.is_reliable and self.confidence.confidence >= threshold

    def __repr__(self) -> str:
        """Concise classification representation."""
        return (
            f"Classification({self.variant_id}, {self.prediction.value}, "
            f"conf={self.confidence.confidence:.2f})"
        )


def extract_confidence(model_output: str) -> ConfidenceScore:
    """Extract confidence score from MedGemma output.

    Tries multiple extraction patterns in order:
    1. Explicit confidence keywords: "(confidence: 0.92)"
    2. Percentage formats: "92% confident", "confidence of 92%"
    3. Likelihood keywords: "likely", "probable", "uncertain"
    4. Fallback: moderate confidence if no indicators

    Args:
        model_output: Raw text output from MedGemma model.

    Returns:
        ConfidenceScore object with normalized confidence.

    Raises:
        ValueError: If model_output is empty or None.

    Example:
        >>> extract_confidence("This variant is pathogenic (confidence: 0.92)")
        ConfidenceScore(confidence=0.92, method='explicit')
    """
    if not model_output or not model_output.strip():
        raise ValueError("Model output cannot be empty")

    text = model_output.lower()

    # Pattern 1: Explicit confidence (0.XX or X.XX)
    patterns_explicit = [
        r"(\d+)%\s+confidence",  # "87% confidence"
        r"confidence[:\s]+(\d+\.?\d*)",  # "confidence: 0.92"
        r"confidence[:\s]+(\d+)%",  # "confidence: 92%"
        r"\(confidence[:\s]+(\d+\.?\d*)\)",  # "(confidence: 0.92)"
        r"\((\d+\.?\d*)%?\s*confident\)",  # "(92% confident)"
        r"\((\d+\.\d+)\)",  # "(0.94)" in parentheses
    ]

    for pattern in patterns_explicit:
        match = re.search(pattern, text)
        if match:
            raw_value = match.group(1)
            confidence_val = float(raw_value)

            # Normalize if percentage (> 1.0)
            if confidence_val > 1.0:
                confidence_val /= 100.0

            return ConfidenceScore(
                confidence=confidence_val,
                raw_value=raw_value,
                extraction_method="explicit",
                is_reliable=True,
            )

    # Pattern 2: Percentage without "confidence" keyword
    match = re.search(r"(\d+)%\s*(confident|certain|sure)", text)
    if match:
        confidence_val = float(match.group(1)) / 100.0
        return ConfidenceScore(
            confidence=confidence_val,
            raw_value=match.group(1),
            extraction_method="percentage",
            is_reliable=True,
        )

    # Pattern 3: Likelihood keywords (heuristic mapping - order matters!)
    keyword_mapping = [
        ("highly likely", 0.90),
        ("very likely", 0.85),
        ("highly unlikely", 0.15),
        ("very unlikely", 0.20),
        ("unlikely", 0.30),
        ("likely", 0.75),
        ("probable", 0.70),
        ("possibly", 0.60),
        ("uncertain", 0.50),
    ]

    for keyword, conf_value in keyword_mapping:
        if keyword in text:
            logger.debug(f"Extracted confidence from keyword '{keyword}': {conf_value}")
            return ConfidenceScore(
                confidence=conf_value,
                raw_value=keyword,
                extraction_method="keyword",
                is_reliable=False,  # Keyword-based less reliable
            )

    # Fallback: No confidence indicators → moderate uncertainty
    logger.warning(f"No confidence indicators found in: {model_output[:100]}")
    return ConfidenceScore(
        confidence=0.50,
        raw_value=None,
        extraction_method="fallback",
        is_reliable=False,
    )


def classify_prediction(
    model_output: str,
    variant_id: str,
    confidence_threshold: float = 0.85,
) -> Classification:
    """Extract classification and confidence from model output.

    Args:
        model_output: Raw MedGemma response text.
        variant_id: Unique identifier for this variant.
        confidence_threshold: Minimum confidence for clinical grade.

    Returns:
        Classification object with prediction and confidence.

    Example:
        >>> output = "This BRCA1 variant is likely pathogenic (confidence: 0.92)"
        >>> classify_prediction(output, "BRCA1:c.68_69delAG")
        Classification(BRCA1:c.68_69delAG, likely_pathogenic, conf=0.92)
    """
    text_lower = model_output.lower()

    # Extract prediction class (order matters: most specific first)
    prediction = PredictionClass.UNKNOWN

    if "pathogenic" in text_lower:
        if "likely pathogenic" in text_lower:
            prediction = PredictionClass.LIKELY_PATHOGENIC
        elif "benign" not in text_lower:  # Avoid "not pathogenic"
            prediction = PredictionClass.PATHOGENIC
    elif "benign" in text_lower:
        if "likely benign" in text_lower:
            prediction = PredictionClass.LIKELY_BENIGN
        else:
            prediction = PredictionClass.BENIGN
    elif any(word in text_lower for word in ["uncertain", "unknown", "unclear", "vus"]):
        prediction = PredictionClass.UNCERTAIN

    # Extract confidence
    confidence = extract_confidence(model_output)

    # Extract reasoning (first sentence after classification)
    reasoning = _extract_reasoning(model_output)

    return Classification(
        variant_id=variant_id,
        prediction=prediction,
        confidence=confidence,
        raw_response=model_output,
        reasoning=reasoning,
        metadata={
            "clinical_grade": confidence.confidence >= confidence_threshold,
            "threshold": confidence_threshold,
        },
    )


def _extract_reasoning(model_output: str) -> Optional[str]:
    """Extract reasoning/explanation from model output.

    Args:
        model_output: Raw model response.

    Returns:
        Extracted reasoning string, or None if not found.
    """
    # Look for common reasoning patterns
    patterns = [
        r"because\s+(.+?)(?:\.|$)",
        r"this is due to\s+(.+?)(?:\.|$)",
        r"reasoning:\s+(.+?)(?:\.|$)",
        r"explanation:\s+(.+?)(?:\.|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, model_output.lower())
        if match:
            reasoning = match.group(1).strip()
            # Return first 200 chars max
            return reasoning[:200] if len(reasoning) > 200 else reasoning

    return None


def filter_low_confidence(
    classifications: List[Classification],
    threshold: float = 0.85,
) -> Tuple[List[Classification], List[Classification]]:
    """Separate classifications by confidence threshold.

    Args:
        classifications: List of Classification objects.
        threshold: Confidence threshold (default: 0.85 for clinical grade).

    Returns:
        Tuple of (high_confidence, low_confidence) classification lists.

    Example:
        >>> high, low = filter_low_confidence(classifications, threshold=0.85)
        >>> print(f"{len(high)} clinical-grade, {len(low)} need review")
    """
    high_confidence = [c for c in classifications if c.is_clinical_grade(threshold)]
    low_confidence = [c for c in classifications if not c.is_clinical_grade(threshold)]

    logger.info(
        f"Filtered {len(classifications)} classifications: "
        f"{len(high_confidence)} high confidence (≥{threshold}), "
        f"{len(low_confidence)} low confidence"
    )

    return high_confidence, low_confidence


def confidence_report(
    classifications: List[Classification],
) -> Dict[str, any]:
    """Generate summary statistics for confidence distribution.

    Args:
        classifications: List of Classification objects.

    Returns:
        Dictionary with:
            - total: Total classifications
            - avg_confidence: Mean confidence
            - high_confidence_count: Count ≥0.85
            - low_confidence_count: Count <0.85
            - by_prediction: Breakdown per prediction class
            - confidence_distribution: Histogram bins

    Example:
        >>> report = confidence_report(classifications)
        >>> print(f"Average confidence: {report['avg_confidence']:.2%}")
    """
    if not classifications:
        return {
            "total": 0,
            "avg_confidence": 0.0,
            "high_confidence_count": 0,
            "low_confidence_count": 0,
        }

    confidences = [c.confidence.confidence for c in classifications]
    avg_confidence = sum(confidences) / len(confidences)

    high_conf, low_conf = filter_low_confidence(classifications)

    # Count by prediction class
    by_prediction = {}
    for pred_class in PredictionClass:
        count = sum(1 for c in classifications if c.prediction == pred_class)
        if count > 0:
            by_prediction[pred_class.value] = count

    # Confidence distribution (bins: 0-0.5, 0.5-0.7, 0.7-0.85, 0.85-1.0)
    bins = {"0.0-0.5": 0, "0.5-0.7": 0, "0.7-0.85": 0, "0.85-1.0": 0}
    for conf in confidences:
        if conf < 0.5:
            bins["0.0-0.5"] += 1
        elif conf < 0.7:
            bins["0.5-0.7"] += 1
        elif conf < 0.85:
            bins["0.7-0.85"] += 1
        else:
            bins["0.85-1.0"] += 1

    return {
        "total": len(classifications),
        "avg_confidence": avg_confidence,
        "high_confidence_count": len(high_conf),
        "low_confidence_count": len(low_conf),
        "by_prediction": by_prediction,
        "confidence_distribution": bins,
        "min_confidence": min(confidences),
        "max_confidence": max(confidences),
    }
