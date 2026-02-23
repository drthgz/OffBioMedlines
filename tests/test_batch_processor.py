"""Unit tests for batch processing module."""

import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.model.batch_processor import (
    BatchProcessor,
    BatchResult,
    ProcessingSummary,
    batch_process_vcf,
)
from src.model.confidence import (
    Classification,
    ConfidenceScore,
    PredictionClass,
)
from src.data.vcf_parser import Variant, VariantType


@pytest.fixture
def mock_inference():
    """Create mock inference function."""

    def inference_fn(variant: Variant) -> str:
        """Mock inference that returns canned response."""
        if "BRCA" in variant.gene:
            return "Classification: pathogenic (confidence: 0.95)"
        return "Classification: benign (confidence: 0.87)"

    return inference_fn


@pytest.fixture
def sample_variants():
    """Create sample variants for testing."""
    return [
        Variant("chr17", 43000000, "A", "G", "BRCA1", VariantType.MISSENSE, "c.123A>G"),
        Variant("chr17", 43000100, "T", "C", "BRCA1", VariantType.MISSENSE, "c.456T>C"),
        Variant("chr13", 32000000, "G", "A", "BRCA2", VariantType.MISSENSE, "c.789G>A"),
        Variant("chr1", 10000000, "C", "T", "TP53", VariantType.MISSENSE, "c.999C>T"),
        Variant("chr7", 55000000, "A", "T", "EGFR", VariantType.MISSENSE, "c.111A>T"),
    ]


class TestBatchProcessor:
    """Test batch processing functionality."""

    def test_initialization(self, mock_inference):
        """Test processor initialization."""
        processor = BatchProcessor(
            inference_function=mock_inference, batch_size=5, timeout_per_variant=10.0
        )

        assert processor.batch_size == 5
        assert processor.timeout_per_variant == 10.0
        assert processor.total_processed == 0
        assert processor.total_errors == 0

    def test_single_variant_processing(self, mock_inference, sample_variants):
        """Test processing a single variant."""
        processor = BatchProcessor(mock_inference)

        classification = processor._process_single_variant(sample_variants[0])

        assert isinstance(classification, Classification)
        assert classification.variant_id == "c.123A>G"
        assert classification.prediction == PredictionClass.PATHOGENIC

    def test_batch_processing(self, mock_inference, sample_variants):
        """Test processing multiple batches."""
        processor = BatchProcessor(mock_inference, batch_size=2)

        batches = list(processor._process_batches(sample_variants))

        # 5 variants with batch_size=2 → 3 batches
        assert len(batches) == 3
        assert batches[0].variants_processed == 2
        assert batches[1].variants_processed == 2
        assert batches[2].variants_processed == 1

    def test_batch_result_structure(self, mock_inference, sample_variants):
        """Test batch result contains expected data."""
        processor = BatchProcessor(mock_inference, batch_size=3)

        batches = list(processor._process_batches(sample_variants[:3]))
        batch_result = batches[0]

        assert isinstance(batch_result, BatchResult)
        assert batch_result.batch_id == 0  # batch_id starts at 0
        assert batch_result.variants_processed == 3
        assert len(batch_result.classifications) == 3
        assert batch_result.processing_time >= 0
        assert batch_result.errors == 0

    def test_processing_statistics(self, mock_inference, sample_variants):
        """Test statistics tracking."""
        processor = BatchProcessor(mock_inference, batch_size=2)

        # Process all batches
        list(processor._process_batches(sample_variants))

        summary = processor.get_summary()

        assert isinstance(summary, ProcessingSummary)
        assert summary.total_variants == 5
        assert summary.successful == 5
        assert summary.failed == 0
        assert summary.batches_processed == 3
        assert summary.avg_time_per_variant >= 0

    def test_error_handling(self, sample_variants):
        """Test error handling during processing."""

        def failing_inference(variant: Variant) -> str:
            """Inference function that fails."""
            raise RuntimeError("Model inference failed")

        processor = BatchProcessor(failing_inference, batch_size=10)

        batches = list(processor._process_batches(sample_variants))
        batch_result = batches[0]

        assert batch_result.errors == len(sample_variants)
        assert len(batch_result.classifications) == 0  # No successful classifications

    def test_timeout_handling(self, sample_variants):
        """Test timeout enforcement."""

        def slow_inference(variant: Variant) -> str:
            """Slow inference function."""
            time.sleep(0.2)  # Simulate slow processing
            return "Classification: pathogenic (confidence: 0.90)"

        processor = BatchProcessor(slow_inference, timeout_per_variant=0.1)

        # TimeoutError is wrapped in RuntimeError
        with pytest.raises(RuntimeError, match="timeout"):
            processor._process_single_variant(sample_variants[0])

    def test_vcf_processing_integration(self, mock_inference, tmp_path):
        """Test end-to-end VCF processing."""
        # Create test VCF
        vcf_path = tmp_path / "test.vcf"
        vcf_content = """##fileformat=VCFv4.2
##contig=<ID=chr17>
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT
chr17\t43000000\t.\tA\tG\t100\tPASS\tGENE=BRCA1;HGVS=c.123A>G\t.
chr17\t43000100\t.\tT\tC\t100\tPASS\tGENE=BRCA1;HGVS=c.456T>C\t.
"""
        with open(vcf_path, "w") as f:
            f.write(vcf_content)

        processor = BatchProcessor(mock_inference, batch_size=10)
        classifications = processor.process_vcf(str(vcf_path))

        assert len(classifications) == 2
        assert all(isinstance(c, Classification) for c in classifications)

    def test_gene_filtering(self, mock_inference, tmp_path):
        """Test VCF processing with gene filtering."""
        vcf_path = tmp_path / "test.vcf"
        vcf_content = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT
chr17\t43000000\t.\tA\tG\t100\tPASS\tGENE=BRCA1;HGVS=c.123A>G\t.
chr1\t10000000\t.\tC\tT\t100\tPASS\tGENE=TP53;HGVS=c.999C>T\t.
"""
        with open(vcf_path, "w") as f:
            f.write(vcf_content)

        processor = BatchProcessor(mock_inference)
        classifications = processor.process_vcf(
            str(vcf_path), genes_of_interest=["BRCA1"]
        )

        # Only BRCA1 variant should be processed
        assert len(classifications) == 1

    def test_reset_statistics(self, mock_inference, sample_variants):
        """Test statistics reset."""
        processor = BatchProcessor(mock_inference)

        list(processor._process_batches(sample_variants))
        assert processor.total_processed > 0

        processor.reset_stats()

        assert processor.total_processed == 0
        assert processor.total_errors == 0
        assert processor.elapsed_time == 0.0

    def test_time_estimation_no_history(self, mock_inference):
        """Test time estimation with no processing history."""
        processor = BatchProcessor(mock_inference)

        estimated = processor.estimate_time(100)

        # Should use default 3s per variant
        assert estimated == pytest.approx(300.0, abs=1.0)

    def test_time_estimation_with_history(self, mock_inference, sample_variants):
        """Test time estimation based on processing history."""
        processor = BatchProcessor(mock_inference)

        # Process some variants to establish baseline
        list(processor._process_batches(sample_variants))
        summary = processor.get_summary()

        estimated = processor.estimate_time(100)

        # Should use actual average time
        expected = summary.avg_time_per_variant * 100
        assert estimated == pytest.approx(expected, rel=0.1)

    def test_progress_logging(self, mock_inference, sample_variants, caplog):
        """Test progress logging during processing."""
        processor = BatchProcessor(mock_inference, batch_size=2)

        with caplog.at_level("INFO"):
            list(processor._process_batches(sample_variants))

        # Check for progress messages (log says "Batch X/Y complete")
        assert any("Batch" in record.message for record in caplog.records)
        assert any("100.0%" in record.message for record in caplog.records)

    def test_batch_process_vcf_convenience(self, mock_inference, tmp_path):
        """Test convenience function for batch processing."""
        vcf_path = tmp_path / "test.vcf"
        vcf_content = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT
chr17\t43000000\t.\tA\tG\t100\tPASS\tGENE=BRCA1;HGVS=c.123A>G\t.
"""
        with open(vcf_path, "w") as f:
            f.write(vcf_content)

        classifications = batch_process_vcf(
            str(vcf_path), mock_inference, batch_size=10
        )

        assert len(classifications) == 1
        assert isinstance(classifications[0], Classification)

    def test_max_variants_limit(self, mock_inference, tmp_path):
        """Test max_variants parameter."""
        vcf_path = tmp_path / "test.vcf"
        vcf_content = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT
chr17\t43000000\t.\tA\tG\t100\tPASS\tGENE=BRCA1;HGVS=c.123A>G\t.
chr17\t43000100\t.\tT\tC\t100\tPASS\tGENE=BRCA1;HGVS=c.456T>C\t.
chr17\t43000200\t.\tG\tA\t100\tPASS\tGENE=BRCA1;HGVS=c.789G>A\t.
"""
        with open(vcf_path, "w") as f:
            f.write(vcf_content)

        processor = BatchProcessor(mock_inference)
        classifications = processor.process_vcf(str(vcf_path), max_variants=2)

        # Should stop after 2 variants
        assert len(classifications) == 2


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
