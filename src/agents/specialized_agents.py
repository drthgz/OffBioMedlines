"""
Specialized Gene Agents for Cancer Genomics

Each agent focuses on specific genes or biomarkers with domain expertise:
- BRCAAgent: BRCA1/BRCA2 hereditary cancer analysis
- EGFRAgent: EGFR mutation therapy selection
- TP53Agent: TP53 tumor suppressor analysis
- TMBAgent: Tumor mutational burden calculation
"""

from typing import List, Dict, Any, Optional, Callable
import re

from src.data.vcf_parser import Variant
from src.agents.base_agent import BaseAgent, AgentResult, AgentStatus


class BRCAAgent(BaseAgent):
    """
    BRCA1/BRCA2 Analysis Agent

    Specializes in hereditary breast and ovarian cancer syndrome analysis.
    Focuses on:
    - Pathogenic variant identification
    - Hereditary cancer risk assessment
    - Family screening recommendations
    - Risk-reducing intervention guidance
    """

    def __init__(
        self,
        model_inference_fn: Optional[Callable] = None,
        rag_retriever: Optional[Any] = None,
    ):
        super().__init__(
            agent_name="BRCAAgent",
            gene_symbols=["BRCA1", "BRCA2"],
            model_inference_fn=model_inference_fn,
            rag_retriever=rag_retriever,
            confidence_threshold=0.75,
        )

    def analyze_variants(self, variants: List[Variant]) -> AgentResult:
        """Analyze BRCA variants with hereditary cancer context"""
        predictions = []
        clinical_insights = []

        for variant in variants:
            # Get medical context from RAG
            rag_context = self._get_rag_context(variant)

            # Generate specialized prompt
            prompt = self.get_specialized_prompt(variant)
            if rag_context:
                prompt += f"\n\nClinical Context:\n{rag_context}"

            # Run inference
            response = self.model_inference_fn(prompt)

            # Parse response
            confidence = self._extract_confidence(response)
            prediction_class = self._extract_classification(response)

            prediction = {
                "gene": variant.gene,
                "chromosome": variant.chromosome,
                "position": variant.position,
                "ref": variant.ref_allele,
                "alt": variant.alt_allele,
                "prediction": prediction_class,
                "confidence": confidence,
                "reasoning": response,
                "agent": self.agent_name,
            }
            predictions.append(prediction)

            # Generate clinical insights for pathogenic variants
            if (
                "pathogenic" in prediction_class.lower()
                and "benign" not in prediction_class.lower()
            ):
                insight = self._generate_brca_insight(
                    variant, prediction_class, confidence
                )
                clinical_insights.append(insight)

        # Add hereditary cancer recommendations
        if any("pathogenic" in p["prediction"].lower() for p in predictions):
            clinical_insights.append(
                "⚠️ Pathogenic BRCA variant detected. Consider: "
                "(1) Family cascade screening, (2) Enhanced surveillance protocols, "
                "(3) Risk-reducing strategies (RRSO/RRBM), (4) PARP inhibitor eligibility"
            )

        return AgentResult(
            agent_name=self.agent_name,
            gene_symbol="BRCA1/BRCA2",
            variants_analyzed=len(variants),
            predictions=predictions,
            clinical_insights=clinical_insights,
            execution_time=0.0,  # Set by run() method
            status=AgentStatus.RUNNING,
        )

    def get_specialized_prompt(self, variant: Variant) -> str:
        """Generate BRCA-specific analysis prompt"""
        prompt = f"""Analyze this BRCA variant for hereditary cancer risk:

Gene: {variant.gene}
Variant: {variant.chromosome}:{variant.position} {variant.ref_allele}>{variant.alt_allele}
Type: {variant.variant_type.value if variant.variant_type else "Unknown"}

Consider:
1. Hereditary breast/ovarian cancer syndrome (HBOC) implications
2. Penetrance and cancer risk (breast: 45-85%, ovarian: 10-40%)
3. Founder mutations (Ashkenazi Jewish: 185delAG, 5382insC, 6174delT)
4. Functional impact on DNA repair (homologous recombination)
5. PARP inhibitor therapy eligibility
6. Family screening recommendations

Provide classification (Pathogenic/Likely Pathogenic/VUS/Likely Benign/Benign) with confidence and reasoning."""
        return prompt

    def validate_results(self, predictions: List[Dict[str, Any]]) -> bool:
        """Validate BRCA predictions"""
        if not predictions:
            return False

        # Check all predictions have required fields
        required_fields = ["gene", "prediction", "confidence"]
        for pred in predictions:
            if not all(field in pred for field in required_fields):
                return False

            # Validate confidence range
            if not 0.0 <= pred["confidence"] <= 1.0:
                return False

        return True

    def _generate_brca_insight(
        self, variant: Variant, classification: str, confidence: float
    ) -> str:
        """Generate clinical insight for BRCA variant"""
        risk_level = "HIGH" if variant.gene == "BRCA1" else "MODERATE-HIGH"
        return (
            f"🔴 {variant.gene} {classification} variant at {variant.chromosome}:{variant.position} "
            f"(confidence: {confidence:.0%}). {risk_level} risk for breast/ovarian cancer. "
            f"Recommend genetic counseling and enhanced surveillance."
        )

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence score from model response"""
        # Try percentage format
        match = re.search(r"(\d+)%\s+confidence", response.lower())
        if match:
            return float(match.group(1)) / 100.0

        # Try decimal format
        match = re.search(r"confidence[:\s]+(\d+\.?\d*)", response.lower())
        if match:
            val = float(match.group(1))
            return val if val <= 1.0 else val / 100.0

        # Default based on keywords
        if "high confidence" in response.lower():
            return 0.9
        elif "moderate confidence" in response.lower():
            return 0.7
        else:
            return 0.5

    def _extract_classification(self, response: str) -> str:
        """Extract variant classification from response"""
        response_lower = response.lower()

        # Check in order of specificity
        if "likely pathogenic" in response_lower:
            return "Likely Pathogenic"
        elif "pathogenic" in response_lower and "benign" not in response_lower:
            return "Pathogenic"
        elif "likely benign" in response_lower:
            return "Likely Benign"
        elif "benign" in response_lower:
            return "Benign"
        elif "vus" in response_lower or "uncertain significance" in response_lower:
            return "VUS"
        else:
            return "Unknown"


class EGFRAgent(BaseAgent):
    """
    EGFR Mutation Analysis Agent

    Specializes in EGFR mutation detection for lung cancer therapy selection.
    Focuses on:
    - Sensitizing mutations (exon 19 del, L858R)
    - Resistance mutations (T790M, C797S)
    - Therapy recommendations (TKI selection)
    - Drug resistance monitoring
    """

    def __init__(
        self,
        model_inference_fn: Optional[Callable] = None,
        rag_retriever: Optional[Any] = None,
    ):
        super().__init__(
            agent_name="EGFRAgent",
            gene_symbols=["EGFR"],
            model_inference_fn=model_inference_fn,
            rag_retriever=rag_retriever,
            confidence_threshold=0.75,
        )

        # Known therapeutic EGFR mutations
        self.sensitizing_mutations = ["L858R", "exon19del", "G719X", "L861Q"]
        self.resistance_mutations = ["T790M", "C797S"]

    def analyze_variants(self, variants: List[Variant]) -> AgentResult:
        """Analyze EGFR variants for therapy implications"""
        predictions = []
        clinical_insights = []

        for variant in variants:
            # Get medical context
            rag_context = self._get_rag_context(variant)

            # Generate specialized prompt
            prompt = self.get_specialized_prompt(variant)
            if rag_context:
                prompt += f"\n\nClinical Context:\n{rag_context}"

            # Run inference
            response = self.model_inference_fn(prompt)

            # Parse response
            confidence = self._extract_confidence(response)
            prediction_class = self._extract_classification(response)

            prediction = {
                "gene": variant.gene,
                "chromosome": variant.chromosome,
                "position": variant.position,
                "ref": variant.ref_allele,
                "alt": variant.alt_allele,
                "prediction": prediction_class,
                "confidence": confidence,
                "reasoning": response,
                "agent": self.agent_name,
                "therapy_relevant": self._is_therapy_relevant(variant, response),
            }
            predictions.append(prediction)

            # Generate therapy insights
            if prediction["therapy_relevant"]:
                insight = self._generate_therapy_insight(variant, response)
                clinical_insights.append(insight)

        return AgentResult(
            agent_name=self.agent_name,
            gene_symbol="EGFR",
            variants_analyzed=len(variants),
            predictions=predictions,
            clinical_insights=clinical_insights,
            execution_time=0.0,
            status=AgentStatus.RUNNING,
        )

    def get_specialized_prompt(self, variant: Variant) -> str:
        """Generate EGFR therapy-focused prompt"""
        prompt = f"""Analyze this EGFR variant for lung cancer therapy implications:

Gene: {variant.gene}
Variant: {variant.chromosome}:{variant.position} {variant.ref_allele}>{variant.alt_allele}
Type: {variant.variant_type.value if variant.variant_type else "Unknown"}

Consider:
1. TKI-sensitizing mutations (exon 19 deletions, L858R, G719X, L861Q)
2. TKI-resistance mutations (T790M, C797S)
3. First-line therapy selection:
   - 1st gen TKIs: Erlotinib, Gefitinib
   - 2nd gen TKIs: Afatinib
   - 3rd gen TKIs: Osimertinib (esp. for T790M)
4. Response prediction and resistance mechanisms
5. Companion diagnostic implications

Provide classification with therapy recommendations and confidence."""
        return prompt

    def validate_results(self, predictions: List[Dict[str, Any]]) -> bool:
        """Validate EGFR predictions"""
        if not predictions:
            return False

        required_fields = ["gene", "prediction", "confidence", "therapy_relevant"]
        for pred in predictions:
            if not all(field in pred for field in required_fields):
                return False
            if not 0.0 <= pred["confidence"] <= 1.0:
                return False

        return True

    def _is_therapy_relevant(self, variant: Variant, response: str) -> bool:
        """Determine if variant has therapy implications"""
        response_lower = response.lower()
        variant_str = f"{variant.ref_allele}{variant.position}{variant.alt_allele}"

        # Check known mutations
        for mutation in self.sensitizing_mutations + self.resistance_mutations:
            if (
                mutation.lower() in response_lower
                or mutation.lower() in variant_str.lower()
            ):
                return True

        # Check therapy keywords
        therapy_keywords = [
            "tki",
            "tyrosine kinase",
            "erlotinib",
            "gefitinib",
            "osimertinib",
            "afatinib",
            "therapy",
            "treatment",
        ]
        return any(keyword in response_lower for keyword in therapy_keywords)

    def _generate_therapy_insight(self, variant: Variant, response: str) -> str:
        """Generate therapy recommendation insight"""
        if "T790M" in response or "t790m" in response.lower():
            return (
                f"🔵 EGFR T790M resistance mutation detected at {variant.position}. "
                "Recommend 3rd generation TKI (Osimertinib) as first-line or after 1st/2nd gen TKI failure."
            )
        elif any(m.lower() in response.lower() for m in self.sensitizing_mutations):
            return (
                f"🟢 EGFR sensitizing mutation at {variant.position}. "
                "Patient eligible for EGFR TKI therapy. Consider Osimertinib (first-line) "
                "or Erlotinib/Gefitinib/Afatinib."
            )
        else:
            return (
                f"⚠️ EGFR variant at {variant.position} detected. "
                "Evaluate therapy relevance based on functional studies and clinical guidelines."
            )

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence from response"""
        match = re.search(r"(\d+)%\s+confidence", response.lower())
        if match:
            return float(match.group(1)) / 100.0
        match = re.search(r"confidence[:\s]+(\d+\.?\d*)", response.lower())
        if match:
            val = float(match.group(1))
            return val if val <= 1.0 else val / 100.0
        return 0.8  # Default for EGFR (high clinical relevance)

    def _extract_classification(self, response: str) -> str:
        """Extract classification from response"""
        response_lower = response.lower()
        if "likely pathogenic" in response_lower:
            return "Likely Pathogenic"
        elif "pathogenic" in response_lower:
            return "Pathogenic"
        elif "likely benign" in response_lower:
            return "Likely Benign"
        elif "benign" in response_lower:
            return "Benign"
        else:
            return "VUS"


class TP53Agent(BaseAgent):
    """
    TP53 Tumor Suppressor Analysis Agent

    Specializes in TP53 mutation analysis for cancer genomics.
    Focuses on:
    - Tumor suppressor function loss
    - Cancer predisposition syndromes (Li-Fraumeni)
    - Hotspot mutations (R175H, R248Q, R273H)
    - Prognostic implications
    """

    def __init__(
        self,
        model_inference_fn: Optional[Callable] = None,
        rag_retriever: Optional[Any] = None,
    ):
        super().__init__(
            agent_name="TP53Agent",
            gene_symbols=["TP53"],
            model_inference_fn=model_inference_fn,
            rag_retriever=rag_retriever,
            confidence_threshold=0.75,
        )

        # Known TP53 hotspots
        self.hotspot_mutations = ["R175H", "R248Q", "R273H", "R248W", "R282W"]

    def analyze_variants(self, variants: List[Variant]) -> AgentResult:
        """Analyze TP53 variants"""
        predictions = []
        clinical_insights = []

        for variant in variants:
            rag_context = self._get_rag_context(variant)
            prompt = self.get_specialized_prompt(variant)
            if rag_context:
                prompt += f"\n\nClinical Context:\n{rag_context}"

            response = self.model_inference_fn(prompt)
            confidence = self._extract_confidence(response)
            prediction_class = self._extract_classification(response)

            prediction = {
                "gene": variant.gene,
                "chromosome": variant.chromosome,
                "position": variant.position,
                "ref": variant.ref_allele,
                "alt": variant.alt_allele,
                "prediction": prediction_class,
                "confidence": confidence,
                "reasoning": response,
                "agent": self.agent_name,
                "is_hotspot": self._is_hotspot(variant, response),
            }
            predictions.append(prediction)

            if "pathogenic" in prediction_class.lower():
                insight = self._generate_tp53_insight(variant, prediction)
                clinical_insights.append(insight)

        return AgentResult(
            agent_name=self.agent_name,
            gene_symbol="TP53",
            variants_analyzed=len(variants),
            predictions=predictions,
            clinical_insights=clinical_insights,
            execution_time=0.0,
            status=AgentStatus.RUNNING,
        )

    def get_specialized_prompt(self, variant: Variant) -> str:
        """Generate TP53-specific prompt"""
        return f"""Analyze this TP53 tumor suppressor variant:

Gene: {variant.gene}
Variant: {variant.chromosome}:{variant.position} {variant.ref_allele}>{variant.alt_allele}

Consider:
1. Loss of tumor suppressor function (DNA binding, transcriptional activation)
2. Hotspot mutations in DNA-binding domain (R175, R248, R273, R282)
3. Li-Fraumeni syndrome (germline pathogenic variants)
4. Prognostic impact (poor prognosis in many cancers)
5. Therapeutic implications (limited targeted options)

Provide classification with clinical significance."""
        return prompt

    def validate_results(self, predictions: List[Dict[str, Any]]) -> bool:
        """Validate TP53 predictions"""
        if not predictions:
            return False
        for pred in predictions:
            if not all(f in pred for f in ["gene", "prediction", "confidence"]):
                return False
        return True

    def _is_hotspot(self, variant: Variant, response: str) -> bool:
        """Check if variant is known hotspot"""
        variant_str = f"{variant.ref_allele}{variant.position}{variant.alt_allele}"
        return any(
            hotspot.lower() in response.lower()
            or hotspot.lower() in variant_str.lower()
            for hotspot in self.hotspot_mutations
        )

    def _generate_tp53_insight(
        self, variant: Variant, prediction: Dict[str, Any]
    ) -> str:
        """Generate TP53 clinical insight"""
        if prediction.get("is_hotspot"):
            return (
                f"🔴 TP53 hotspot mutation at {variant.position}. "
                "Loss of tumor suppressor function. Poor prognostic indicator. "
                "Consider Li-Fraumeni syndrome if germline."
            )
        else:
            return (
                f"⚠️ TP53 pathogenic variant at {variant.position}. "
                "Evaluate functional impact and germline status."
            )

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence"""
        match = re.search(r"(\d+)%", response)
        return float(match.group(1)) / 100.0 if match else 0.9

    def _extract_classification(self, response: str) -> str:
        """Extract classification"""
        response_lower = response.lower()
        if "likely pathogenic" in response_lower:
            return "Likely Pathogenic"
        elif "pathogenic" in response_lower:
            return "Pathogenic"
        elif "benign" in response_lower:
            return "Benign"
        else:
            return "VUS"


class TMBAgent(BaseAgent):
    """
    Tumor Mutational Burden (TMB) Calculator Agent

    Calculates TMB score for immunotherapy eligibility assessment.
    """

    def __init__(
        self,
        model_inference_fn: Optional[Callable] = None,
        rag_retriever: Optional[Any] = None,
    ):
        super().__init__(
            agent_name="TMBAgent",
            gene_symbols=[],  # Analyzes all genes
            model_inference_fn=model_inference_fn,
            rag_retriever=rag_retriever,
            confidence_threshold=0.7,
        )

    def analyze_variants(self, variants: List[Variant]) -> AgentResult:
        """Calculate TMB from variants"""
        # Simple TMB calculation: count non-synonymous mutations
        non_syn_count = sum(
            1
            for v in variants
            if v.variant_type and v.variant_type.value != "synonymous"
        )

        # TMB score (mutations per megabase, assume ~30Mb exome)
        tmb_score = non_syn_count / 30.0

        # Classify TMB
        if tmb_score >= 20:
            tmb_class = "TMB-High"
            insight = "🟢 TMB-High (≥20 mut/Mb). Strong candidate for immune checkpoint inhibitor therapy."
        elif tmb_score >= 10:
            tmb_class = "TMB-Intermediate"
            insight = "🟡 TMB-Intermediate (10-20 mut/Mb). Consider immunotherapy based on other factors."
        else:
            tmb_class = "TMB-Low"
            insight = "⚪ TMB-Low (<10 mut/Mb). Limited immunotherapy benefit expected."

        prediction = {
            "gene": "TMB_SCORE",
            "chromosome": "N/A",
            "position": 0,
            "ref": "",
            "alt": "",
            "prediction": tmb_class,
            "confidence": 0.95,
            "reasoning": f"Calculated from {non_syn_count} non-synonymous variants across ~30Mb",
            "agent": self.agent_name,
            "tmb_score": tmb_score,
            "variant_count": non_syn_count,
        }

        return AgentResult(
            agent_name=self.agent_name,
            gene_symbol="TMB",
            variants_analyzed=len(variants),
            predictions=[prediction],
            clinical_insights=[insight],
            execution_time=0.0,
            status=AgentStatus.RUNNING,
        )

    def get_specialized_prompt(self, variant: Variant) -> str:
        """TMB doesn't use individual variant prompts"""
        return ""

    def validate_results(self, predictions: List[Dict[str, Any]]) -> bool:
        """Validate TMB results"""
        return len(predictions) == 1 and "tmb_score" in predictions[0]

    def _filter_variants(self, variants: List[Variant]) -> List[Variant]:
        """TMB analyzes all variants"""
        return variants
