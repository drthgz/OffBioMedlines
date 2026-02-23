"""Unit tests for confidence extraction module.

Tests confidence score extraction, classification, and filtering
from MedGemma model outputs.
"""

import pytest

from src.model.confidence import (
    Classification,
    ConfidenceScore,
    PredictionClass,
    classify_prediction,
    confidence_report,
    extract_confidence,
    filter_low_confidence,
)


class TestConfidenceExtraction:
    """Test confidence score extraction from various formats."""

    def test_explicit_confidence_decimal(self):
        """Test extraction from explicit decimal format."""
        output = "This variant is pathogenic (confidence: 0.92)"
        score = extract_confidence(output)

        assert score.confidence == 0.92
        assert score.extraction_method == "explicit"
        assert score.is_reliable is True

    def test_explicit_confidence_percentage(self):
        """Test extraction from percentage format."""
        output = "Likely pathogenic with 87% confidence"
        score = extract_confidence(output)

        assert score.confidence == 0.87
        assert score.extraction_method == "explicit"
        assert score.is_reliable is True

    def test_confidence_in_parentheses(self):
        """Test extraction from parenthetical confidence."""
        output = "Classification: pathogenic (confidence: 0.95)"
        score = extract_confidence(output)

        assert score.confidence == 0.95
        assert score.raw_value == "0.95"

    def test_percentage_without_keyword(self):
        """Test extraction from standalone percentage."""
        output = "This variant is 88% certain to be pathogenic"
        score = extract_confidence(output)

        assert score.confidence == 0.88
        assert score.extraction_method == "percentage"

    def test_likelihood_keywords(self):
        """Test extraction from likelihood keywords."""
        test_cases = [
            ("This is highly likely pathogenic", 0.90),
            ("This is likely benign", 0.75),
            ("This is uncertain", 0.50),
            ("This is unlikely to be pathogenic", 0.30),
        ]

        for output, expected_conf in test_cases:
            score = extract_confidence(output)
            assert score.confidence == expected_conf
            assert score.extraction_method == "keyword"
            assert score.is_reliable is False  # Keywords less reliable

    def test_no_confidence_indicators(self):
        """Test fallback when no confidence found."""
        output = "This is a variant in the BRCA1 gene"
        score = extract_confidence(output)

        assert score.confidence == 0.50  # Default fallback
        assert score.extraction_method == "fallback"
        assert score.is_reliable is False

    def test_empty_input_raises_error(self):
        """Test error handling for empty input."""
        with pytest.raises(ValueError, match="cannot be empty"):
            extract_confidence("")

        with pytest.raises(ValueError, match="cannot be empty"):
            extract_confidence(None)

    def test_confidence_score_validation(self):
        """Test ConfidenceScore validates range."""
        # Valid range
        score = ConfidenceScore(confidence=0.85)
        assert score.confidence == 0.85

        # Invalid: too high
        with pytest.raises(ValueError, match="must be in"):
            ConfidenceScore(confidence=1.5)

        # Invalid: negative
        with pytest.raises(ValueError, match="must be in"):
            ConfidenceScore(confidence=-0.1)


class TestClassificationExtraction:
    """Test clinical classification extraction from model output."""

    def test_classify_pathogenic(self):
        """Test pathogenic classification."""
        output = "This BRCA1 variant is pathogenic (confidence: 0.92)"
        classification = classify_prediction(output, "BRCA1:c.68_69delAG")

        assert classification.variant_id == "BRCA1:c.68_69delAG"
        assert classification.prediction == PredictionClass.PATHOGENIC
        assert classification.confidence.confidence == 0.92
        assert classification.is_clinical_grade()

    def test_classify_likely_pathogenic(self):
        """Test likely pathogenic classification."""
        output = "This variant is likely pathogenic (85% confident)"
        classification = classify_prediction(output, "BRCA2:c.1687C>T")

        assert classification.prediction == PredictionClass.LIKELY_PATHOGENIC
        assert classification.confidence.confidence == 0.85

    def test_classify_benign(self):
        """Test benign classification."""
        output = "This variant is benign with high confidence (0.94)"
        classification = classify_prediction(output, "TP53:c.215C>G")

        assert classification.prediction == PredictionClass.BENIGN
        assert classification.confidence.confidence == 0.94

    def test_classify_likely_benign(self):
        """Test likely benign classification."""
        output = "This is likely benign (confidence: 0.78)"
        classification = classify_prediction(output, "EGFR:c.2573T>G")

        assert classification.prediction == PredictionClass.LIKELY_BENIGN
        assert classification.confidence.confidence == 0.78

    def test_classify_uncertain(self):
        """Test uncertain significance classification."""
        output = "This variant has uncertain significance (VUS)"
        classification = classify_prediction(output, "KRAS:c.35G>A")

        assert classification.prediction == PredictionClass.UNCERTAIN
        assert classification.confidence.confidence == 0.50  # Fallback

    def test_classify_unknown(self):
        """Test unknown classification fallback."""
        output = "Unable to determine classification for this variant"
        classification = classify_prediction(output, "UNKNOWN:c.123A>T")

        assert classification.prediction == PredictionClass.UNKNOWN

    def test_clinical_grade_threshold(self):
        """Test clinical grade threshold logic."""
        # Above threshold
        output_high = "Pathogenic (confidence: 0.90)"
        class_high = classify_prediction(output_high, "VAR1")
        assert class_high.is_clinical_grade(threshold=0.85) is True

        # Below threshold
        output_low = "Pathogenic (confidence: 0.70)"
        class_low = classify_prediction(output_low, "VAR2")
        assert class_low.is_clinical_grade(threshold=0.85) is False

    def test_reasoning_extraction(self):
        """Test reasoning extraction from output."""
        output = "Pathogenic because this causes a frameshift mutation."
        classification = classify_prediction(output, "BRCA1:c.68_69delAG")

        assert classification.reasoning is not None
        assert "frameshift" in classification.reasoning.lower()

    def test_metadata_includes_threshold(self):
        """Test metadata contains threshold information."""
        output = "Pathogenic (confidence: 0.90)"
        classification = classify_prediction(output, "VAR1", confidence_threshold=0.85)

        assert classification.metadata["threshold"] == 0.85
        assert classification.metadata["clinical_grade"] is True


class TestConfidenceFiltering:
    """Test filtering classifications by confidence."""

    def test_filter_by_threshold(self):
        """Test filtering separates high and low confidence."""
        classifications = [
            Classification(
                "VAR1",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.92),
                "output1",
            ),
            Classification(
                "VAR2",
                PredictionClass.BENIGN,
                ConfidenceScore(0.75),
                "output2",
            ),
            Classification(
                "VAR3",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.88),
                "output3",
            ),
            Classification(
                "VAR4",
                PredictionClass.UNCERTAIN,
                ConfidenceScore(0.50),
                "output4",
            ),
        ]

        high, low = filter_low_confidence(classifications, threshold=0.85)

        assert len(high) == 2  # 0.92, 0.88
        assert len(low) == 2  # 0.75, 0.50
        assert all(c.confidence.confidence >= 0.85 for c in high)
        assert all(c.confidence.confidence < 0.85 for c in low)

    def test_filter_empty_list(self):
        """Test filtering handles empty list."""
        high, low = filter_low_confidence([], threshold=0.85)

        assert len(high) == 0
        assert len(low) == 0

    def test_filter_all_high_confidence(self):
        """Test filtering when all meet threshold."""
        classifications = [
            Classification(
                f"VAR{i}",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.90),
                f"output{i}",
            )
            for i in range(5)
        ]

        high, low = filter_low_confidence(classifications, threshold=0.85)

        assert len(high) == 5
        assert len(low) == 0


class TestConfidenceReport:
    """Test confidence summary report generation."""

    def test_report_basic_statistics(self):
        """Test report contains basic statistics."""
        classifications = [
            Classification(
                "VAR1",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.90),
                "output1",
            ),
            Classification(
                "VAR2",
                PredictionClass.BENIGN,
                ConfidenceScore(0.70),
                "output2",
            ),
            Classification(
                "VAR3",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.85),
                "output3",
            ),
        ]

        report = confidence_report(classifications)

        assert report["total"] == 3
        assert report["avg_confidence"] == pytest.approx(0.8166, abs=0.01)
        assert report["high_confidence_count"] == 2  # 0.90, 0.85
        assert report["low_confidence_count"] == 1  # 0.70

    def test_report_by_prediction_class(self):
        """Test report breaks down by prediction class."""
        classifications = [
            Classification(
                "VAR1",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.90),
                "out1",
            ),
            Classification(
                "VAR2",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.88),
                "out2",
            ),
            Classification(
                "VAR3",
                PredictionClass.BENIGN,
                ConfidenceScore(0.85),
                "out3",
            ),
        ]

        report = confidence_report(classifications)

        assert report["by_prediction"]["pathogenic"] == 2
        assert report["by_prediction"]["benign"] == 1

    def test_report_confidence_distribution(self):
        """Test report includes confidence distribution bins."""
        classifications = [
            Classification(
                "VAR1",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.40),
                "out1",
            ),  # 0-0.5
            Classification(
                "VAR2",
                PredictionClass.BENIGN,
                ConfidenceScore(0.60),
                "out2",
            ),  # 0.5-0.7
            Classification(
                "VAR3",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.75),
                "out3",
            ),  # 0.7-0.85
            Classification(
                "VAR4",
                PredictionClass.BENIGN,
                ConfidenceScore(0.92),
                "out4",
            ),  # 0.85-1.0
        ]

        report = confidence_report(classifications)
        bins = report["confidence_distribution"]

        assert bins["0.0-0.5"] == 1
        assert bins["0.5-0.7"] == 1
        assert bins["0.7-0.85"] == 1
        assert bins["0.85-1.0"] == 1

    def test_report_empty_list(self):
        """Test report handles empty classification list."""
        report = confidence_report([])

        assert report["total"] == 0
        assert report["avg_confidence"] == 0.0
        assert report["high_confidence_count"] == 0

    def test_report_min_max_confidence(self):
        """Test report includes min/max confidence."""
        classifications = [
            Classification(
                "VAR1",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.45),
                "out1",
            ),
            Classification(
                "VAR2",
                PredictionClass.BENIGN,
                ConfidenceScore(0.95),
                "out2",
            ),
            Classification(
                "VAR3",
                PredictionClass.PATHOGENIC,
                ConfidenceScore(0.70),
                "out3",
            ),
        ]

        report = confidence_report(classifications)

        assert report["min_confidence"] == 0.45
        assert report["max_confidence"] == 0.95


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
