"""
Unit Tests for VCF Parser

Tests parsing, filtering, and variant classification functionality.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.vcf_parser import VCFParser, Variant, VariantType, parse_vcf


class TestVCFParser:
    """Test suite for VCF parsing functionality"""

    @pytest.fixture
    def sample_vcf_path(self):
        """Path to test VCF file"""
        return project_root / "data" / "test_samples" / "sample_001.vcf"

    def test_parser_initialization(self, sample_vcf_path):
        """Test parser can be initialized"""
        parser = VCFParser(str(sample_vcf_path))
        assert parser.vcf_path.exists()
        assert parser.min_quality == 0.0

    def test_file_not_found(self):
        """Test error handling for missing file"""
        with pytest.raises(FileNotFoundError):
            VCFParser("nonexistent.vcf")

    def test_parse_all_variants(self, sample_vcf_path):
        """Test parsing all variants without filters"""
        parser = VCFParser(str(sample_vcf_path))
        variants = parser.parse(pass_only=False)

        # Sample VCF has 5 variants
        assert len(variants) >= 4, f"Expected at least 4 variants, got {len(variants)}"

        # Check variants are Variant objects
        assert all(isinstance(v, Variant) for v in variants)

    def test_parse_pass_only(self, sample_vcf_path):
        """Test FILTER=PASS filtering"""
        parser = VCFParser(str(sample_vcf_path))
        variants = parser.parse(pass_only=True)

        # Only PASS variants
        assert all(v.filter_status == "PASS" for v in variants)
        assert len(variants) == 4  # 4 PASS variants in sample

    def test_gene_filtering(self, sample_vcf_path):
        """Test filtering by genes of interest"""
        parser = VCFParser(str(sample_vcf_path))
        variants = parser.parse(genes_of_interest=["BRCA1", "BRCA2"])

        # Only BRCA1/2 variants
        genes = [v.gene for v in variants]
        assert all(g in ["BRCA1", "BRCA2"] for g in genes)
        assert len(variants) == 2

    def test_quality_filtering(self, sample_vcf_path):
        """Test quality score filtering"""
        parser = VCFParser(str(sample_vcf_path), min_quality=90)
        variants = parser.parse(pass_only=False)

        # All variants should have QUAL >= 90
        assert all(v.quality_score >= 90 for v in variants if v.quality_score)

    def test_variant_fields(self, sample_vcf_path):
        """Test variant fields are correctly populated"""
        parser = VCFParser(str(sample_vcf_path))
        variants = parser.parse()

        # Check first variant (BRCA1 frameshift)
        brca1 = [v for v in variants if v.gene == "BRCA1"][0]
        assert brca1.chromosome == "chr17"
        assert brca1.position == 41196372
        assert brca1.ref_allele == "G"
        assert brca1.alt_allele == "A"
        assert brca1.variant_type == VariantType.FRAMESHIFT
        assert brca1.quality_score == 100.0

    def test_variant_type_classification(self, sample_vcf_path):
        """Test variant type classification"""
        parser = VCFParser(str(sample_vcf_path))
        variants = parser.parse()

        # Map genes to expected types
        expected_types = {
            "BRCA1": VariantType.FRAMESHIFT,
            "BRCA2": VariantType.MISSENSE,
            "EGFR": VariantType.MISSENSE,
            "TP53": VariantType.MISSENSE,
        }

        for variant in variants:
            if variant.gene in expected_types:
                assert variant.variant_type == expected_types[variant.gene], (
                    f"{variant.gene} type mismatch: got {variant.variant_type}, expected {expected_types[variant.gene]}"
                )

    def test_hgvs_extraction(self, sample_vcf_path):
        """Test HGVS nomenclature extraction"""
        parser = VCFParser(str(sample_vcf_path))
        variants = parser.parse()

        # All variants should have HGVS notation
        assert all(v.hgvs_nomenclature for v in variants)

        # Check specific HGVS formats
        brca1 = [v for v in variants if v.gene == "BRCA1"][0]
        assert "BRCA1" in brca1.hgvs_nomenclature or "c." in brca1.hgvs_nomenclature

    def test_population_frequency(self, sample_vcf_path):
        """Test allele frequency extraction"""
        parser = VCFParser(str(sample_vcf_path))
        variants = parser.parse()

        # Check frequencies are within valid range
        for variant in variants:
            if variant.population_frequency:
                assert 0 <= variant.population_frequency <= 1.0

    def test_max_variants_limit(self, sample_vcf_path):
        """Test max_variants parameter"""
        parser = VCFParser(str(sample_vcf_path), max_variants=2)
        variants = parser.parse(pass_only=False)

        assert len(variants) == 2

    def test_convenience_function(self, sample_vcf_path):
        """Test parse_vcf convenience function"""
        variants = parse_vcf(str(sample_vcf_path), genes=["BRCA1"])

        assert len(variants) == 1
        assert variants[0].gene == "BRCA1"

    def test_get_statistics(self, sample_vcf_path):
        """Test statistics generation"""
        parser = VCFParser(str(sample_vcf_path))
        stats = parser.get_statistics()

        assert "total_variants" in stats
        assert "unique_genes" in stats
        assert "gene_distribution" in stats
        assert "type_distribution" in stats
        assert stats["total_variants"] >= 4

    def test_variant_string_representation(self, sample_vcf_path):
        """Test variant __str__ method"""
        variants = parse_vcf(str(sample_vcf_path))
        variant_str = str(variants[0])

        assert variants[0].chromosome in variant_str
        assert str(variants[0].position) in variant_str
        assert variants[0].gene in variant_str


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_vcf(self, tmp_path):
        """Test handling of empty VCF file"""
        vcf_file = tmp_path / "empty.vcf"
        vcf_file.write_text(
            "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        )

        parser = VCFParser(str(vcf_file))
        variants = parser.parse()

        assert len(variants) == 0

    def test_malformed_line(self, tmp_path):
        """Test handling of malformed VCF line"""
        vcf_file = tmp_path / "malformed.vcf"
        content = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr1\t1000\t.\tA\tT\t50\tPASS\tGENE=TEST
chr2\tinvalid\t.\tG\tC\t60\tPASS\tGENE=TEST2
chr3\t3000\t.\tC\tG\t70\tPASS\tGENE=TEST3
"""
        vcf_file.write_text(content)

        parser = VCFParser(str(vcf_file))
        variants = parser.parse()

        # Should skip malformed line, parse valid ones
        assert len(variants) >= 1


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
