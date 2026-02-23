"""Unit tests for clinical validation module."""

import json
import pytest
from pathlib import Path

from src.model.clinical_validator import (
    ClinicalValidator,
    DiscordantCase,
    GoldStandardVariant,
    load_gold_standard,
)
from src.model.confidence import (
    Classification,
    ConfidenceScore,
    PredictionClass,
)


@pytest.fixture
def temp_gold_standard(tmp_path):
    """Create temporary gold standard file."""
    data = {
        "metadata": {
            "source": "Test",
            "version": "1.0",
            "total_variants": 6,
        },
        "variants": [
            {
                "variant_id": "BRCA1:c.68_69delAG",
                "gene": "BRCA1",
                "known_classification": "pathogenic",
                "clinvar_id": "RCV000000051",
                "evidence_level": "5_star",
            },
            {
                "variant_id": "BRCA1:c.181T>G",
                "gene": "BRCA1",
                "known_classification": "pathogenic",
                "clinvar_id": "RCV000000053",
                "evidence_level": "4_star",
            },
            {
                "variant_id": "BRCA2:c.1687C>T",
                "gene": "BRCA2",
                "known_classification": "likely_pathogenic",
                "clinvar_id": "RCV000000120",
            },
            {
                "variant_id": "TP53:c.733G>A",
                "gene": "TP53",
                "known_classification": "pathogenic",
                "clinvar_id": "RCV000000200",
            },
            {
                "variant_id": "BRCA1:c.3840C>T",
                "gene": "BRCA1",
                "known_classification": "benign",
                "clinvar_id": "RCV000001000",
            },
            {
                "variant_id": "TP53:c.639A>G",
                "gene": "TP53",
                "known_classification": "benign",
                "clinvar_id": "RCV000001001",
            },
        ],
    }

    filepath = tmp_path / "test_gold_standard.json"
    with open(filepath, "w") as f:
        json.dump(data, f)

    return str(filepath)


class TestClinicalValidator:
    """Test clinical validation functionality."""

    def test_validator_initialization(self, temp_gold_standard):
        """Test validator can be initialized."""
        validator = ClinicalValidator(temp_gold_standard)

        assert validator.total_variants == 6
        assert len(validator.gold_standard) == 6
        assert "BRCA1:c.68_69delAG" in validator.gold_standard

    def test_file_not_found_raises_error(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            ClinicalValidator("nonexistent.json")

    def test_load_gold_standard_variants(self, temp_gold_standard):
        """Test gold standard variants loaded correctly."""
        validator = ClinicalValidator(temp_gold_standard)

        brca1_variant = validator.gold_standard["BRCA1:c.68_69delAG"]
        assert brca1_variant.gene == "BRCA1"
        assert brca1_variant.known_classification == "pathogenic"
        assert brca1_variant.clinvar_id == "RCV000000051"

    def test_perfect_predictions(self, temp_gold_standard):
        """Test validation with 100% accurate predictions."""
        validator = ClinicalValidator(temp_gold_standard)

        # Create perfect predictions
        predictions = [
            Classification(
                "BRCA1:c.68_69delAG",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.95),
                "output",
            ),
            Classification(
                "BRCA1:c.181T>G",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.92),
                "output",
            ),
            Classification(
                "TP53:c.733G>A",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.98),
                "output",
            ),
            Classification(
                "BRCA1:c.3840C>T",
                PredictionClass.BENIGN,
                ConfidenceScore(0.91),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions)

        assert report["accuracy"] == 1.0
        assert report["total_evaluated"] == 4
        assert report["correct"] == 4
        assert report["incorrect"] == 0
        assert len(report["discordant_cases"]) == 0

    def test_imperfect_predictions(self, temp_gold_standard):
        """Test validation with some incorrect predictions."""
        validator = ClinicalValidator(temp_gold_standard)

        predictions = [
            # Correct
            Classification(
                "BRCA1:c.68_69delAG",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.95),
                "output",
            ),
            # Incorrect: predicts benign, should be pathogenic
            Classification(
                "BRCA1:c.181T>G",
                PredictionClass.BENIGN,
                ConfidenceScore(0.70),
                "output",
            ),
            # Correct
            Classification(
                "BRCA1:c.3840C>T",
                PredictionClass.BENIGN,
                ConfidenceScore(0.91),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions)

        assert report["total_evaluated"] == 3
        assert report["correct"] == 2
        assert report["incorrect"] == 1
        assert report["accuracy"] == pytest.approx(0.6666, abs=0.01)
        assert len(report["discordant_cases"]) == 1

    def test_discordant_case_identification(self, temp_gold_standard):
        """Test identification of discordant cases."""
        validator = ClinicalValidator(temp_gold_standard)

        predictions = [
            # Wrong prediction
            Classification(
                "BRCA1:c.68_69delAG",
                PredictionClass.BENIGN,
                ConfidenceScore(0.60),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions)
        discordant = report["discordant_cases"]

        assert len(discordant) == 1
        case = discordant[0]
        assert case.variant_id == "BRCA1:c.68_69delAG"
        assert case.predicted == "benign"
        assert case.expected == "pathogenic"
        assert case.confidence == 0.60
        assert case.gene == "BRCA1"

    def test_confidence_filtering(self, temp_gold_standard):
        """Test minimum confidence threshold filtering."""
        validator = ClinicalValidator(temp_gold_standard)

        predictions = [
            # High confidence
            Classification(
                "BRCA1:c.68_69delAG",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.95),
                "output",
            ),
            # Low confidence (should be filtered)
            Classification(
                "BRCA1:c.181T>G",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.50),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions, min_confidence=0.85)

        # Only high confidence prediction evaluated
        assert report["total_evaluated"] == 1
        assert report["correct"] == 1

    def test_sensitivity_specificity_calculation(self, temp_gold_standard):
        """Test sensitivity and specificity metrics."""
        validator = ClinicalValidator(temp_gold_standard)

        predictions = [
            # True Positive
            Classification(
                "BRCA1:c.68_69delAG",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.95),
                "output",
            ),
            # True Negative
            Classification(
                "BRCA1:c.3840C>T",
                PredictionClass.BENIGN,
                ConfidenceScore(0.91),
                "output",
            ),
            # False Negative (predict benign, actually pathogenic)
            Classification(
                "TP53:c.733G>A",
                PredictionClass.BENIGN,
                ConfidenceScore(0.70),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions)

        assert report["true_positives"] == 1
        assert report["true_negatives"] == 1
        assert report["false_negatives"] == 1
        assert report["false_positives"] == 0

        # Sensitivity = TP / (TP + FN) = 1/2 = 0.5
        assert report["sensitivity"] == 0.5

        # Specificity = TN / (TN + FP) = 1/1 = 1.0
        assert report["specificity"] == 1.0

    def test_f1_score_calculation(self, temp_gold_standard):
        """Test F1 score calculation."""
        validator = ClinicalValidator(temp_gold_standard)

        predictions = [
            Classification(
                "BRCA1:c.68_69delAG",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.95),
                "output",
            ),
            Classification(
                "BRCA1:c.3840C>T",
                PredictionClass.BENIGN,
                ConfidenceScore(0.91),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions)

        # Perfect predictions: F1 = 1.0
        assert report["f1_score"] == 1.0

    def test_per_gene_metrics(self, temp_gold_standard):
        """Test per-gene performance breakdown."""
        validator = ClinicalValidator(temp_gold_standard)

        predictions = [
            # BRCA1: 2 correct
            Classification(
                "BRCA1:c.68_69delAG",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.95),
                "output",
            ),
            Classification(
                "BRCA1:c.181T>G",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.92),
                "output",
            ),
            # TP53: 1 correct, 1 incorrect
            Classification(
                "TP53:c.733G>A",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.98),
                "output",
            ),
            Classification(
                "TP53:c.639A>G",
                PredictionClass.PATHOGENIC,  # Wrong, should be benign
                ConfidenceScore(0.70),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions)
        per_gene = report["per_gene_metrics"]

        assert "BRCA1" in per_gene
        assert per_gene["BRCA1"]["accuracy"] == 1.0
        assert per_gene["BRCA1"]["total"] == 2

        assert "TP53" in per_gene
        assert per_gene["TP53"]["accuracy"] == 0.5
        assert per_gene["TP53"]["correct"] == 1
        assert per_gene["TP53"]["incorrect"] == 1

    def test_empty_predictions(self, temp_gold_standard):
        """Test handling of empty prediction list."""
        validator = ClinicalValidator(temp_gold_standard)

        report = validator.validate_batch([])

        assert report["total_evaluated"] == 0
        assert report["accuracy"] == 0.0

    def test_no_matching_variants(self, temp_gold_standard):
        """Test predictions with no gold standard matches."""
        validator = ClinicalValidator(temp_gold_standard)

        predictions = [
            Classification(
                "UNKNOWN:c.999A>T",
                PredictionClass.UNCERTAIN,
                ConfidenceScore(0.50),
                "output",
            ),
        ]

        report = validator.validate_batch(predictions)

        assert report["total_evaluated"] == 0

    def test_get_gene_performance(self, temp_gold_standard):
        """Test gene-specific performance query."""
        validator = ClinicalValidator(temp_gold_standard)

        brca1_perf = validator.get_gene_performance("BRCA1")

        assert brca1_perf is not None
        assert brca1_perf["gene"] == "BRCA1"
        assert brca1_perf["total_variants"] == 3  # 3 BRCA1 variants in test data
        assert "BRCA1:c.68_69delAG" in brca1_perf["variant_ids"]

    def test_load_gold_standard_convenience(self, temp_gold_standard):
        """Test convenience function for loading gold standard."""
        gold_std = load_gold_standard(temp_gold_standard)

        assert len(gold_std) == 6
        assert isinstance(gold_std["BRCA1:c.68_69delAG"], GoldStandardVariant)


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
