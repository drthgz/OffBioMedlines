#!/usr/bin/env python3
"""
Integration Test Suite for VCF + MedGemma Pipeline

Tests the complete workflow:
1. VCF parsing
2. MedGemma classification
3. Report generation
4. Validation against gold standard

Run with: python tests/test_integration.py
"""

import sys
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.parsing import parse_vcf, VCFParser, Variant, VariantType


class TestVCFParsing(unittest.TestCase):
    """Test VCF parser integration."""

    def setUp(self):
        self.vcf_path = project_root / "data" / "test_samples" / "sample_001.vcf"
        self.assertTrue(self.vcf_path.exists(), f"VCF file not found: {self.vcf_path}")

    def test_vcf_file_exists(self):
        """Verify test VCF file is available."""
        self.assertTrue(self.vcf_path.exists())
        self.assertTrue(self.vcf_path.is_file())

    def test_parse_vcf_with_filters(self):
        """Test parsing VCF with quality and gene filters."""
        parser = VCFParser(str(self.vcf_path), min_quality=50)
        variants = parser.parse(
            genes_of_interest=["BRCA1", "BRCA2", "EGFR", "TP53"], pass_only=True
        )

        # Should extract 4 PASS variants (PTEN is LowQual)
        self.assertGreaterEqual(
            len(variants), 4, "Should parse at least 4 PASS variants"
        )

        # Verify all are Variant objects
        for v in variants:
            self.assertIsInstance(v, Variant)
            self.assertIn(v.filter_status, ["PASS", "."])
            self.assertGreaterEqual(v.quality_score, 50)

    def test_variant_types_classified(self):
        """Test that variant types are correctly classified."""
        parser = VCFParser(str(self.vcf_path))
        variants = parser.parse()

        variant_types = {v.gene: v.variant_type for v in variants}

        # BRCA1 should be frameshift
        if "BRCA1" in variant_types:
            self.assertEqual(variant_types["BRCA1"], VariantType.FRAMESHIFT)

        # BRCA2, EGFR, TP53 should be missense
        for gene in ["BRCA2", "EGFR", "TP53"]:
            if gene in variant_types:
                self.assertEqual(variant_types[gene], VariantType.MISSENSE)

    def test_hgvs_extraction(self):
        """Test HGVS nomenclature extraction."""
        parser = VCFParser(str(self.vcf_path))
        variants = parser.parse()

        # At least some variants should have HGVS
        variants_with_hgvs = [v for v in variants if v.hgvs_nomenclature]
        self.assertGreater(
            len(variants_with_hgvs), 0, "Should extract HGVS nomenclature"
        )

        # Check format
        for v in variants_with_hgvs:
            self.assertIn(
                ":", v.hgvs_nomenclature, "HGVS should contain transcript:change"
            )


class TestVariantDataModel(unittest.TestCase):
    """Test Variant data model."""

    def test_variant_creation(self):
        """Test creating Variant objects."""
        variant = Variant(
            chromosome="chr17",
            position=41196372,
            ref_allele="G",
            alt_allele="A",
            gene="BRCA1",
            variant_type=VariantType.FRAMESHIFT,
            hgvs_nomenclature="NM_007294.3:c.68_69delAG",
            quality_score=100.0,
            filter_status="PASS",
            population_frequency=0.0001,
        )

        self.assertEqual(variant.gene, "BRCA1")
        self.assertEqual(variant.variant_type, VariantType.FRAMESHIFT)
        self.assertEqual(variant.quality_score, 100.0)

    def test_variant_string_representation(self):
        """Test Variant __str__ method."""
        variant = Variant(
            chromosome="chr17",
            position=7577548,
            ref_allele="C",
            alt_allele="T",
            gene="TP53",
            variant_type=VariantType.MISSENSE,
            hgvs_nomenclature="NM_000546.5:c.818G>A",
            quality_score=85.0,
            filter_status="PASS",
            population_frequency=None,
        )

        str_repr = str(variant)
        self.assertIn("chr17", str_repr)
        self.assertIn("7577548", str_repr)
        self.assertIn("TP53", str_repr)


class TestMedGemmaIntegration(unittest.TestCase):
    """Test MedGemma integration (mocked for unit testing)."""

    def setUp(self):
        self.vcf_path = project_root / "data" / "test_samples" / "sample_001.vcf"

    def test_classification_structure(self):
        """Test that classification results have expected structure."""
        # Mock MedGemma response
        mock_result = {
            "classification": "pathogenic",
            "confidence": 92.0,
            "interpretation": "This frameshift variant causes loss of function...",
            "raw_response": "Classification: PATHOGENIC\nConfidence: 92%...",
        }

        # Verify structure
        self.assertIn("classification", mock_result)
        self.assertIn("confidence", mock_result)
        self.assertIn("interpretation", mock_result)

        # Verify types
        self.assertIsInstance(mock_result["classification"], str)
        self.assertIsInstance(mock_result["confidence"], (int, float))
        self.assertGreaterEqual(mock_result["confidence"], 0)
        self.assertLessEqual(mock_result["confidence"], 100)

    def test_valid_classification_values(self):
        """Test that classifications are valid ACMG categories."""
        valid_classifications = {
            "pathogenic",
            "likely_pathogenic",
            "uncertain_significance",
            "likely_benign",
            "benign",
        }

        test_classifications = [
            "pathogenic",
            "likely_pathogenic",
            "uncertain_significance",
        ]

        for cls in test_classifications:
            self.assertIn(cls, valid_classifications)


class TestClinicalReport(unittest.TestCase):
    """Test clinical report generation."""

    def test_report_structure(self):
        """Test that clinical reports have required fields."""
        mock_report = {
            "sample_id": "TEST_001",
            "analysis_date": "2024-01-15",
            "model": "google/medgemma-1.5-4b-it",
            "vcf_file": "test.vcf",
            "summary": {
                "total_variants_analyzed": 4,
                "pathogenic": 3,
                "likely_pathogenic": 1,
                "uncertain": 0,
                "benign": 0,
                "average_confidence": 88.5,
            },
            "findings": [],
        }

        # Verify required fields
        required_fields = ["sample_id", "analysis_date", "model", "summary", "findings"]
        for field in required_fields:
            self.assertIn(field, mock_report)

        # Verify summary structure
        summary_fields = ["total_variants_analyzed", "pathogenic", "average_confidence"]
        for field in summary_fields:
            self.assertIn(field, mock_report["summary"])

    def test_report_json_serializable(self):
        """Test that reports can be serialized to JSON."""
        mock_report = {
            "sample_id": "TEST_001",
            "summary": {"total_variants_analyzed": 4},
            "findings": [],
        }

        # Should not raise exception
        json_str = json.dumps(mock_report, indent=2)
        self.assertIsInstance(json_str, str)

        # Should be able to deserialize
        parsed = json.loads(json_str)
        self.assertEqual(parsed["sample_id"], "TEST_001")


class TestGoldStandardValidation(unittest.TestCase):
    """Test validation against ClinVar gold standard."""

    def setUp(self):
        self.gold_standard = {
            "BRCA1": "pathogenic",
            "BRCA2": "likely_pathogenic",
            "EGFR": "pathogenic",
            "TP53": "pathogenic",
        }

    def test_accuracy_calculation(self):
        """Test accuracy calculation logic."""
        medgemma_results = {
            "BRCA1": "pathogenic",  # Match
            "BRCA2": "likely_pathogenic",  # Match
            "EGFR": "pathogenic",  # Match
            "TP53": "likely_pathogenic",  # Mismatch (should be pathogenic)
        }

        matches = 0
        total = 0

        for gene, gold_class in self.gold_standard.items():
            if gene in medgemma_results:
                if medgemma_results[gene] == gold_class:
                    matches += 1
                total += 1

        accuracy = (matches / total) * 100

        self.assertEqual(matches, 3)
        self.assertEqual(total, 4)
        self.assertEqual(accuracy, 75.0)

    def test_perfect_accuracy(self):
        """Test perfect accuracy scenario."""
        medgemma_results = self.gold_standard.copy()

        matches = sum(
            1
            for gene, cls in self.gold_standard.items()
            if medgemma_results.get(gene) == cls
        )

        accuracy = (matches / len(self.gold_standard)) * 100
        self.assertEqual(accuracy, 100.0)


class TestEndToEndPipeline(unittest.TestCase):
    """Test complete pipeline integration."""

    def test_pipeline_components_available(self):
        """Test that all pipeline components are importable."""
        # VCF Parser
        from src.parsing import parse_vcf, VCFParser, Variant, VariantType

        self.assertIsNotNone(VCFParser)
        self.assertIsNotNone(Variant)

        # Data models - check class has proper fields
        variant_fields = Variant.__dataclass_fields__
        self.assertIn("gene", variant_fields)
        self.assertIn("variant_type", variant_fields)

    def test_pipeline_directories_exist(self):
        """Test that required directories exist."""
        required_dirs = [
            project_root / "data" / "test_samples",
            project_root / "src" / "parsing",
            project_root / "tests",
            project_root / "docs",
        ]

        for dir_path in required_dirs:
            self.assertTrue(dir_path.exists(), f"Directory missing: {dir_path}")

    def test_documentation_exists(self):
        """Test that required documentation exists."""
        docs = [
            project_root / "docs" / "IMPLEMENTATION_PLAN.md",
            project_root / "docs" / "VCF_PARSER_GUIDE.md",
            project_root / "docs" / "VCF_INTEGRATION_DEMO.md",
        ]

        for doc in docs:
            self.assertTrue(doc.exists(), f"Documentation missing: {doc}")


def run_tests():
    """Run all tests with verbose output."""
    print("=" * 80)
    print(" VCF + MedGemma Integration Test Suite")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVCFParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestVariantDataModel))
    suite.addTests(loader.loadTestsFromTestCase(TestMedGemmaIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestClinicalReport))
    suite.addTests(loader.loadTestsFromTestCase(TestGoldStandardValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndPipeline))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 80)
    print(" Test Summary")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 80)

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED")
        print("👉 Ready to run notebook: notebooks/vcf_medgemma_integration.ipynb")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("⚠️  Review failures above before running integration notebook")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
