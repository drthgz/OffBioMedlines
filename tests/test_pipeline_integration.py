"""End-to-end integration test for Phase 2 pipeline.

Tests the complete workflow:
1. Parse VCF file
2. Batch process variants through mock inference
3. Validate against gold standard
4. Generate reports
"""

import json
import pytest
from pathlib import Path

from src.data import VCFParser, Variant
from src.model import (
    BatchProcessor,
    ClinicalValidator,
    ReportGenerator,
    generate_all_reports,
)


@pytest.fixture
def test_vcf(tmp_path):
    """Create test VCF file with gold standard variants."""
    vcf_content = """##fileformat=VCFv4.2
##contig=<ID=chr17>
##contig=<ID=chr13>
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT
chr17\t43000000\t.\tA\tG\t100\tPASS\tGENE=BRCA1;HGVS=BRCA1:c.68_69delAG\t.
chr17\t43000100\t.\tT\tC\t100\tPASS\tGENE=BRCA1;HGVS=BRCA1:c.181T>G\t.
chr13\t32000000\t.\tG\tA\t100\tPASS\tGENE=BRCA2;HGVS=BRCA2:c.1687C>T\t.
chr17\t7000000\t.\tG\tA\t100\tPASS\tGENE=TP53;HGVS=TP53:c.733G>A\t.
"""
    vcf_path = tmp_path / "test.vcf"
    vcf_path.write_text(vcf_content)
    return str(vcf_path)


@pytest.fixture
def test_gold_standard(tmp_path):
    """Create test gold standard file."""
    gold_standard = {
        "metadata": {
            "source": "ClinVar",
            "version": "2026-02-22",
            "total_variants": 4,
        },
        "variants": [
            {
                "variant_id": "BRCA1:c.68_69delAG",
                "gene": "BRCA1",
                "known_classification": "pathogenic",
                "clinvar_id": "RCV000000051",
            },
            {
                "variant_id": "BRCA1:c.181T>G",
                "gene": "BRCA1",
                "known_classification": "pathogenic",
                "clinvar_id": "RCV000000053",
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
        ],
    }

    gold_path = tmp_path / "gold_standard.json"
    with open(gold_path, "w") as f:
        json.dump(gold_standard, f)
    return str(gold_path)


@pytest.fixture
def mock_inference_high_accuracy():
    """Mock inference function with high accuracy (matches gold standard)."""

    def inference(variant: Variant) -> str:
        """Return classification matching gold standard."""
        hgvs = variant.hgvs_nomenclature

        # Match gold standard classifications
        if "BRCA1:c.68_69delAG" in hgvs:
            return "Classification: pathogenic (confidence: 0.95). This is a frameshift deletion."
        elif "BRCA1:c.181T>G" in hgvs:
            return "Classification: pathogenic (confidence: 0.92). Known pathogenic variant."
        elif "BRCA2:c.1687C>T" in hgvs:
            return "Classification: likely pathogenic (confidence: 0.88). Missense in critical domain."
        elif "TP53:c.733G>A" in hgvs:
            return "Classification: pathogenic (confidence: 0.97). Well-characterized mutation."
        else:
            return (
                "Classification: uncertain (confidence: 0.50). Insufficient evidence."
            )

    return inference


class TestEndToEndPipeline:
    """Test complete Phase 2 pipeline integration."""

    def test_complete_pipeline_flow(
        self, test_vcf, test_gold_standard, mock_inference_high_accuracy, tmp_path
    ):
        """Test end-to-end: VCF → Batch → Validate → Report."""

        # Step 1: Parse VCF
        parser = VCFParser(test_vcf)
        variants = parser.parse()
        assert len(variants) == 4

        # Step 2: Batch process through inference
        processor = BatchProcessor(mock_inference_high_accuracy, batch_size=2)
        classifications = processor.process_vcf(test_vcf)
        assert len(classifications) == 4

        # Step 3: Validate against gold standard
        validator = ClinicalValidator(test_gold_standard)
        report = validator.validate_batch(classifications)

        # Step 4: Generate reports
        report_dir = tmp_path / "reports"
        paths = generate_all_reports(
            report, classifications, str(report_dir), "pipeline_test"
        )

        # Verify all reports exist
        assert Path(paths["html"]).exists()
        assert Path(paths["json"]).exists()
        assert Path(paths["csv"]).exists()
        assert Path(paths["discordant_csv"]).exists()

        # Verify accuracy meets threshold
        assert report["accuracy"] >= 0.85, (
            f"Accuracy {report['accuracy']:.2f} below 0.85 threshold"
        )

    def test_pipeline_with_perfect_accuracy(
        self, test_vcf, test_gold_standard, mock_inference_high_accuracy
    ):
        """Test pipeline achieves 100% accuracy with perfect inference."""

        # Process
        processor = BatchProcessor(mock_inference_high_accuracy, batch_size=10)
        classifications = processor.process_vcf(test_vcf)

        # Validate
        validator = ClinicalValidator(test_gold_standard)
        report = validator.validate_batch(classifications)

        # Check metrics
        assert report["accuracy"] == 1.0
        assert report["f1_score"] == 1.0
        assert len(report["discordant_cases"]) == 0

    def test_pipeline_metrics_calculation(
        self, test_vcf, test_gold_standard, mock_inference_high_accuracy
    ):
        """Test comprehensive metrics are calculated."""

        processor = BatchProcessor(mock_inference_high_accuracy)
        classifications = processor.process_vcf(test_vcf)

        validator = ClinicalValidator(test_gold_standard)
        report = validator.validate_batch(classifications)

        # Verify all metrics present
        required_metrics = [
            "accuracy",
            "sensitivity",
            "specificity",
            "precision",
            "f1_score",
            "true_positives",
            "true_negatives",
            "false_positives",
            "false_negatives",
            "per_gene_metrics",
        ]

        for metric in required_metrics:
            assert metric in report, f"Missing metric: {metric}"

    def test_pipeline_per_gene_breakdown(
        self, test_vcf, test_gold_standard, mock_inference_high_accuracy
    ):
        """Test per-gene metrics are calculated correctly."""

        processor = BatchProcessor(mock_inference_high_accuracy)
        classifications = processor.process_vcf(test_vcf)

        validator = ClinicalValidator(test_gold_standard)
        report = validator.validate_batch(classifications)

        per_gene = report["per_gene_metrics"]

        # Verify genes present
        assert "BRCA1" in per_gene
        assert "BRCA2" in per_gene
        assert "TP53" in per_gene

        # Verify BRCA1 metrics (2 variants, both correct)
        assert per_gene["BRCA1"]["total"] == 2
        assert per_gene["BRCA1"]["accuracy"] == 1.0

    def test_pipeline_html_report_content(
        self, test_vcf, test_gold_standard, mock_inference_high_accuracy, tmp_path
    ):
        """Test HTML report contains all key information."""

        processor = BatchProcessor(mock_inference_high_accuracy)
        classifications = processor.process_vcf(test_vcf)

        validator = ClinicalValidator(test_gold_standard)
        report = validator.validate_batch(classifications)

        generator = ReportGenerator()
        html_path = generator.generate_html(
            report, str(tmp_path / "report.html"), classifications
        )

        html_content = Path(html_path).read_text()

        # Check key sections
        assert "Clinical Validation Report" in html_content
        assert "Accuracy" in html_content
        assert "Per-Gene Performance" in html_content
        assert "BRCA1" in html_content
        assert "BRCA2" in html_content
        assert "TP53" in html_content

    def test_pipeline_json_report_structure(
        self, test_vcf, test_gold_standard, mock_inference_high_accuracy, tmp_path
    ):
        """Test JSON report is properly structured."""

        processor = BatchProcessor(mock_inference_high_accuracy)
        classifications = processor.process_vcf(test_vcf)

        validator = ClinicalValidator(test_gold_standard)
        report = validator.validate_batch(classifications)

        generator = ReportGenerator()
        json_path = generator.generate_json(report, str(tmp_path / "report.json"))

        with open(json_path) as f:
            data = json.load(f)

        # Verify structure
        assert "metadata" in data
        assert "validation_metrics" in data
        assert "per_gene_metrics" in data
        assert data["validation_metrics"]["accuracy"] == 1.0

    def test_pipeline_with_low_confidence_filtering(
        self, test_vcf, test_gold_standard, tmp_path
    ):
        """Test pipeline respects confidence thresholds."""

        # Mock inference with low confidence
        def low_confidence_inference(variant: Variant) -> str:
            return "Classification: pathogenic (confidence: 0.60). Low confidence prediction."

        processor = BatchProcessor(low_confidence_inference)
        classifications = processor.process_vcf(test_vcf)

        validator = ClinicalValidator(test_gold_standard)

        # With high threshold, should evaluate 0 variants
        report = validator.validate_batch(classifications, min_confidence=0.85)
        assert report["total_evaluated"] == 0

        # With low threshold, should evaluate all
        report = validator.validate_batch(classifications, min_confidence=0.50)
        assert report["total_evaluated"] == 4

    def test_pipeline_processing_speed(
        self, test_vcf, test_gold_standard, mock_inference_high_accuracy
    ):
        """Test pipeline meets performance requirements."""

        processor = BatchProcessor(mock_inference_high_accuracy, batch_size=10)

        # Process and time it
        import time

        start = time.time()
        classifications = processor.process_vcf(test_vcf)
        elapsed = time.time() - start

        # Should be very fast for 4 variants
        assert elapsed < 1.0, f"Processing took {elapsed:.2f}s (too slow)"

        # Check summary
        summary = processor.get_summary()
        assert summary.successful == 4
        assert summary.failed == 0

    def test_pipeline_error_handling(self, test_vcf, test_gold_standard, tmp_path):
        """Test pipeline handles inference errors gracefully."""

        error_count = {"count": 0}

        def failing_inference(variant: Variant) -> str:
            """Fail on first variant, succeed on others."""
            error_count["count"] += 1
            if error_count["count"] == 1:
                raise RuntimeError("Simulated inference failure")
            return "Classification: pathogenic (confidence: 0.90)."

        processor = BatchProcessor(failing_inference)
        classifications = processor.process_vcf(test_vcf)

        # Should have 3 successful (1 failed)
        assert len(classifications) == 3

        summary = processor.get_summary()
        assert summary.successful == 3
        assert summary.failed == 1


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
