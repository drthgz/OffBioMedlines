"""
Medical Knowledge RAG (Retrieval-Augmented Generation)

Provides medical knowledge retrieval for agent contextual reasoning.
Currently supports:
- ClinVar variant database
- Basic medical literature context

Future enhancements:
- COSMIC mutation database
- PubMed literature search
- Drug-gene interaction database
- Clinical guidelines repository
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MedicalKnowledgeRAG:
    """
    Simple RAG interface for medical knowledge retrieval

    Provides contextual medical information to agents for informed
    variant interpretation.
    """

    def __init__(self, clinvar_data_path: Optional[str] = None):
        """
        Initialize medical knowledge RAG

        Args:
            clinvar_data_path: Optional path to ClinVar database
        """
        self.clinvar_data_path = clinvar_data_path
        self.logger = logging.getLogger(__name__)

        # Load ClinVar gold standards if available
        self.clinvar_db = {}
        if clinvar_data_path:
            self._load_clinvar_data(clinvar_data_path)

    def retrieve(self, query: str, top_k: int = 3) -> str:
        """
        Retrieve relevant medical knowledge for query

        Args:
            query: Search query (e.g., "BRCA1 c.185delAG clinical significance")
            top_k: Number of results to return

        Returns:
            Formatted context string
        """
        # Extract gene from query
        gene = self._extract_gene_from_query(query)

        # Search ClinVar database
        if gene and gene in self.clinvar_db:
            return self._format_clinvar_context(gene, self.clinvar_db[gene])

        # Fallback to general knowledge
        return self._get_general_context(gene)

    def _load_clinvar_data(self, data_path: str):
        """Load ClinVar gold standard data"""
        try:
            import json

            with open(data_path, "r") as f:
                data = json.load(f)

            # Index by gene
            for entry in data:
                gene = entry.get("gene", "")
                if gene:
                    if gene not in self.clinvar_db:
                        self.clinvar_db[gene] = []
                    self.clinvar_db[gene].append(entry)

            self.logger.info(f"Loaded ClinVar data for {len(self.clinvar_db)} genes")

        except Exception as e:
            self.logger.warning(f"Could not load ClinVar data: {str(e)}")

    def _extract_gene_from_query(self, query: str) -> Optional[str]:
        """Extract gene symbol from query"""
        # Common cancer genes
        genes = ["BRCA1", "BRCA2", "TP53", "EGFR", "KRAS", "PTEN", "APC", "MLH1"]

        query_upper = query.upper()
        for gene in genes:
            if gene in query_upper:
                return gene

        return None

    def _format_clinvar_context(self, gene: str, entries: List[Dict[str, Any]]) -> str:
        """Format ClinVar entries as context"""
        context_parts = [f"ClinVar Knowledge for {gene}:"]

        for entry in entries[:3]:  # Top 3 entries
            variant = entry.get("variant_id", "unknown")
            classification = entry.get("clinical_significance", "unknown")
            context_parts.append(f"- Variant {variant}: {classification}")

        return "\n".join(context_parts)

    def _get_general_context(self, gene: Optional[str]) -> str:
        """Provide general medical context for gene"""
        gene_contexts = {
            "BRCA1": (
                "BRCA1 is a tumor suppressor gene involved in DNA repair. "
                "Pathogenic variants confer high risk for hereditary breast and ovarian cancer "
                "(45-85% breast cancer risk, 10-40% ovarian cancer risk). "
                "Key considerations: Ashkenazi founder mutations, PARP inhibitor eligibility, "
                "family cascade screening."
            ),
            "BRCA2": (
                "BRCA2 is a tumor suppressor involved in homologous recombination DNA repair. "
                "Pathogenic variants increase breast cancer risk (40-84%) and ovarian cancer risk (11-27%). "
                "Also associated with prostate, pancreatic, and male breast cancer. "
                "PARP inhibitor eligible."
            ),
            "TP53": (
                "TP53 is the 'guardian of the genome' tumor suppressor. "
                "Most frequently mutated gene in human cancers. "
                "Germline pathogenic variants cause Li-Fraumeni syndrome (multi-cancer predisposition). "
                "Somatic mutations predict poor prognosis. "
                "Hotspots: R175H, R248Q, R273H."
            ),
            "EGFR": (
                "EGFR is a receptor tyrosine kinase. "
                "Activating mutations common in non-small cell lung cancer (NSCLC). "
                "Sensitizing mutations (exon 19 del, L858R) predict TKI response. "
                "Resistance mutations (T790M) guide therapy selection. "
                "FDA-approved companion diagnostics available."
            ),
            "KRAS": (
                "KRAS is an oncogene encoding a GTPase signal transduction protein. "
                "Activating mutations common in colorectal, lung, and pancreatic cancers. "
                "G12C mutation targetable with sotorasib/adagrasib. "
                "Generally predict resistance to anti-EGFR therapy in colorectal cancer."
            ),
        }

        if gene and gene in gene_contexts:
            return f"General Medical Context:\n{gene_contexts[gene]}"

        return "No specific medical context available."
