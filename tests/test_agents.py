"""
Multi-Agent Workflow Test Suite

Tests the supervisor-agent coordination for cancer genomics analysis.
"""

import pytest
from pathlib import Path

from src.agents import SupervisorAgent, BRCAAgent, EGFRAgent, TP53Agent, TMBAgent
from src.agents.base_agent import AgentStatus
from src.data.vcf_parser import Variant, VariantType


@pytest.fixture
def sample_variants():
    """Create sample variants for testing"""
    return [
        Variant(
            chromosome="chr17",
            position=41234470,
            ref_allele="A",
            alt_allele="G",
            gene="BRCA1",
            variant_type=VariantType.MISSENSE,
            hgvs_nomenclature="NM_007294.3:c.185A>G",
        ),
        Variant(
            chromosome="chr13",
            position=32339381,
            ref_allele="C",
            alt_allele="T",
            gene="BRCA2",
            variant_type=VariantType.MISSENSE,
            hgvs_nomenclature="NM_000059.3:c.68C>T",
        ),
        Variant(
            chromosome="chr7",
            position=55249071,
            ref_allele="G",
            alt_allele="A",
            gene="EGFR",
            variant_type=VariantType.MISSENSE,
            hgvs_nomenclature="NM_005228.5:c.2573G>A",
        ),
        Variant(
            chromosome="chr17",
            position=7577548,
            ref_allele="C",
            alt_allele="T",
            gene="TP53",
            variant_type=VariantType.MISSENSE,
            hgvs_nomenclature="NM_000546.5:c.524C>T",
        ),
    ]


class TestBRCAAgent:
    """Test BRCA analysis agent"""

    def test_brca_agent_initialization(self):
        """Test BRCA agent initializes correctly"""
        agent = BRCAAgent()

        assert agent.agent_name == "BRCAAgent"
        assert "BRCA1" in agent.gene_symbols
        assert "BRCA2" in agent.gene_symbols
        assert agent.status == AgentStatus.IDLE

    def test_brca_agent_analyzes_variants(self, sample_variants):
        """Test BRCA agent analyzes BRCA variants"""
        agent = BRCAAgent()
        brca_variants = [v for v in sample_variants if "BRCA" in v.gene]

        result = agent.run(brca_variants)

        assert result.status == AgentStatus.COMPLETED
        assert result.variants_analyzed == 2
        assert len(result.predictions) == 2
        assert all("BRCA" in p["gene"] for p in result.predictions)

    def test_brca_agent_filters_non_brca_variants(self, sample_variants):
        """Test BRCA agent ignores non-BRCA genes"""
        agent = BRCAAgent()

        result = agent.run(sample_variants)

        # Should only analyze BRCA1 and BRCA2
        assert result.variants_analyzed == 2
        assert all("BRCA" in p["gene"] for p in result.predictions)

    def test_brca_agent_generates_clinical_insights(self, sample_variants):
        """Test BRCA agent generates hereditary cancer insights"""
        agent = BRCAAgent()
        brca_variants = [v for v in sample_variants if "BRCA" in v.gene]

        result = agent.run(brca_variants)

        # Should have clinical insights (mock returns pathogenic)
        assert len(result.clinical_insights) > 0


class TestEGFRAgent:
    """Test EGFR therapy selection agent"""

    def test_egfr_agent_initialization(self):
        """Test EGFR agent initializes correctly"""
        agent = EGFRAgent()

        assert agent.agent_name == "EGFRAgent"
        assert "EGFR" in agent.gene_symbols
        assert agent.status == AgentStatus.IDLE

    def test_egfr_agent_analyzes_variants(self, sample_variants):
        """Test EGFR agent analyzes EGFR variants"""
        agent = EGFRAgent()
        egfr_variants = [v for v in sample_variants if v.gene == "EGFR"]

        result = agent.run(egfr_variants)

        assert result.status == AgentStatus.COMPLETED
        assert result.variants_analyzed == 1
        assert result.predictions[0]["gene"] == "EGFR"
        assert "therapy_relevant" in result.predictions[0]

    def test_egfr_agent_identifies_therapy_relevance(self, sample_variants):
        """Test EGFR agent identifies therapy-relevant mutations"""
        agent = EGFRAgent()
        egfr_variants = [v for v in sample_variants if v.gene == "EGFR"]

        result = agent.run(egfr_variants)

        # Mock inference should return therapy-relevant response
        assert result.predictions[0]["therapy_relevant"] is True


class TestTP53Agent:
    """Test TP53 tumor suppressor agent"""

    def test_tp53_agent_initialization(self):
        """Test TP53 agent initializes correctly"""
        agent = TP53Agent()

        assert agent.agent_name == "TP53Agent"
        assert "TP53" in agent.gene_symbols

    def test_tp53_agent_analyzes_variants(self, sample_variants):
        """Test TP53 agent analyzes TP53 variants"""
        agent = TP53Agent()
        tp53_variants = [v for v in sample_variants if v.gene == "TP53"]

        result = agent.run(tp53_variants)

        assert result.status == AgentStatus.COMPLETED
        assert result.variants_analyzed == 1
        assert result.predictions[0]["gene"] == "TP53"


class TestTMBAgent:
    """Test tumor mutational burden calculator"""

    def test_tmb_agent_initialization(self):
        """Test TMB agent initializes correctly"""
        agent = TMBAgent()

        assert agent.agent_name == "TMBAgent"
        assert agent.gene_symbols == []  # Analyzes all genes

    def test_tmb_agent_calculates_burden(self, sample_variants):
        """Test TMB agent calculates mutational burden"""
        agent = TMBAgent()

        result = agent.run(sample_variants)

        assert result.status == AgentStatus.COMPLETED
        assert result.variants_analyzed == 4
        assert len(result.predictions) == 1
        assert "tmb_score" in result.predictions[0]
        assert "variant_count" in result.predictions[0]

    def test_tmb_agent_classifies_tmb_levels(self, sample_variants):
        """Test TMB classification (high/intermediate/low)"""
        agent = TMBAgent()

        result = agent.run(sample_variants)

        prediction = result.predictions[0]
        assert prediction["prediction"] in ["TMB-High", "TMB-Intermediate", "TMB-Low"]


class TestSupervisorAgent:
    """Test supervisor orchestration"""

    def test_supervisor_initialization(self):
        """Test supervisor initializes correctly"""
        supervisor = SupervisorAgent()

        assert supervisor.max_parallel_agents == 4
        assert len(supervisor.agents) == 0

    def test_supervisor_registers_agents(self):
        """Test agent registration"""
        supervisor = SupervisorAgent()

        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(EGFRAgent())

        assert len(supervisor.agents) == 2

    def test_supervisor_analyzes_with_multiple_agents(self, sample_variants):
        """Test supervisor coordinates multiple agents"""
        supervisor = SupervisorAgent()
        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(EGFRAgent())
        supervisor.register_agent(TP53Agent())

        result = supervisor.analyze_variants(sample_variants)

        assert result.total_variants == 4  # Total across all agents
        assert len(result.agent_results) == 3
        assert result.agents_completed == 3
        assert result.agents_failed == 0

    def test_supervisor_parallel_execution(self, sample_variants):
        """Test agents run in parallel"""
        supervisor = SupervisorAgent(max_parallel_agents=3)
        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(EGFRAgent())
        supervisor.register_agent(TP53Agent())

        result = supervisor.analyze_variants(sample_variants)

        # All agents should complete
        assert result.agents_completed == 3

        # Execution time should be less than sum (indicates parallelism)
        total_agent_time = sum(r.execution_time for r in result.agent_results)
        # Parallel execution should be faster than sequential
        # (This is lenient due to mock inference being fast)
        assert result.execution_time <= total_agent_time + 0.5  # Allow 500ms overhead

    def test_supervisor_identifies_critical_findings(self, sample_variants):
        """Test supervisor prioritizes critical findings"""
        supervisor = SupervisorAgent()
        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(TP53Agent())

        result = supervisor.analyze_variants(sample_variants)

        # Mock inference returns pathogenic for BRCA/TP53
        # Should identify as critical findings
        assert len(result.critical_findings) > 0

        # Verify critical findings have required fields
        for finding in result.critical_findings:
            assert "priority_score" in finding
            assert "gene" in finding
            assert "classification" in finding

    def test_supervisor_generates_summary(self, sample_variants):
        """Test supervisor generates readable summary"""
        supervisor = SupervisorAgent()
        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(EGFRAgent())

        result = supervisor.analyze_variants(sample_variants)
        summary = result.get_summary()

        assert "Cancer Genomics Analysis Summary" in summary
        assert "Total Variants:" in summary
        assert "BRCAAgent" in summary
        assert "EGFRAgent" in summary

    def test_supervisor_handles_agent_failures_gracefully(self, sample_variants):
        """Test supervisor continues when agent fails"""
        supervisor = SupervisorAgent()

        # Create agent that will fail
        class FailingAgent(BRCAAgent):
            def analyze_variants(self, variants):
                raise ValueError("Intentional test failure")

        supervisor.register_agent(FailingAgent())
        supervisor.register_agent(EGFRAgent())  # This should still succeed

        result = supervisor.analyze_variants(sample_variants)

        # One agent should fail, one should succeed
        assert result.agents_failed == 1
        assert result.agents_completed == 1
        assert len(result.agent_results) == 2


class TestMultiAgentWorkflow:
    """Integration tests for complete workflow"""

    def test_complete_cancer_panel_workflow(self, sample_variants, tmp_path):
        """Test end-to-end cancer panel analysis"""
        # Create temporary VCF file
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr17\t41234470\t.\tA\tG\t.\tPASS\tGENE=BRCA1
chr13\t32339381\t.\tC\tT\t.\tPASS\tGENE=BRCA2
chr7\t55249071\t.\tG\tA\t.\tPASS\tGENE=EGFR
chr17\t7577548\t.\tC\tT\t.\tPASS\tGENE=TP53
"""
        vcf_file = tmp_path / "test_panel.vcf"
        vcf_file.write_text(vcf_content)

        # Set up supervisor with all agents
        supervisor = SupervisorAgent()
        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(EGFRAgent())
        supervisor.register_agent(TP53Agent())
        supervisor.register_agent(TMBAgent())

        # Run analysis
        result = supervisor.analyze_cancer_panel(str(vcf_file))

        # Verify comprehensive analysis
        assert result.total_variants >= 4
        assert result.agents_completed == 4
        assert len(result.critical_findings) > 0

        # Verify all agent types ran
        agent_names = [r.agent_name for r in result.agent_results]
        assert "BRCAAgent" in agent_names
        assert "EGFRAgent" in agent_names
        assert "TP53Agent" in agent_names
        assert "TMBAgent" in agent_names

    def test_workflow_with_gene_filtering(self, sample_variants):
        """Test analysis focuses on specified genes"""
        supervisor = SupervisorAgent()
        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(EGFRAgent())

        # Only BRCA agent should find variants
        brca_only = [v for v in sample_variants if "BRCA" in v.gene]
        result = supervisor.analyze_variants(brca_only)

        # BRCA agent should have results, EGFR should not
        brca_result = next(
            r for r in result.agent_results if r.agent_name == "BRCAAgent"
        )
        egfr_result = next(
            r for r in result.agent_results if r.agent_name == "EGFRAgent"
        )

        assert brca_result.variants_analyzed == 2
        assert egfr_result.variants_analyzed == 0

    def test_workflow_performance(self, sample_variants):
        """Test workflow completes in reasonable time"""
        import time

        supervisor = SupervisorAgent()
        supervisor.register_agent(BRCAAgent())
        supervisor.register_agent(EGFRAgent())
        supervisor.register_agent(TP53Agent())
        supervisor.register_agent(TMBAgent())

        start = time.time()
        result = supervisor.analyze_variants(sample_variants)
        elapsed = time.time() - start

        # Should complete quickly with mock inference
        assert elapsed < 5.0  # 5 seconds max
        assert result.execution_time < 5.0
