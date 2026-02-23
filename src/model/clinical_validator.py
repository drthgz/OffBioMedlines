"""Clinical Validation Module.

Validates variant predictions against gold standard datasets (ClinVar/COSMIC),
calculates accuracy metrics, and identifies discordant cases for review.

Example:
    >>> validator = ClinicalValidator("data/gold_standards/clinvar_pathogenic.json")
    >>> report = validator.validate_batch(predictions)
    >>> print(f"Accuracy: {report['accuracy']:.2%}")
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.model.confidence import Classification, PredictionClass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GoldStandardVariant:
    """Reference variant from validated clinical database.

    Attributes:
        variant_id: Unique identifier (e.g., BRCA1:c.68_69delAG).
        gene: Gene symbol.
        known_classification: Validated clinical classification.
        clinvar_id: ClinVar accession (if available).
        evidence_level: Strength of evidence (1-5 stars).
    """

    variant_id: str
    gene: str
    known_classification: str
    clinvar_id: Optional[str] = None
    evidence_level: Optional[str] = None
    population_frequency: Optional[float] = None


@dataclass
class DiscordantCase:
    """Variant where prediction disagrees with gold standard.

    Attributes:
        variant_id: Variant identifier.
        predicted: Model prediction.
        expected: Gold standard classification.
        confidence: Prediction confidence.
        gene: Gene symbol.
    """

    variant_id: str
    predicted: str
    expected: str
    confidence: float
    gene: str

    def __repr__(self) -> str:
        return (
            f"Discordant({self.variant_id}: predicted={self.predicted}, "
            f"expected={self.expected}, conf={self.confidence:.2f})"
        )


class ClinicalValidator:
    """Validate variant predictions against clinical gold standards.

    Loads reference datasets and computes accuracy metrics including
    sensitivity, specificity, precision, F1 score, and per-gene breakdown.

    Attributes:
        gold_standard: Dictionary of variant_id -> GoldStandardVariant.
        total_variants: Count of reference variants loaded.

    Example:
        >>> validator = ClinicalValidator("data/gold_standards/clinvar_pathogenic.json")
        >>> predictions = [Classification(...), ...]
        >>> report = validator.validate_batch(predictions)
        >>> print(f"Sensitivity: {report['sensitivity']:.2%}")
    """

    def __init__(self, gold_standard_path: str) -> None:
        """Initialize validator with gold standard dataset.

        Args:
            gold_standard_path: Path to JSON file with validated variants.

        Raises:
            FileNotFoundError: Gold standard file not found.
            ValueError: Invalid JSON format.
        """
        self.gold_standard_path = Path(gold_standard_path)
        self.gold_standard: Dict[str, GoldStandardVariant] = {}

        if not self.gold_standard_path.exists():
            raise FileNotFoundError(
                f"Gold standard file not found: {gold_standard_path}"
            )

        self._load_gold_standard()
        logger.info(
            f"Loaded {len(self.gold_standard)} gold standard variants "
            f"from {self.gold_standard_path.name}"
        )

    def _load_gold_standard(self) -> None:
        """Load and parse gold standard JSON file."""
        with open(self.gold_standard_path, "r") as f:
            data = json.load(f)

        if "variants" not in data:
            raise ValueError("Gold standard JSON must contain 'variants' key")

        for variant in data["variants"]:
            gs_variant = GoldStandardVariant(
                variant_id=variant["variant_id"],
                gene=variant["gene"],
                known_classification=variant["known_classification"],
                clinvar_id=variant.get("clinvar_id"),
                evidence_level=variant.get("evidence_level"),
                population_frequency=variant.get("population_frequency"),
            )
            self.gold_standard[gs_variant.variant_id] = gs_variant

    @property
    def total_variants(self) -> int:
        """Total number of gold standard variants."""
        return len(self.gold_standard)

    def validate_batch(
        self,
        predictions: List[Classification],
        min_confidence: float = 0.0,
    ) -> Dict:
        """Validate predictions against gold standard.

        Args:
            predictions: List of Classification objects from model.
            min_confidence: Minimum confidence threshold (default: 0.0).

        Returns:
            Dictionary containing:
                - accuracy: Overall accuracy (0-1)
                - sensitivity: True positive rate
                - specificity: True negative rate
                - precision: Positive predictive value
                - f1_score: Harmonic mean of precision and recall
                - total_evaluated: Number of predictions evaluated
                - correct: Number of correct predictions
                - incorrect: Number of incorrect predictions
                - discordant_cases: List of DiscordantCase objects
                - per_gene_metrics: Dict of gene -> metrics

        Example:
            >>> report = validator.validate_batch(predictions, min_confidence=0.85)
            >>> print(f"F1 Score: {report['f1_score']:.3f}")
        """
        # Filter predictions by confidence
        filtered_predictions = [
            p for p in predictions if p.confidence.confidence >= min_confidence
        ]

        if not filtered_predictions:
            logger.warning("No predictions meet confidence threshold")
            return self._empty_report()

        # Match predictions to gold standard
        matched_predictions = []
        for pred in filtered_predictions:
            if pred.variant_id in self.gold_standard:
                matched_predictions.append(pred)

        if not matched_predictions:
            logger.warning("No predictions match gold standard variants")
            return self._empty_report()

        # Calculate metrics
        tp, tn, fp, fn = 0, 0, 0, 0
        correct = 0
        discordant_cases = []

        for pred in matched_predictions:
            gs_variant = self.gold_standard[pred.variant_id]
            predicted_class = self._normalize_classification(pred.prediction.value)
            expected_class = self._normalize_classification(
                gs_variant.known_classification
            )

            if predicted_class == expected_class:
                correct += 1
                # True positive or true negative
                if expected_class == "pathogenic":
                    tp += 1
                elif expected_class == "benign":
                    tn += 1
            else:
                # Discordant case
                discordant_cases.append(
                    DiscordantCase(
                        variant_id=pred.variant_id,
                        predicted=predicted_class,
                        expected=expected_class,
                        confidence=pred.confidence.confidence,
                        gene=gs_variant.gene,
                    )
                )

                # False positive or false negative
                if predicted_class == "pathogenic" and expected_class == "benign":
                    fp += 1
                elif predicted_class == "benign" and expected_class == "pathogenic":
                    fn += 1

        # Calculate overall metrics
        total = len(matched_predictions)
        accuracy = correct / total if total > 0 else 0.0

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1_score = (
            2 * (precision * sensitivity) / (precision + sensitivity)
            if (precision + sensitivity) > 0
            else 0.0
        )

        # Per-gene analysis
        per_gene_metrics = self._calculate_per_gene_metrics(matched_predictions)

        logger.info(
            f"Validation complete: {correct}/{total} correct (accuracy={accuracy:.2%})"
        )

        return {
            "accuracy": accuracy,
            "sensitivity": sensitivity,
            "specificity": specificity,
            "precision": precision,
            "f1_score": f1_score,
            "total_evaluated": total,
            "correct": correct,
            "incorrect": total - correct,
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "discordant_cases": discordant_cases,
            "per_gene_metrics": per_gene_metrics,
            "min_confidence_threshold": min_confidence,
        }

    def _normalize_classification(self, classification: str) -> str:
        """Normalize classification to binary pathogenic/benign.

        Args:
            classification: Raw classification string.

        Returns:
            Normalized classification ("pathogenic", "benign", "uncertain").
        """
        classification = classification.lower()

        if "pathogenic" in classification and "benign" not in classification:
            return "pathogenic"
        elif "benign" in classification and "pathogenic" not in classification:
            return "benign"
        else:
            return "uncertain"

    def _calculate_per_gene_metrics(
        self, predictions: List[Classification]
    ) -> Dict[str, Dict]:
        """Calculate accuracy metrics per gene.

        Args:
            predictions: List of predictions matched to gold standard.

        Returns:
            Dictionary mapping gene -> {accuracy, total, correct, incorrect}.
        """
        gene_stats = {}

        for pred in predictions:
            gs_variant = self.gold_standard[pred.variant_id]
            gene = gs_variant.gene

            if gene not in gene_stats:
                gene_stats[gene] = {"total": 0, "correct": 0}

            gene_stats[gene]["total"] += 1

            predicted = self._normalize_classification(pred.prediction.value)
            expected = self._normalize_classification(gs_variant.known_classification)

            if predicted == expected:
                gene_stats[gene]["correct"] += 1

        # Calculate accuracy per gene
        per_gene_metrics = {}
        for gene, stats in gene_stats.items():
            accuracy = stats["correct"] / stats["total"]
            per_gene_metrics[gene] = {
                "accuracy": accuracy,
                "total": stats["total"],
                "correct": stats["correct"],
                "incorrect": stats["total"] - stats["correct"],
            }

        return per_gene_metrics

    def _empty_report(self) -> Dict:
        """Return empty validation report."""
        return {
            "accuracy": 0.0,
            "sensitivity": 0.0,
            "specificity": 0.0,
            "precision": 0.0,
            "f1_score": 0.0,
            "total_evaluated": 0,
            "correct": 0,
            "incorrect": 0,
            "true_positives": 0,
            "true_negatives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "discordant_cases": [],
            "per_gene_metrics": {},
        }

    def identify_discordant_cases(
        self, predictions: List[Classification]
    ) -> List[DiscordantCase]:
        """Find all predictions that disagree with gold standard.

        Args:
            predictions: List of Classification objects.

        Returns:
            List of DiscordantCase objects for manual review.
        """
        report = self.validate_batch(predictions)
        return report["discordant_cases"]

    def get_gene_performance(self, gene: str) -> Optional[Dict]:
        """Get performance metrics for specific gene.

        Args:
            gene: Gene symbol (e.g., "BRCA1").

        Returns:
            Dictionary with gene-specific metrics, or None if not found.
        """
        # Filter gold standard to gene
        gene_variants = [v for v in self.gold_standard.values() if v.gene == gene]

        if not gene_variants:
            logger.warning(f"No gold standard variants for gene: {gene}")
            return None

        return {
            "gene": gene,
            "total_variants": len(gene_variants),
            "variant_ids": [v.variant_id for v in gene_variants],
        }


def load_gold_standard(filepath: str) -> Dict[str, GoldStandardVariant]:
    """Convenience function to load gold standard variants.

    Args:
        filepath: Path to gold standard JSON file.

    Returns:
        Dictionary of variant_id -> GoldStandardVariant.

    Example:
        >>> gold_std = load_gold_standard("data/gold_standards/clinvar_pathogenic.json")
        >>> print(f"Loaded {len(gold_std)} variants")
    """
    validator = ClinicalValidator(filepath)
    return validator.gold_standard
