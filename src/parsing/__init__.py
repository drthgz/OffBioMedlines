"""
Parsing Module

VCF, BAM, and genomic file parsing utilities
"""

from .vcf_parser import VCFParser, Variant, VariantType, parse_vcf

__all__ = ["VCFParser", "Variant", "VariantType", "parse_vcf"]
