"""Unit tests for report generation module."""

import json
import pytest
from pathlib import Path

from src.model.report_generator import (
    ReportGenerator,
    ReportMetadata,
    generate_all_reports,
)
from src.model.confidence import (
    Classification,
    ConfidenceScore,
    PredictionClass,
)
from src.model.clinical_validator import DiscordantCase


@pytest.fixture
def sample_validation_report():
    """Create sample validation report."""
    return {
        "accuracy": 0.875,
        "sensitivity": 0.90,
        "specificity": 0.85,
        "precision": 0.88,
        "f1_score": 0.890,
        "true_positives": 18,
        "true_negatives": 17,
        "false_positives": 3,
        "false_negatives": 2,
        "total_evaluated": 40,
        "correct": 35,
        "incorrect": 5,
        "per_gene_metrics": {
            "BRCA1": {"total": 10, "correct": 9, "incorrect": 1, "accuracy": 0.90},
            "BRCA2": {"total": 10, "correct": 8, "incorrect": 2, "accuracy": 0.80},
            "TP53": {"total": 10, "correct": 10, "incorrect": 0, "accuracy": 1.00},
        },
        "discordant_cases": [
            DiscordantCase("BRCA1:c.123A>G", "benign", "pathogenic", 0.75, "BRCA1"),
            DiscordantCase("BRCA2:c.456T>C", "pathogenic", "benign", 0.82, "BRCA2"),
        ],
    }


@pytest.fixture
def sample_classifications():
    """Create sample classifications."""
    return [
        Classification(
            "VAR1",
            PredictionClass.PATHOGENIC,
            ConfidenceScore(0.95),
            "High confidence pathogenic",
            reasoning="Frameshift mutation",
        ),
        Classification(
            "VAR2",
            PredictionClass.BENIGN,
            ConfidenceScore(0.88),
            "Benign variant",
            reasoning="Synonymous change",
        ),
        Classification(
            "VAR3",
            PredictionClass.UNCERTAIN,
            ConfidenceScore(0.55),
            "Uncertain significance",
        ),
        Classification(
            "VAR4",
            PredictionClass.LIKELY_PATHOGENIC,
            ConfidenceScore(0.78),
            "Likely pathogenic",
        ),
    ]


class TestReportGenerator:
    """Test report generation functionality."""

    def test_generator_initialization(self):
        """Test generator can be initialized."""
        generator = ReportGenerator()
        assert generator is not None

    def test_generate_html(
        self, tmp_path, sample_validation_report, sample_classifications
    ):
        """Test HTML report generation."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.html"

        result = generator.generate_html(
            sample_validation_report, str(output_path), sample_classifications
        )

        assert Path(result).exists()
        html_content = Path(result).read_text()
        assert "Clinical Validation Report" in html_content
        assert "87.5%" in html_content or "0.875" in html_content  # Accuracy
        assert "BRCA1" in html_content
        assert "Discordant Cases" in html_content

    def test_html_contains_metrics(self, tmp_path, sample_validation_report):
        """Test HTML includes all key metrics."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.html"

        result = generator.generate_html(sample_validation_report, str(output_path))
        html_content = Path(result).read_text()

        # Check for metrics
        assert "Accuracy" in html_content
        assert "Sensitivity" in html_content
        assert "Specificity" in html_content
        assert "F1 Score" in html_content

        # Check for confusion matrix
        assert "True Positives" in html_content
        assert "False Negatives" in html_content

    def test_generate_json(self, tmp_path, sample_validation_report):
        """Test JSON report generation."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.json"

        metadata = ReportMetadata(
            generated_at="2026-02-22T10:00:00",
            vcf_file="test.vcf",
            total_variants=40,
        )

        result = generator.generate_json(
            sample_validation_report, str(output_path), metadata
        )

        assert Path(result).exists()
        with open(result) as f:
            data = json.load(f)

        assert data["metadata"]["vcf_file"] == "test.vcf"
        assert data["validation_metrics"]["accuracy"] == 0.875
        assert data["confusion_matrix"]["true_positives"] == 18
        assert "BRCA1" in data["per_gene_metrics"]

    def test_json_structure(self, tmp_path, sample_validation_report):
        """Test JSON report has correct structure."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.json"

        generator.generate_json(sample_validation_report, str(output_path))

        with open(output_path) as f:
            data = json.load(f)

        # Check top-level keys
        assert "metadata" in data
        assert "validation_metrics" in data
        assert "confusion_matrix" in data
        assert "evaluation_summary" in data
        assert "per_gene_metrics" in data
        assert "discordant_cases" in data

    def test_generate_csv(self, tmp_path, sample_classifications):
        """Test CSV report generation."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.csv"

        result = generator.generate_csv(sample_classifications, str(output_path))

        assert Path(result).exists()
        csv_content = Path(result).read_text()

        # Check headers
        assert "variant_id" in csv_content
        assert "prediction" in csv_content
        assert "confidence" in csv_content
        assert "is_clinical_grade" in csv_content

        # Check data rows
        assert "VAR1" in csv_content
        assert "pathogenic" in csv_content

    def test_csv_with_reasoning(self, tmp_path, sample_classifications):
        """Test CSV includes reasoning when requested."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.csv"

        result = generator.generate_csv(
            sample_classifications, str(output_path), include_reasoning=True
        )

        csv_content = Path(result).read_text()

        assert "reasoning" in csv_content
        assert "Frameshift mutation" in csv_content

    def test_generate_discordant_csv(self, tmp_path, sample_validation_report):
        """Test discordant cases CSV generation."""
        generator = ReportGenerator()
        output_path = tmp_path / "discordant.csv"

        result = generator.generate_discordant_csv(
            sample_validation_report, str(output_path)
        )

        assert Path(result).exists()
        csv_content = Path(result).read_text()

        assert "variant_id" in csv_content
        assert "predicted" in csv_content
        assert "expected" in csv_content
        assert "BRCA1:c.123A>G" in csv_content

    def test_confidence_distribution_chart(self, tmp_path, sample_classifications):
        """Test confidence distribution in HTML."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.html"

        # Add more classifications with varied confidence
        classifications = sample_classifications + [
            Classification(
                "VAR5", PredictionClass.PATHOGENIC, ConfidenceScore(0.30), "low"
            ),
            Classification(
                "VAR6", PredictionClass.PATHOGENIC, ConfidenceScore(0.92), "high"
            ),
        ]

        report = {"accuracy": 0.85, "total_evaluated": 6, "correct": 5, "incorrect": 1}
        result = generator.generate_html(report, str(output_path), classifications)

        html_content = Path(result).read_text()
        assert "Confidence Distribution" in html_content
        assert "0.85-1.0" in html_content  # Clinical grade bin

    def test_per_gene_performance_chart(self, tmp_path, sample_validation_report):
        """Test per-gene performance table in HTML."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.html"

        result = generator.generate_html(sample_validation_report, str(output_path))

        html_content = Path(result).read_text()
        assert "Per-Gene Performance" in html_content
        assert "BRCA1" in html_content
        assert "BRCA2" in html_content
        assert "TP53" in html_content

    def test_empty_discordant_cases(self, tmp_path):
        """Test HTML with no discordant cases."""
        generator = ReportGenerator()
        output_path = tmp_path / "report.html"

        report = {
            "accuracy": 1.0,
            "total_evaluated": 10,
            "correct": 10,
            "incorrect": 0,
            "discordant_cases": [],
        }

        result = generator.generate_html(report, str(output_path))
        html_content = Path(result).read_text()

        assert "No discordant cases found" in html_content

    def test_accuracy_color_coding(self, tmp_path):
        """Test accuracy color coding in HTML."""
        generator = ReportGenerator()

        # Test good accuracy (>= 0.85)
        assert generator._get_accuracy_class(0.90) == "good"

        # Test warning accuracy (0.70-0.85)
        assert generator._get_accuracy_class(0.75) == "warning"

        # Test danger accuracy (< 0.70)
        assert generator._get_accuracy_class(0.65) == "danger"

    def test_generate_all_reports(
        self, tmp_path, sample_validation_report, sample_classifications
    ):
        """Test generating all report formats at once."""
        output_dir = tmp_path / "reports"

        paths = generate_all_reports(
            sample_validation_report,
            sample_classifications,
            str(output_dir),
            "test_report",
        )

        assert "html" in paths
        assert "json" in paths
        assert "csv" in paths
        assert "discordant_csv" in paths

        # Verify all files exist
        assert Path(paths["html"]).exists()
        assert Path(paths["json"]).exists()
        assert Path(paths["csv"]).exists()
        assert Path(paths["discordant_csv"]).exists()

    def test_default_metadata(self):
        """Test default metadata generation."""
        generator = ReportGenerator()
        metadata = generator._default_metadata()

        assert "generated_at" in metadata
        assert "model_version" in metadata
        assert metadata["model_version"] == "MedGemma-4B-4bit"

    def test_report_metadata_serialization(self):
        """Test ReportMetadata can be serialized."""
        from dataclasses import asdict

        metadata = ReportMetadata(
            generated_at="2026-02-22T10:00:00",
            vcf_file="test.vcf",
            total_variants=100,
            confidence_threshold=0.85,
        )

        serialized = asdict(metadata)

        assert serialized["vcf_file"] == "test.vcf"
        assert serialized["total_variants"] == 100
        assert serialized["confidence_threshold"] == 0.85


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
