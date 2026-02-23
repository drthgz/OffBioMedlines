"""
Supervisor Agent - Multi-Agent Workflow Orchestrator

Coordinates specialized gene agents for parallel cancer genomics analysis.
Responsible for:
- Task distribution to specialized agents
- Parallel execution management
- Result aggregation and prioritization
- Comprehensive report generation
"""

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.data.vcf_parser import Variant, VCFParser
from src.agents.base_agent import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """
    Container for multi-agent workflow results

    Attributes:
        total_variants: Total variants analyzed across all agents
        agent_results: Results from each specialized agent
        critical_findings: High-priority actionable findings
        execution_time: Total workflow execution time
        agents_completed: Number of agents that completed successfully
        agents_failed: Number of agents that failed
        metadata: Additional workflow information
    """

    total_variants: int
    agent_results: List[AgentResult]
    critical_findings: List[Dict[str, Any]]
    execution_time: float
    agents_completed: int
    agents_failed: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "total_variants": self.total_variants,
            "agent_results": [r.to_dict() for r in self.agent_results],
            "critical_findings": self.critical_findings,
            "execution_time": self.execution_time,
            "agents_completed": self.agents_completed,
            "agents_failed": self.agents_failed,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def get_summary(self) -> str:
        """Generate human-readable summary"""
        summary = [
            f"Cancer Genomics Analysis Summary",
            f"=" * 50,
            f"Total Variants: {self.total_variants}",
            f"Agents Run: {len(self.agent_results)}",
            f"  ✓ Completed: {self.agents_completed}",
            f"  ✗ Failed: {self.agents_failed}",
            f"Critical Findings: {len(self.critical_findings)}",
            f"Execution Time: {self.execution_time:.2f}s",
            f"",
            f"Agent Performance:",
        ]

        for result in self.agent_results:
            status_icon = "✓" if result.status == AgentStatus.COMPLETED else "✗"
            summary.append(
                f"  {status_icon} {result.agent_name} ({result.gene_symbol}): "
                f"{result.variants_analyzed} variants, {result.execution_time:.2f}s"
            )

        if self.critical_findings:
            summary.append(f"\nCritical Findings:")
            for i, finding in enumerate(self.critical_findings[:5], 1):
                summary.append(f"  {i}. {finding.get('summary', 'N/A')}")

        return "\n".join(summary)


class SupervisorAgent:
    """
    Supervisor Agent for Multi-Agent Cancer Genomics Workflow

    Orchestrates specialized gene agents to perform parallel analysis of
    cancer-related variants. Distributes work, manages execution, aggregates
    results, and prioritizes critical clinical findings.

    Example:
        >>> supervisor = SupervisorAgent()
        >>> supervisor.register_agent(BRCAAgent())
        >>> supervisor.register_agent(EGFRAgent())
        >>> result = supervisor.analyze_cancer_panel("sample.vcf")
        >>> print(result.get_summary())
    """

    def __init__(self, max_parallel_agents: int = 4, timeout_per_agent: int = 300):
        """
        Initialize supervisor agent

        Args:
            max_parallel_agents: Maximum agents to run in parallel
            timeout_per_agent: Timeout in seconds for each agent
        """
        self.agents: List[BaseAgent] = []
        self.max_parallel_agents = max_parallel_agents
        self.timeout_per_agent = timeout_per_agent
        self.logger = logging.getLogger(__name__)

    def register_agent(self, agent: BaseAgent):
        """
        Register a specialized agent with the supervisor

        Args:
            agent: Agent instance to register
        """
        self.agents.append(agent)
        self.logger.info(
            f"Registered agent: {agent.agent_name} "
            f"(specializes in {', '.join(agent.gene_symbols)})"
        )

    def analyze_cancer_panel(
        self, vcf_file_path: str, gene_list: Optional[List[str]] = None
    ) -> WorkflowResult:
        """
        Analyze cancer genomics panel using multi-agent workflow

        Args:
            vcf_file_path: Path to VCF file with variants
            gene_list: Optional list of genes to focus on (uses all if None)

        Returns:
            WorkflowResult with aggregated analysis
        """
        start_time = time.time()

        self.logger.info(f"Starting cancer panel analysis: {vcf_file_path}")

        # Parse VCF file
        parser = VCFParser(vcf_file_path)
        variants = parser.parse()

        self.logger.info(f"Parsed {len(variants)} variants from VCF")

        # Filter by gene list if provided
        if gene_list:
            variants = [v for v in variants if v.gene in gene_list]
            self.logger.info(
                f"Filtered to {len(variants)} variants in genes: {gene_list}"
            )

        # Analyze with agents
        result = self.analyze_variants(variants)

        result.execution_time = time.time() - start_time

        self.logger.info(
            f"Cancer panel analysis completed in {result.execution_time:.2f}s"
        )

        return result

    def analyze_variants(self, variants: List[Variant]) -> WorkflowResult:
        """
        Analyze variants using registered agents in parallel

        Args:
            variants: List of variants to analyze

        Returns:
            WorkflowResult with aggregated results
        """
        if not self.agents:
            raise ValueError("No agents registered. Use register_agent() first.")

        start_time = time.time()
        agent_results = []

        self.logger.info(
            f"Distributing {len(variants)} variants to {len(self.agents)} agents"
        )

        # Execute agents in parallel
        with ThreadPoolExecutor(max_workers=self.max_parallel_agents) as executor:
            # Submit all agent tasks
            future_to_agent = {
                executor.submit(agent.run, variants): agent for agent in self.agents
            }

            # Collect results as they complete
            for future in as_completed(
                future_to_agent, timeout=self.timeout_per_agent * len(self.agents)
            ):
                agent = future_to_agent[future]
                try:
                    result = future.result(timeout=self.timeout_per_agent)
                    agent_results.append(result)

                    self.logger.info(
                        f"Agent {result.agent_name} completed: "
                        f"{result.variants_analyzed} variants in {result.execution_time:.2f}s"
                    )

                except TimeoutError:
                    self.logger.error(f"Agent {agent.agent_name} timed out")
                    agent_results.append(
                        AgentResult(
                            agent_name=agent.agent_name,
                            gene_symbol=",".join(agent.gene_symbols),
                            variants_analyzed=0,
                            predictions=[],
                            clinical_insights=[],
                            execution_time=self.timeout_per_agent,
                            status=AgentStatus.TIMEOUT,
                            error_message=f"Agent timed out after {self.timeout_per_agent}s",
                        )
                    )

                except Exception as e:
                    self.logger.error(
                        f"Agent {agent.agent_name} failed: {str(e)}", exc_info=True
                    )
                    agent_results.append(
                        AgentResult(
                            agent_name=agent.agent_name,
                            gene_symbol=",".join(agent.gene_symbols),
                            variants_analyzed=0,
                            predictions=[],
                            clinical_insights=[],
                            execution_time=time.time() - start_time,
                            status=AgentStatus.FAILED,
                            error_message=str(e),
                        )
                    )

        # Aggregate results
        total_variants = sum(r.variants_analyzed for r in agent_results)
        agents_completed = sum(
            1 for r in agent_results if r.status == AgentStatus.COMPLETED
        )
        agents_failed = len(agent_results) - agents_completed

        # Extract critical findings
        critical_findings = self._prioritize_findings(agent_results)

        workflow_result = WorkflowResult(
            total_variants=total_variants,
            agent_results=agent_results,
            critical_findings=critical_findings,
            execution_time=time.time() - start_time,
            agents_completed=agents_completed,
            agents_failed=agents_failed,
            metadata={
                "num_agents": len(self.agents),
                "input_variants": len(variants),
                "genes_analyzed": list(
                    set(gene for agent in self.agents for gene in agent.gene_symbols)
                ),
            },
        )

        self.logger.info(
            f"Workflow completed: {agents_completed}/{len(self.agents)} agents succeeded"
        )

        return workflow_result

    def _prioritize_findings(
        self, agent_results: List[AgentResult]
    ) -> List[Dict[str, Any]]:
        """
        Extract and prioritize critical clinical findings

        Prioritization criteria:
        1. Pathogenic variants in cancer genes (BRCA, TP53, EGFR)
        2. Actionable variants (therapy implications)
        3. High-confidence predictions

        Args:
            agent_results: Results from all agents

        Returns:
            Sorted list of critical findings
        """
        critical_findings = []

        # Priority genes for cancer genomics
        high_priority_genes = {"BRCA1", "BRCA2", "TP53", "EGFR", "KRAS", "PTEN"}

        for result in agent_results:
            if result.status != AgentStatus.COMPLETED:
                continue

            for prediction in result.predictions:
                # Check for pathogenic variants
                classification = prediction.get("prediction", "").lower()
                confidence = prediction.get("confidence", 0.0)
                gene = prediction.get("gene", "")

                is_pathogenic = (
                    "pathogenic" in classification and "benign" not in classification
                )
                is_high_confidence = confidence >= 0.85
                is_priority_gene = gene in high_priority_genes

                # Score finding
                priority_score = 0
                if is_pathogenic:
                    priority_score += 10
                if is_high_confidence:
                    priority_score += 5
                if is_priority_gene:
                    priority_score += 8

                if priority_score >= 15:  # Threshold for critical
                    critical_findings.append(
                        {
                            "priority_score": priority_score,
                            "gene": gene,
                            "variant": f"{prediction.get('chromosome', '')}:{prediction.get('position', '')} {prediction.get('ref', '')}>{prediction.get('alt', '')}",
                            "classification": classification,
                            "confidence": confidence,
                            "agent": result.agent_name,
                            "summary": f"{gene} {classification} variant (confidence: {confidence:.0%})",
                            "clinical_insight": prediction.get(
                                "reasoning", "No reasoning provided"
                            ),
                            "actionable": "therapy"
                            in prediction.get("reasoning", "").lower(),
                        }
                    )

        # Sort by priority score (highest first)
        critical_findings.sort(key=lambda x: x["priority_score"], reverse=True)

        self.logger.info(f"Identified {len(critical_findings)} critical findings")

        return critical_findings

    def get_agent_summary(self) -> str:
        """Get summary of registered agents"""
        if not self.agents:
            return "No agents registered"

        lines = [f"Registered Agents ({len(self.agents)}):"]
        for agent in self.agents:
            lines.append(f"  • {agent.agent_name}: {', '.join(agent.gene_symbols)}")
        return "\n".join(lines)
