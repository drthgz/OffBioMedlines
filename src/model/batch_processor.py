"""Batch Processing Engine.

Efficiently processes multiple variants in batches with progress tracking,
timeout handling, and memory optimization.

Example:
    >>> processor = BatchProcessor(medgemma_model, batch_size=10)
    >>> results = processor.process_vcf("sample.vcf", genes=["BRCA1", "BRCA2"])
    >>> print(f"Processed {len(results)} variants in {processor.elapsed_time:.1f}s")
"""

import logging
import time
from dataclasses import dataclass
from typing import Callable, Generator, List, Optional

from src.data import Variant, VCFParser
from src.model.confidence import Classification, classify_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Results from processing a batch of variants.

    Attributes:
        batch_id: Sequential batch number.
        variants_processed: Count of variants in batch.
        classifications: List of Classification objects.
        processing_time: Time taken for this batch (seconds).
        errors: Count of errors encountered.
    """

    batch_id: int
    variants_processed: int
    classifications: List[Classification]
    processing_time: float
    errors: int = 0


@dataclass
class ProcessingSummary:
    """Summary statistics for batch processing run.

    Attributes:
        total_variants: Total variants attempted.
        successful: Variants successfully processed.
        failed: Variants that errored.
        total_time: Total elapsed time (seconds).
        avg_time_per_variant: Average processing time.
        batches_processed: Number of batches completed.
    """

    total_variants: int
    successful: int
    failed: int
    total_time: float
    avg_time_per_variant: float
    batches_processed: int


class BatchProcessor:
    """Process multiple variants efficiently in batches.

    Handles batching, progress tracking, timeout management, and
    memory-efficient streaming for large VCF files.

    Attributes:
        batch_size: Variants per batch.
        timeout_per_variant: Max seconds per variant (None = no limit).
        inference_function: Model inference callable.

    Example:
        >>> def inference(variant):
        ...     return "This variant is pathogenic (confidence: 0.92)"
        >>> processor = BatchProcessor(inference, batch_size=50)
        >>> results = processor.process_vcf("sample.vcf")
    """

    def __init__(
        self,
        inference_function: Callable[[Variant], str],
        batch_size: int = 10,
        timeout_per_variant: Optional[float] = None,
    ) -> None:
        """Initialize batch processor.

        Args:
            inference_function: Function that takes Variant, returns prediction string.
            batch_size: Number of variants per batch.
            timeout_per_variant: Max seconds per variant (None = unlimited).
        """
        self.inference_function = inference_function
        self.batch_size = batch_size
        self.timeout_per_variant = timeout_per_variant

        self.total_processed = 0
        self.total_errors = 0
        self.start_time = 0.0
        self.elapsed_time = 0.0

        logger.info(
            f"Initialized BatchProcessor (batch_size={batch_size}, "
            f"timeout={timeout_per_variant}s)"
        )

    def process_vcf(
        self,
        vcf_path: str,
        genes_of_interest: Optional[List[str]] = None,
        min_quality: float = 0.0,
        max_variants: Optional[int] = None,
    ) -> List[Classification]:
        """Process all variants from VCF file.

        Args:
            vcf_path: Path to VCF file.
            genes_of_interest: Filter to specific genes.
            min_quality: Minimum QUAL score.
            max_variants: Max variants to process (None = all).

        Returns:
            List of Classification objects.

        Example:
            >>> results = processor.process_vcf(
            ...     "sample.vcf",
            ...     genes=["BRCA1", "BRCA2"],
            ...     min_quality=50
            ... )
        """
        # Parse VCF
        parser = VCFParser(vcf_path, min_quality=min_quality)
        variants = parser.parse(genes_of_interest=genes_of_interest)

        if max_variants:
            variants = variants[:max_variants]

        logger.info(f"Processing {len(variants)} variants from {vcf_path}")

        # Process in batches
        all_classifications = []
        self.start_time = time.time()

        for batch_result in self._process_batches(variants):
            all_classifications.extend(batch_result.classifications)

        self.elapsed_time = time.time() - self.start_time

        logger.info(
            f"✓ Completed: {self.total_processed} variants in "
            f"{self.elapsed_time:.1f}s "
            f"({self.elapsed_time/self.total_processed:.2f}s/variant)"
        )

        return all_classifications

    def _process_batches(
        self, variants: List[Variant]
    ) -> Generator[BatchResult, None, None]:
        """Generate BatchResult objects from variant list.

        Args:
            variants: List of Variant objects to process.

        Yields:
            BatchResult for each batch processed.
        """
        total_batches = (len(variants) + self.batch_size - 1) // self.batch_size

        for batch_id in range(total_batches):
            start_idx = batch_id * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(variants))
            batch = variants[start_idx:end_idx]

            batch_start_time = time.time()
            classifications = []
            errors = 0

            for variant in batch:
                try:
                    classification = self._process_single_variant(variant)
                    classifications.append(classification)
                    self.total_processed += 1
                except Exception as e:
                    logger.warning(
                        f"Error processing {variant}: {e}"
                    )
                    errors += 1
                    self.total_errors += 1

            batch_time = time.time() - batch_start_time

            # Progress update
            progress = ((batch_id + 1) / total_batches) * 100
            eta = (
                (self.elapsed_time / (batch_id + 1)) * (total_batches - batch_id - 1)
                if batch_id > 0
                else 0
            )

            logger.info(
                f"Batch {batch_id + 1}/{total_batches} complete "
                f"({progress:.1f}%, ETA: {eta:.0f}s)"
            )

            yield BatchResult(
                batch_id=batch_id,
                variants_processed=len(batch),
                classifications=classifications,
                processing_time=batch_time,
                errors=errors,
            )

    def _process_single_variant(self, variant: Variant) -> Classification:
        """Process single variant through inference.

        Args:
            variant: Variant object to classify.

        Returns:
            Classification object.

        Raises:
            TimeoutError: If processing exceeds timeout.
            RuntimeError: If inference fails.
        """
        start_time = time.time()

        try:
            # Call inference function
            model_output = self.inference_function(variant)

            # Check timeout
            if self.timeout_per_variant:
                elapsed = time.time() - start_time
                if elapsed > self.timeout_per_variant:
                    raise TimeoutError(
                        f"Variant processing exceeded timeout "
                        f"({elapsed:.1f}s > {self.timeout_per_variant}s)"
                    )

            # Extract classification
            classification = classify_prediction(
                model_output=model_output,
                variant_id=variant.hgvs_nomenclature,
            )

            return classification

        except Exception as e:
            logger.error(f"Inference failed for {variant}: {e}")
            raise RuntimeError(f"Inference error: {e}") from e

    def get_summary(self) -> ProcessingSummary:
        """Get processing summary statistics.

        Returns:
            ProcessingSummary object with run statistics.

        Example:
            >>> summary = processor.get_summary()
            >>> print(f"Success rate: {summary.successful/summary.total_variants:.1%}")
        """
        total = self.total_processed + self.total_errors
        avg_time = (
            self.elapsed_time / self.total_processed
            if self.total_processed > 0
            else 0.0
        )

        return ProcessingSummary(
            total_variants=total,
            successful=self.total_processed,
            failed=self.total_errors,
            total_time=self.elapsed_time,
            avg_time_per_variant=avg_time,
            batches_processed=(total + self.batch_size - 1) // self.batch_size,
        )

    def estimate_time(self, num_variants: int) -> float:
        """Estimate processing time for given variant count.

        Args:
            num_variants: Number of variants to process.

        Returns:
            Estimated time in seconds.

        Example:
            >>> est_time = processor.estimate_time(100)
            >>> print(f"Estimated: {est_time/60:.1f} minutes")
        """
        if self.total_processed == 0:
            # No data yet, use conservative estimate
            return num_variants * 3.0  # Assume 3s per variant

        avg_time = self.elapsed_time / self.total_processed
        return num_variants * avg_time

    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.total_processed = 0
        self.total_errors = 0
        self.start_time = 0.0
        self.elapsed_time = 0.0
        logger.info("Processor statistics reset")


def batch_process_vcf(
    vcf_path: str,
    inference_function: Callable[[Variant], str],
    batch_size: int = 10,
    genes: Optional[List[str]] = None,
) -> List[Classification]:
    """Convenience function for batch processing.

    Args:
        vcf_path: Path to VCF file.
        inference_function: Model inference function.
        batch_size: Variants per batch.
        genes: Filter to specific genes.

    Returns:
        List of Classification objects.

    Example:
        >>> def my_inference(v):
        ...     return f"Pathogenic (confidence: 0.9)"
        >>> results = batch_process_vcf("sample.vcf", my_inference, batch_size=50)
    """
    processor = BatchProcessor(inference_function, batch_size=batch_size)
    return processor.process_vcf(vcf_path, genes_of_interest=genes)
