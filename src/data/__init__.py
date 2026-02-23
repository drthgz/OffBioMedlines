"""Data module for VCF parsing and variant processing."""

from src.data.vcf_parser import Variant, VCFParser, VariantType, parse_vcf

__all__ = ["VCFParser", "Variant", "VariantType", "parse_vcf"]
