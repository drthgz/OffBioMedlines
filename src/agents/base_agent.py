"""
Base Agent Class for Bioinformatics Pipeline

Provides core agent functionality including:
- MedGemma inference integration
- RAG knowledge retrieval
- Result validation
- Error handling and logging
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import logging

from src.data.vcf_parser import Variant


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentResult:
    """
    Container for agent analysis results

    Attributes:
        agent_name: Name of the agent that produced the result
        gene_symbol: Gene analyzed (e.g., 'BRCA1', 'EGFR')
        variants_analyzed: Number of variants processed
        predictions: List of variant predictions with confidence
        clinical_insights: Agent-specific clinical interpretations
        execution_time: Time taken in seconds
        status: Agent execution status
        error_message: Error details if failed
        metadata: Additional agent-specific data
    """

    agent_name: str
    gene_symbol: str
    variants_analyzed: int
    predictions: List[Dict[str, Any]]
    clinical_insights: List[str]
    execution_time: float
    status: AgentStatus
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            "agent_name": self.agent_name,
            "gene_symbol": self.gene_symbol,
            "variants_analyzed": self.variants_analyzed,
            "predictions": self.predictions,
            "clinical_insights": self.clinical_insights,
            "execution_time": self.execution_time,
            "status": self.status.value,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAgent(ABC):
    """
    Abstract base class for bioinformatics analysis agents

    Each agent specializes in analyzing specific genes or biomarkers,
    leveraging MedGemma for intelligent interpretation and RAG for
    contextual medical knowledge.

    Subclasses must implement:
        - analyze_variants(): Core analysis logic
        - get_specialized_prompt(): Agent-specific prompting
        - validate_results(): Domain-specific validation
    """

    def __init__(
        self,
        agent_name: str,
        gene_symbols: List[str],
        model_inference_fn: Optional[Callable] = None,
        rag_retriever: Optional[Any] = None,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize base agent

        Args:
            agent_name: Unique identifier for the agent
            gene_symbols: List of genes this agent specializes in
            model_inference_fn: Function for MedGemma inference
            rag_retriever: Medical knowledge RAG interface
            confidence_threshold: Minimum confidence for predictions
        """
        self.agent_name = agent_name
        self.gene_symbols = gene_symbols
        self.model_inference_fn = model_inference_fn or self._mock_inference
        self.rag_retriever = rag_retriever
        self.confidence_threshold = confidence_threshold
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")

    @abstractmethod
    def analyze_variants(self, variants: List[Variant]) -> AgentResult:
        """
        Analyze variants specific to this agent's expertise

        Args:
            variants: List of variants to analyze

        Returns:
            AgentResult containing predictions and insights
        """
        pass

    @abstractmethod
    def get_specialized_prompt(self, variant: Variant) -> str:
        """
        Generate agent-specific prompt for MedGemma

        Args:
            variant: Variant to analyze

        Returns:
            Specialized prompt string
        """
        pass

    @abstractmethod
    def validate_results(self, predictions: List[Dict[str, Any]]) -> bool:
        """
        Validate analysis results against domain knowledge

        Args:
            predictions: List of predictions to validate

        Returns:
            True if results pass validation
        """
        pass

    def run(self, variants: List[Variant]) -> AgentResult:
        """
        Main execution method with error handling

        Args:
            variants: Variants to analyze

        Returns:
            AgentResult with status and predictions
        """
        import time

        start_time = time.time()

        try:
            self.status = AgentStatus.RUNNING
            self.logger.info(
                f"{self.agent_name} starting analysis of {len(variants)} variants"
            )

            # Filter variants for this agent's genes
            relevant_variants = self._filter_variants(variants)

            if not relevant_variants:
                self.logger.info(f"No variants found for genes: {self.gene_symbols}")
                return AgentResult(
                    agent_name=self.agent_name,
                    gene_symbol=",".join(self.gene_symbols),
                    variants_analyzed=0,
                    predictions=[],
                    clinical_insights=[
                        f"No variants found for {', '.join(self.gene_symbols)}"
                    ],
                    execution_time=time.time() - start_time,
                    status=AgentStatus.COMPLETED,
                )

            # Perform analysis
            result = self.analyze_variants(relevant_variants)

            # Validate results
            if not self.validate_results(result.predictions):
                result.status = AgentStatus.FAILED
                result.error_message = "Result validation failed"
            else:
                result.status = AgentStatus.COMPLETED

            result.execution_time = time.time() - start_time
            self.status = result.status

            self.logger.info(
                f"{self.agent_name} completed: {result.variants_analyzed} variants, "
                f"{len(result.predictions)} predictions, {result.execution_time:.2f}s"
            )

            return result

        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.error(f"{self.agent_name} failed: {str(e)}", exc_info=True)

            return AgentResult(
                agent_name=self.agent_name,
                gene_symbol=",".join(self.gene_symbols),
                variants_analyzed=0,
                predictions=[],
                clinical_insights=[],
                execution_time=time.time() - start_time,
                status=AgentStatus.FAILED,
                error_message=str(e),
            )

    def _filter_variants(self, variants: List[Variant]) -> List[Variant]:
        """Filter variants relevant to this agent's genes"""
        return [v for v in variants if v.gene in self.gene_symbols]

    def _get_rag_context(self, variant: Variant) -> str:
        """
        Retrieve relevant medical knowledge from RAG

        Args:
            variant: Variant to get context for

        Returns:
            Contextual medical knowledge string
        """
        if not self.rag_retriever:
            return ""

        try:
            query = f"{variant.gene} {variant.alt_allele} clinical significance"
            context = self.rag_retriever.retrieve(query, top_k=3)
            return context
        except Exception as e:
            self.logger.warning(f"RAG retrieval failed: {str(e)}")
            return ""

    def _mock_inference(self, prompt: str) -> str:
        """
        Mock inference for development/testing

        Args:
            prompt: Input prompt

        Returns:
            Mock prediction response
        """
        # Simple mock that varies based on prompt content
        if "BRCA" in prompt:
            return "Pathogenic with 92% confidence. Associated with hereditary breast/ovarian cancer."
        elif "EGFR" in prompt:
            return "Likely pathogenic with 88% confidence. May affect targeted therapy response."
        elif "TP53" in prompt:
            return "Pathogenic with 95% confidence. Tumor suppressor mutation."
        else:
            return "Likely benign with 78% confidence. Insufficient evidence for pathogenicity."

    def get_status(self) -> AgentStatus:
        """Get current agent status"""
        return self.status

    def reset(self):
        """Reset agent to idle state"""
        self.status = AgentStatus.IDLE
        self.logger.info(f"{self.agent_name} reset to idle")
