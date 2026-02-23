"""Clinical Report Generation Module.

Generates comprehensive validation reports in multiple formats:
- HTML with interactive visualizations
- JSON for programmatic access
- CSV for spreadsheet analysis

Example:
    >>> generator = ReportGenerator()
    >>> report_data = validator.validate_batch(predictions)
    >>> generator.generate_html(report_data, "report.html")
    >>> generator.generate_json(report_data, "report.json")
"""

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.model.confidence import Classification, PredictionClass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReportMetadata:
    """Metadata for clinical validation report.

    Attributes:
        generated_at: Timestamp of report generation.
        vcf_file: Source VCF filename.
        total_variants: Number of variants analyzed.
        model_version: MedGemma model identifier.
        confidence_threshold: Minimum confidence for evaluation.
    """

    generated_at: str
    vcf_file: Optional[str] = None
    total_variants: int = 0
    model_version: str = "MedGemma-4B-4bit"
    confidence_threshold: float = 0.85


class ReportGenerator:
    """Generates clinical validation reports in multiple formats.

    Supports HTML (with visualizations), JSON, and CSV export of
    validation metrics, confidence distributions, and per-gene performance.
    """

    def __init__(self):
        """Initialize report generator."""
        self.metadata = None

    def generate_html(
        self,
        validation_report: Dict[str, Any],
        output_path: str,
        classifications: Optional[List[Classification]] = None,
    ) -> str:
        """Generate HTML report with visualizations.

        Args:
            validation_report: Report dict from ClinicalValidator.validate_batch()
            output_path: Path to save HTML file.
            classifications: Optional list of all classifications for distribution.

        Returns:
            Path to generated HTML file.

        Example:
            >>> report = validator.validate_batch(predictions)
            >>> generator.generate_html(report, "results.html", predictions)
        """
        output_path = Path(output_path)

        # Build HTML content
        html = self._build_html_structure(validation_report, classifications)

        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)

        logger.info(f"HTML report generated: {output_path}")
        return str(output_path)

    def generate_json(
        self,
        validation_report: Dict[str, Any],
        output_path: str,
        metadata: Optional[ReportMetadata] = None,
    ) -> str:
        """Generate JSON report for programmatic access.

        Args:
            validation_report: Report dict from ClinicalValidator.
            output_path: Path to save JSON file.
            metadata: Optional metadata to include.

        Returns:
            Path to generated JSON file.

        Example:
            >>> metadata = ReportMetadata(
            ...     generated_at=datetime.now().isoformat(),
            ...     vcf_file="sample.vcf",
            ...     total_variants=150
            ... )
            >>> generator.generate_json(report, "results.json", metadata)
        """
        output_path = Path(output_path)

        # Build JSON structure
        report_data = {
            "metadata": asdict(metadata) if metadata else self._default_metadata(),
            "validation_metrics": {
                "accuracy": validation_report.get("accuracy", 0.0),
                "sensitivity": validation_report.get("sensitivity", 0.0),
                "specificity": validation_report.get("specificity", 0.0),
                "precision": validation_report.get("precision", 0.0),
                "f1_score": validation_report.get("f1_score", 0.0),
            },
            "confusion_matrix": {
                "true_positives": validation_report.get("true_positives", 0),
                "true_negatives": validation_report.get("true_negatives", 0),
                "false_positives": validation_report.get("false_positives", 0),
                "false_negatives": validation_report.get("false_negatives", 0),
            },
            "evaluation_summary": {
                "total_evaluated": validation_report.get("total_evaluated", 0),
                "correct": validation_report.get("correct", 0),
                "incorrect": validation_report.get("incorrect", 0),
            },
            "per_gene_metrics": validation_report.get("per_gene_metrics", {}),
            "discordant_cases": [
                {
                    "variant_id": case.variant_id,
                    "gene": case.gene,
                    "predicted": case.predicted,
                    "expected": case.expected,
                    "confidence": case.confidence,
                }
                for case in validation_report.get("discordant_cases", [])
            ],
        }

        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"JSON report generated: {output_path}")
        return str(output_path)

    def generate_csv(
        self,
        classifications: List[Classification],
        output_path: str,
        include_reasoning: bool = False,
    ) -> str:
        """Generate CSV report for spreadsheet analysis.

        Args:
            classifications: List of Classification objects.
            output_path: Path to save CSV file.
            include_reasoning: Include reasoning text (increases file size).

        Returns:
            Path to generated CSV file.

        Example:
            >>> generator.generate_csv(predictions, "results.csv")
        """
        output_path = Path(output_path)

        # Define CSV columns
        fieldnames = [
            "variant_id",
            "prediction",
            "confidence",
            "is_clinical_grade",
        ]
        if include_reasoning:
            fieldnames.append("reasoning")

        # Write CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for cls in classifications:
                row = {
                    "variant_id": cls.variant_id,
                    "prediction": cls.prediction.value,
                    "confidence": f"{cls.confidence.confidence:.3f}",
                    "is_clinical_grade": cls.confidence.confidence >= 0.85,
                }
                if include_reasoning:
                    row["reasoning"] = cls.reasoning or ""

                writer.writerow(row)

        logger.info(
            f"CSV report generated: {output_path} ({len(classifications)} rows)"
        )
        return str(output_path)

    def generate_discordant_csv(
        self, validation_report: Dict[str, Any], output_path: str
    ) -> str:
        """Generate CSV of discordant cases for manual review.

        Args:
            validation_report: Report dict from ClinicalValidator.
            output_path: Path to save CSV file.

        Returns:
            Path to generated CSV file.
        """
        output_path = Path(output_path)
        discordant_cases = validation_report.get("discordant_cases", [])

        # Write discordant cases CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as csvfile:
            fieldnames = ["variant_id", "gene", "predicted", "expected", "confidence"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for case in discordant_cases:
                writer.writerow(
                    {
                        "variant_id": case.variant_id,
                        "gene": case.gene,
                        "predicted": case.predicted,
                        "expected": case.expected,
                        "confidence": f"{case.confidence:.3f}",
                    }
                )

        logger.info(
            f"Discordant cases CSV generated: {output_path} ({len(discordant_cases)} cases)"
        )
        return str(output_path)

    def _build_html_structure(
        self,
        validation_report: Dict[str, Any],
        classifications: Optional[List[Classification]] = None,
    ) -> str:
        """Build HTML report structure."""
        metrics = validation_report
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build confidence distribution data
        confidence_chart = ""
        if classifications:
            confidence_chart = self._build_confidence_chart(classifications)

        # Build per-gene chart
        gene_chart = self._build_gene_performance_chart(
            metrics.get("per_gene_metrics", {})
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MedGemma Clinical Validation Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .timestamp {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .good {{ color: #28a745; font-weight: bold; }}
        .warning {{ color: #ffc107; font-weight: bold; }}
        .danger {{ color: #dc3545; font-weight: bold; }}
        .chart-container {{
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧬 MedGemma Clinical Validation Report</h1>
        <div class="timestamp">Generated: {timestamp}</div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Accuracy</div>
            <div class="metric-value {self._get_accuracy_class(metrics.get("accuracy", 0))}">{metrics.get("accuracy", 0):.1%}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Sensitivity</div>
            <div class="metric-value">{metrics.get("sensitivity", 0):.1%}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Specificity</div>
            <div class="metric-value">{metrics.get("specificity", 0):.1%}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">F1 Score</div>
            <div class="metric-value">{metrics.get("f1_score", 0):.3f}</div>
        </div>
    </div>

    <div class="section">
        <h2>Confusion Matrix</h2>
        <table>
            <tr>
                <th>True Positives</th>
                <th>True Negatives</th>
                <th>False Positives</th>
                <th>False Negatives</th>
            </tr>
            <tr>
                <td class="good">{metrics.get("true_positives", 0)}</td>
                <td class="good">{metrics.get("true_negatives", 0)}</td>
                <td class="danger">{metrics.get("false_positives", 0)}</td>
                <td class="danger">{metrics.get("false_negatives", 0)}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>Evaluation Summary</h2>
        <p><strong>Total Evaluated:</strong> {metrics.get("total_evaluated", 0)} variants</p>
        <p><strong>Correct:</strong> <span class="good">{metrics.get("correct", 0)}</span></p>
        <p><strong>Incorrect:</strong> <span class="danger">{metrics.get("incorrect", 0)}</span></p>
    </div>

    {gene_chart}
    {confidence_chart}

    <div class="section">
        <h2>Discordant Cases ({len(metrics.get("discordant_cases", []))})</h2>
        {self._build_discordant_table(metrics.get("discordant_cases", []))}
    </div>
</body>
</html>"""
        return html

    def _build_confidence_chart(self, classifications: List[Classification]) -> str:
        """Build confidence distribution visualization."""
        bins = {"0.0-0.5": 0, "0.5-0.7": 0, "0.7-0.85": 0, "0.85-1.0": 0}

        for cls in classifications:
            conf = cls.confidence.confidence
            if conf < 0.5:
                bins["0.0-0.5"] += 1
            elif conf < 0.7:
                bins["0.5-0.7"] += 1
            elif conf < 0.85:
                bins["0.7-0.85"] += 1
            else:
                bins["0.85-1.0"] += 1

        total = len(classifications)
        chart = """
    <div class="section">
        <h2>Confidence Distribution</h2>
        <div class="chart-container">
            <table>
                <tr>
                    <th>Confidence Range</th>
                    <th>Count</th>
                    <th>Percentage</th>
                    <th>Status</th>
                </tr>
"""
        for bin_range, count in bins.items():
            pct = (count / total * 100) if total > 0 else 0
            status = (
                "✅ Clinical Grade" if bin_range == "0.85-1.0" else "⚠️ Sub-threshold"
            )
            chart += f"""
                <tr>
                    <td>{bin_range}</td>
                    <td>{count}</td>
                    <td>{pct:.1f}%</td>
                    <td>{status}</td>
                </tr>
"""
        chart += """
            </table>
        </div>
    </div>
"""
        return chart

    def _build_gene_performance_chart(self, per_gene_metrics: Dict[str, Any]) -> str:
        """Build per-gene performance table."""
        if not per_gene_metrics:
            return ""

        chart = """
    <div class="section">
        <h2>Per-Gene Performance</h2>
        <table>
            <tr>
                <th>Gene</th>
                <th>Total</th>
                <th>Correct</th>
                <th>Incorrect</th>
                <th>Accuracy</th>
            </tr>
"""
        for gene, metrics in sorted(per_gene_metrics.items()):
            accuracy = metrics.get("accuracy", 0)
            accuracy_class = self._get_accuracy_class(accuracy)
            chart += f"""
            <tr>
                <td><strong>{gene}</strong></td>
                <td>{metrics.get("total", 0)}</td>
                <td class="good">{metrics.get("correct", 0)}</td>
                <td class="danger">{metrics.get("incorrect", 0)}</td>
                <td class="{accuracy_class}">{accuracy:.1%}</td>
            </tr>
"""
        chart += """
        </table>
    </div>
"""
        return chart

    def _build_discordant_table(self, discordant_cases: List) -> str:
        """Build table of discordant cases."""
        if not discordant_cases:
            return "<p>✅ No discordant cases found. All predictions match gold standard!</p>"

        table = """
        <table>
            <tr>
                <th>Variant ID</th>
                <th>Gene</th>
                <th>Predicted</th>
                <th>Expected</th>
                <th>Confidence</th>
            </tr>
"""
        for case in discordant_cases:
            table += f"""
            <tr>
                <td>{case.variant_id}</td>
                <td>{case.gene}</td>
                <td class="danger">{case.predicted}</td>
                <td class="good">{case.expected}</td>
                <td>{case.confidence:.3f}</td>
            </tr>
"""
        table += """
        </table>
"""
        return table

    def _get_accuracy_class(self, accuracy: float) -> str:
        """Get CSS class based on accuracy threshold."""
        if accuracy >= 0.85:
            return "good"
        elif accuracy >= 0.70:
            return "warning"
        else:
            return "danger"

    def _default_metadata(self) -> Dict[str, Any]:
        """Generate default metadata."""
        return asdict(
            ReportMetadata(
                generated_at=datetime.now().isoformat(),
                model_version="MedGemma-4B-4bit",
            )
        )


def generate_all_reports(
    validation_report: Dict[str, Any],
    classifications: List[Classification],
    output_dir: str,
    base_name: str = "clinical_report",
) -> Dict[str, str]:
    """Generate all report formats at once.

    Args:
        validation_report: Report from ClinicalValidator.
        classifications: List of all classifications.
        output_dir: Directory to save reports.
        base_name: Base filename for reports.

    Returns:
        Dict mapping format to file path.

    Example:
        >>> reports = generate_all_reports(report, predictions, "reports/")
        >>> print(reports["html"])  # "reports/clinical_report.html"
    """
    generator = ReportGenerator()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    paths["html"] = generator.generate_html(
        validation_report, str(output_dir / f"{base_name}.html"), classifications
    )
    paths["json"] = generator.generate_json(
        validation_report, str(output_dir / f"{base_name}.json")
    )
    paths["csv"] = generator.generate_csv(
        classifications, str(output_dir / f"{base_name}.csv")
    )
    paths["discordant_csv"] = generator.generate_discordant_csv(
        validation_report, str(output_dir / f"{base_name}_discordant.csv")
    )

    logger.info(f"All reports generated in {output_dir}")
    return paths
