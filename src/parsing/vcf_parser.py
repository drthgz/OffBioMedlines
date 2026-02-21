"""
VCF Parser Module

Parses Variant Call Format (VCF) files into structured Variant objects
for downstream MedGemma analysis.

Supports:
- VCF 4.2+ specification
- Compressed (.vcf.gz) and uncompressed files
- Gene filtering
- Quality score thresholds
- INFO field annotation extraction
"""

import re
import gzip
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VariantType(str, Enum):
    """Variant consequence types"""

    MISSENSE = "missense"
    FRAMESHIFT = "frameshift"
    SPLICE_SITE = "splice_site"
    STOP_GAINED = "stop_gained"
    STOP_LOST = "stop_lost"
    INFRAME_INDEL = "inframe_indel"
    SYNONYMOUS = "synonymous"
    INTERGENIC = "intergenic"
    UNKNOWN = "unknown"


@dataclass
class Variant:
    """Represents a genomic variant"""

    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    gene: str
    variant_type: VariantType
    hgvs_nomenclature: str
    quality_score: Optional[float] = None
    population_frequency: Optional[float] = None
    annotation: Optional[str] = None
    filter_status: Optional[str] = None

    def __str__(self):
        return f"{self.chromosome}:{self.position} {self.ref_allele}→{self.alt_allele} ({self.gene})"


class VCFParser:
    """
    Parse VCF files into Variant objects

    Example:
        parser = VCFParser("sample.vcf", min_quality=20)
        variants = parser.parse(genes_of_interest=['BRCA1', 'BRCA2'])

    Attributes:
        vcf_path: Path to VCF file
        min_quality: Minimum QUAL score threshold
        max_variants: Maximum variants to parse (None = unlimited)
    """

    def __init__(
        self,
        vcf_path: str,
        min_quality: float = 0.0,
        max_variants: Optional[int] = None,
    ):
        self.vcf_path = Path(vcf_path)
        self.min_quality = min_quality
        self.max_variants = max_variants

        # Validate file exists
        if not self.vcf_path.exists():
            raise FileNotFoundError(f"VCF file not found: {vcf_path}")

        logger.info(f"Initialized VCF parser for: {self.vcf_path.name}")

    def parse(
        self, genes_of_interest: Optional[List[str]] = None, pass_only: bool = True
    ) -> List[Variant]:
        """
        Parse VCF file and return list of Variant objects

        Args:
            genes_of_interest: Filter to specific genes (None = all genes)
            pass_only: Only include variants with FILTER=PASS

        Returns:
            List of Variant objects
        """
        variants = []

        logger.info(f"Parsing VCF file: {self.vcf_path.name}")
        if genes_of_interest:
            logger.info(f"  Filtering to genes: {', '.join(genes_of_interest)}")

        for variant in self._parse_vcf_lines():
            # Apply filters
            if pass_only and variant.filter_status != "PASS":
                continue

            if genes_of_interest and variant.gene not in genes_of_interest:
                continue

            if variant.quality_score and variant.quality_score < self.min_quality:
                continue

            variants.append(variant)

            # Check max limit
            if self.max_variants and len(variants) >= self.max_variants:
                logger.info(f"Reached max_variants limit: {self.max_variants}")
                break

        logger.info(f"✓ Parsed {len(variants)} variants")
        return variants

    def _parse_vcf_lines(self) -> Iterator[Variant]:
        """Generator that yields Variant objects from VCF lines"""

        # Open file (handle .gz compression)
        if str(self.vcf_path).endswith(".gz"):
            file_handle = gzip.open(self.vcf_path, "rt")
        else:
            file_handle = open(self.vcf_path, "r")

        try:
            for line_num, line in enumerate(file_handle, 1):
                line = line.strip()

                # Skip header lines
                if line.startswith("#"):
                    continue

                # Skip empty lines
                if not line:
                    continue

                # Parse variant line
                try:
                    variant = self._parse_variant_line(line)
                    if variant:
                        yield variant
                except Exception as e:
                    logger.warning(f"Error parsing line {line_num}: {e}")
                    continue

        finally:
            file_handle.close()

    def _parse_variant_line(self, line: str) -> Optional[Variant]:
        """
        Parse a single VCF variant line

        VCF Format:
        CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO  FORMAT  SAMPLE...
        """
        fields = line.split("\t")

        if len(fields) < 8:
            logger.warning(f"Invalid VCF line (too few fields): {line[:100]}")
            return None

        # Extract standard fields
        chrom = fields[0]
        pos = int(fields[1])
        ref = fields[3]
        alt = fields[4].split(",")[0]  # Take first ALT if multiple
        qual = float(fields[5]) if fields[5] != "." else None
        filter_status = fields[6]
        info = fields[7]

        # Parse INFO field
        info_dict = self._parse_info_field(info)

        # Extract gene name
        gene = self._extract_gene(info_dict)
        if not gene:
            gene = "UNKNOWN"

        # Determine variant type
        variant_type = self._classify_variant_type(ref, alt, info_dict)

        # Extract HGVS nomenclature
        hgvs = self._extract_hgvs(info_dict, gene, ref, alt)

        # Extract population frequency
        pop_freq = self._extract_population_frequency(info_dict)

        # Extract annotation
        annotation = info_dict.get("ANN", info_dict.get("CSQ", ""))

        return Variant(
            chromosome=chrom,
            position=pos,
            ref_allele=ref,
            alt_allele=alt,
            gene=gene,
            variant_type=variant_type,
            hgvs_nomenclature=hgvs,
            quality_score=qual,
            population_frequency=pop_freq,
            annotation=annotation[:200]
            if annotation
            else None,  # Truncate long annotations
            filter_status=filter_status,
        )

    def _parse_info_field(self, info: str) -> Dict[str, str]:
        """Parse INFO field into dictionary"""
        info_dict = {}

        for item in info.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                info_dict[key] = value
            else:
                info_dict[item] = "True"

        return info_dict

    def _extract_gene(self, info_dict: Dict[str, str]) -> Optional[str]:
        """Extract gene name from INFO field"""

        # Try common gene annotation fields
        for field in ["GENE", "GENEINFO", "Gene", "gene"]:
            if field in info_dict:
                gene = info_dict[field]
                # Clean gene name
                if ":" in gene:
                    gene = gene.split(":")[0]
                if "|" in gene:
                    gene = gene.split("|")[0]
                return gene

        # Try annotation fields (ANN or CSQ)
        for field in ["ANN", "CSQ"]:
            if field in info_dict:
                # Annotation format: Gene|Effect|...
                parts = info_dict[field].split("|")
                if len(parts) > 0:
                    return parts[0]

        return None

    def _classify_variant_type(
        self, ref: str, alt: str, info_dict: Dict[str, str]
    ) -> VariantType:
        """Classify variant type based on alleles and annotations"""

        # Check annotation for consequence
        for field in ["ANN", "CSQ", "Consequence"]:
            if field in info_dict:
                ann = info_dict[field].lower()

                if "frameshift" in ann:
                    return VariantType.FRAMESHIFT
                elif "stop_gained" in ann or "nonsense" in ann:
                    return VariantType.STOP_GAINED
                elif "stop_lost" in ann:
                    return VariantType.STOP_LOST
                elif "splice" in ann:
                    return VariantType.SPLICE_SITE
                elif "missense" in ann:
                    return VariantType.MISSENSE
                elif "synonymous" in ann:
                    return VariantType.SYNONYMOUS
                elif "intergenic" in ann:
                    return VariantType.INTERGENIC

        # Fallback: classify by length
        ref_len = len(ref)
        alt_len = len(alt)

        if ref_len == alt_len == 1:
            return VariantType.MISSENSE  # Likely SNV
        elif ref_len != alt_len:
            if (ref_len - alt_len) % 3 != 0 and (alt_len - ref_len) % 3 != 0:
                return VariantType.FRAMESHIFT
            else:
                return VariantType.INFRAME_INDEL

        return VariantType.UNKNOWN

    def _extract_hgvs(
        self, info_dict: Dict[str, str], gene: str, ref: str, alt: str
    ) -> str:
        """Extract or construct HGVS nomenclature"""

        # Try to find HGVS in INFO
        for field in ["HGVS", "HGVSc", "HGVSp", "hgvs"]:
            if field in info_dict:
                return info_dict[field]

        # Try annotation fields
        for field in ["ANN", "CSQ"]:
            if field in info_dict:
                ann_parts = info_dict[field].split("|")
                # Look for HGVS-like patterns in annotation
                for part in ann_parts:
                    if ":c." in part or ":p." in part:
                        return part

        # Fallback: construct simple nomenclature
        if len(ref) == 1 and len(alt) == 1:
            return f"{gene}:c.{ref}>{alt}"
        else:
            return f"{gene}:c.{ref}_{alt}"

    def _extract_population_frequency(
        self, info_dict: Dict[str, str]
    ) -> Optional[float]:
        """Extract population allele frequency"""

        # Try common frequency fields
        for field in ["AF", "gnomAD_AF", "ExAC_AF", "MAF"]:
            if field in info_dict:
                try:
                    return float(info_dict[field])
                except (ValueError, TypeError):
                    continue

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        variants = self.parse()

        genes = [v.gene for v in variants]
        types = [v.variant_type.value for v in variants]

        return {
            "total_variants": len(variants),
            "unique_genes": len(set(genes)),
            "gene_distribution": {gene: genes.count(gene) for gene in set(genes)},
            "type_distribution": {vtype: types.count(vtype) for vtype in set(types)},
            "avg_quality": sum(v.quality_score for v in variants if v.quality_score)
            / len(variants)
            if variants
            else 0,
        }


# Convenience function
def parse_vcf(
    vcf_path: str, genes: Optional[List[str]] = None, min_quality: float = 0.0
) -> List[Variant]:
    """
    Quick parse function

    Example:
        variants = parse_vcf("sample.vcf", genes=['BRCA1', 'BRCA2'])
    """
    parser = VCFParser(vcf_path, min_quality=min_quality)
    return parser.parse(genes_of_interest=genes)
