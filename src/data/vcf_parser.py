"""VCF Parser Module.

Parses Variant Call Format (VCF) files into structured Variant objects
for downstream MedGemma analysis.

Supports:
    - VCF 4.2+ specification
    - Compressed (.vcf.gz) and uncompressed files
    - Gene filtering
    - Quality score thresholds
    - INFO field annotation extraction

Example:
    >>> parser = VCFParser("sample.vcf", min_quality=20)
    >>> variants = parser.parse(genes_of_interest=["BRCA1", "BRCA2"])
    >>> print(f"Found {len(variants)} variants")
"""

import gzip
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VariantType(str, Enum):
    """Genomic variant consequence types."""

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
    """Represents a genomic variant with clinical annotations.

    Attributes:
        chromosome: Chromosome identifier (e.g., "chr1", "1").
        position: Genomic position on chromosome.
        ref_allele: Reference allele sequence.
        alt_allele: Alternate (variant) allele sequence.
        gene: Gene symbol associated with variant.
        variant_type: Consequence type (missense, frameshift, etc.).
        hgvs_nomenclature: HGVS variant designation.
        quality_score: Variant quality confidence score (optional).
        population_frequency: Allele frequency in population databases (optional).
        annotation: Functional annotation string (optional).
        filter_status: VCF FILTER column value (optional).

    Raises:
        ValueError: If chromosome or position are invalid.
    """

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

    def __str__(self) -> str:
        """Return human-readable variant string."""
        return (
            f"{self.chromosome}:{self.position} {self.ref_allele}→{self.alt_allele} "
            f"({self.gene})"
        )

    def __repr__(self) -> str:
        """Return detailed variant representation."""
        return (
            f"Variant(chr={self.chromosome}, pos={self.position}, "
            f"gene={self.gene}, type={self.variant_type.value})"
        )


class VCFParser:
    """Parse VCF files into structured Variant objects.

    This class handles parsing of Variant Call Format files, applying filters,
    and extracting clinical annotations for downstream analysis.

    Attributes:
        vcf_path: Path to VCF file (compressed or uncompressed).
        min_quality: Minimum QUAL score threshold. Defaults to 0.0.
        max_variants: Maximum variants to parse (None = unlimited). Defaults to None.

    Raises:
        FileNotFoundError: If VCF file does not exist.

    Example:
        >>> parser = VCFParser("sample.vcf", min_quality=20)
        >>> variants = parser.parse(genes_of_interest=["BRCA1"])
        >>> print(f"Parsed {len(variants)} variants")
    """

    def __init__(
        self,
        vcf_path: str,
        min_quality: float = 0.0,
        max_variants: Optional[int] = None,
    ) -> None:
        """Initialize VCF parser.

        Args:
            vcf_path: Path to VCF file.
            min_quality: Minimum QUAL score for variants (default: 0.0).
            max_variants: Max variants to parse, None for unlimited.

        Raises:
            FileNotFoundError: VCF file does not exist.
        """
        self.vcf_path = Path(vcf_path)
        self.min_quality = min_quality
        self.max_variants = max_variants

        if not self.vcf_path.exists():
            raise FileNotFoundError(f"VCF file not found: {vcf_path}")

        logger.info(f"Initialized VCF parser for: {self.vcf_path.name}")

    def parse(
        self,
        genes_of_interest: Optional[List[str]] = None,
        pass_only: bool = True,
    ) -> List[Variant]:
        """Parse VCF file and apply filters.

        Args:
            genes_of_interest: Filter to specific genes (None = all).
            pass_only: Only include variants with FILTER=PASS.

        Returns:
            List of Variant objects matching filter criteria.

        Example:
            >>> parser = VCFParser("sample.vcf")
            >>> variants = parser.parse(
            ...     genes_of_interest=["BRCA1", "BRCA2"],
            ...     pass_only=True
            ... )
        """
        variants = []

        logger.info(f"Parsing VCF file: {self.vcf_path.name}")
        if genes_of_interest:
            logger.info(f"  Filtering to genes: {', '.join(genes_of_interest)}")

        for variant in self._parse_vcf_lines():
            # Apply filter status constraint
            if pass_only and variant.filter_status != "PASS":
                continue

            # Apply gene filter
            if genes_of_interest and variant.gene not in genes_of_interest:
                continue

            # Apply quality threshold
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
        """Generate Variant objects from VCF file lines.

        Yields:
            Variant objects (skips headers and empty lines).

        Raises:
            ValueError: If VCF line format is invalid.
        """
        # Handle .gz compression
        if str(self.vcf_path).endswith(".gz"):
            file_handle = gzip.open(self.vcf_path, "rt")
        else:
            file_handle = open(self.vcf_path, "r")

        try:
            for line_num, line in enumerate(file_handle, 1):
                line = line.strip()

                # Skip header and empty lines
                if line.startswith("#") or not line:
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
        """Parse a single VCF data line.

        VCF Format: CHROM POS ID REF ALT QUAL FILTER INFO FORMAT SAMPLE...

        Args:
            line: Single VCF line (tab-separated).

        Returns:
            Variant object or None if line is malformed.

        Raises:
            ValueError: If required fields are missing or malformed.
        """
        fields = line.split("\t")

        if len(fields) < 8:
            logger.warning(f"Invalid VCF line (too few fields): {line[:100]}")
            return None

        try:
            # Extract standard VCF fields
            chrom = fields[0]
            pos = int(fields[1])
            ref = fields[3]
            alt = fields[4].split(",")[0]  # Take first ALT if multiple
            qual = float(fields[5]) if fields[5] != "." else None
            filter_status = fields[6]
            info = fields[7]

            # Parse INFO field annotations
            info_dict = self._parse_info_field(info)

            # Extract clinical annotations
            gene = self._extract_gene(info_dict) or "UNKNOWN"
            variant_type = self._classify_variant_type(ref, alt, info_dict)
            hgvs = self._extract_hgvs(info_dict, gene, ref, alt)
            pop_freq = self._extract_population_frequency(info_dict)
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
                annotation=annotation[:200] if annotation else None,
                filter_status=filter_status,
            )

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse variant line: {e}")
            return None

    def _parse_info_field(self, info: str) -> Dict[str, str]:
        """Parse VCF INFO field into dictionary.

        INFO format: KEY1=VALUE1;KEY2=VALUE2;FLAG

        Args:
            info: INFO field string from VCF.

        Returns:
            Dictionary of INFO key-value pairs.
        """
        info_dict: Dict[str, str] = {}

        for item in info.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                info_dict[key] = value
            else:
                info_dict[item] = "True"

        return info_dict

    def _extract_gene(self, info_dict: Dict[str, str]) -> Optional[str]:
        """Extract gene symbol from annotation fields.

        Tries multiple common gene annotation fields in order of preference.

        Args:
            info_dict: Parsed INFO field dictionary.

        Returns:
            Gene symbol or None if not found.
        """
        # Try explicit gene fields (case variations)
        for field in ["GENE", "GENEINFO", "Gene", "gene"]:
            if field in info_dict:
                gene = info_dict[field]
                # Clean gene name (handle pipe-separated annotations)
                if ":" in gene:
                    gene = gene.split(":")[0]
                if "|" in gene:
                    gene = gene.split("|")[0]
                return gene

        # Try annotation fields
        for field in ["ANN", "CSQ"]:
            if field in info_dict:
                # Annotation format: Gene|Effect|...
                parts = info_dict[field].split("|")
                if parts and parts[0]:
                    return parts[0]

        return None

    def _classify_variant_type(
        self,
        ref: str,
        alt: str,
        info_dict: Dict[str, str],
    ) -> VariantType:
        """Classify variant consequence type.

        Uses annotation field consequence annotations if available,
        falls back to sequence-based classification.

        Args:
            ref: Reference allele sequence.
            alt: Alternate allele sequence.
            info_dict: Parsed INFO field dictionary.

        Returns:
            VariantType classification.
        """
        # Check annotation for consequence terms
        for field in ["ANN", "CSQ", "Consequence"]:
            if field in info_dict:
                ann = info_dict[field].lower()

                # Match consequence keywords
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

        # Fallback: classify by sequence length
        ref_len = len(ref)
        alt_len = len(alt)

        if ref_len == alt_len == 1:
            return VariantType.MISSENSE  # Likely SNV

        # Check if indel is frameshift (not multiple of 3)
        if ref_len != alt_len:
            length_diff = abs(ref_len - alt_len)
            if length_diff % 3 != 0:
                return VariantType.FRAMESHIFT
            else:
                return VariantType.INFRAME_INDEL

        return VariantType.UNKNOWN

    def _extract_hgvs(
        self,
        info_dict: Dict[str, str],
        gene: str,
        ref: str,
        alt: str,
    ) -> str:
        """Extract or construct HGVS nomenclature.

        Tries to find HGVS designation in annotation fields,
        constructs simplified version if not available.

        Args:
            info_dict: Parsed INFO field dictionary.
            gene: Gene symbol.
            ref: Reference allele.
            alt: Alternate allele.

        Returns:
            HGVS nomenclature string.
        """
        # Try explicit HGVS fields
        for field in ["HGVS", "HGVSc", "HGVSp", "hgvs"]:
            if field in info_dict:
                return info_dict[field]

        # Try annotation fields
        for field in ["ANN", "CSQ"]:
            if field in info_dict:
                ann_parts = info_dict[field].split("|")
                # Look for HGVS-like patterns
                for part in ann_parts:
                    if ":c." in part or ":p." in part:
                        return part

        # Fallback: construct simple nomenclature
        if len(ref) == 1 and len(alt) == 1:
            return f"{gene}:c.{ref}>{alt}"
        else:
            return f"{gene}:c.{ref}_{alt}"

    def _extract_population_frequency(
        self,
        info_dict: Dict[str, str],
    ) -> Optional[float]:
        """Extract population allele frequency from annotations.

        Tries multiple common frequency databases in order.

        Args:
            info_dict: Parsed INFO field dictionary.

        Returns:
            Allele frequency (0-1) or None if not found.
        """
        # Try common frequency fields (in order of preference)
        for field in ["AF", "gnomAD_AF", "ExAC_AF", "MAF"]:
            if field in info_dict:
                try:
                    return float(info_dict[field])
                except (ValueError, TypeError):
                    logger.debug(
                        f"Could not parse frequency from {field}: {info_dict[field]}"
                    )
                    continue

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Generate parsing statistics for entire VCF file.

        Returns:
            Dictionary containing:
                - total_variants: Count of parsed variants
                - unique_genes: Number of distinct genes
                - gene_distribution: Variants per gene
                - type_distribution: Variants per consequence type
                - avg_quality: Mean quality score
        """
        variants = self.parse()

        genes = [v.gene for v in variants]
        types = [v.variant_type.value for v in variants]

        # Calculate average quality
        quality_scores = [v.quality_score for v in variants if v.quality_score]
        avg_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        return {
            "total_variants": len(variants),
            "unique_genes": len(set(genes)),
            "gene_distribution": {gene: genes.count(gene) for gene in set(genes)},
            "type_distribution": {vtype: types.count(vtype) for vtype in set(types)},
            "avg_quality": avg_quality,
        }


def parse_vcf(
    vcf_path: str,
    genes: Optional[List[str]] = None,
    min_quality: float = 0.0,
) -> List[Variant]:
    """Convenience function for quick VCF parsing.

    Args:
        vcf_path: Path to VCF file.
        genes: Filter to specific genes (optional).
        min_quality: Minimum QUAL score threshold.

    Returns:
        List of Variant objects.

    Example:
        >>> variants = parse_vcf("sample.vcf", genes=["BRCA1", "BRCA2"])
        >>> print(f"Found {len(variants)} variants")
    """
    parser = VCFParser(vcf_path, min_quality=min_quality)
    return parser.parse(genes_of_interest=genes)
