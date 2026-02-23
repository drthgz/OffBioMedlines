"""Model module for MedGemma integration and clinical validation."""

from src.model.confidence import (
    Classification,
    ConfidenceScore,
    PredictionClass,
    extract_confidence,
    classify_prediction,
    filter_low_confidence,
)
from src.model.clinical_validator import (
    ClinicalValidator,
    GoldStandardVariant,
    DiscordantCase,
    load_gold_standard,
)
from src.model.batch_processor import (
    BatchProcessor,
    BatchResult,
    ProcessingSummary,
    batch_process_vcf,
)
from src.model.report_generator import (
    ReportGenerator,
    ReportMetadata,
    generate_all_reports,
)

__all__ = [
    # Confidence extraction
    "Classification",
    "ConfidenceScore",
    "PredictionClass",
    "extract_confidence",
    "classify_prediction",
    "filter_low_confidence",
    # Clinical validation
    "ClinicalValidator",
    "GoldStandardVariant",
    "DiscordantCase",
    "load_gold_standard",
    # Batch processing
    "BatchProcessor",
    "BatchResult",
    "ProcessingSummary",
    "batch_process_vcf",
    # Report generation
    "ReportGenerator",
    "ReportMetadata",
    "generate_all_reports",
]
