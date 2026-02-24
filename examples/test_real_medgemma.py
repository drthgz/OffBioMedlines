#!/usr/bin/env python3
"""
Test Real MedGemma Integration

Quick test script to verify MedGemma model loads and generates responses.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model.medgemma_inference import MedGemmaInference, create_inference_function
from src.agents import SupervisorAgent, BRCAAgent, EGFRAgent, TP53Agent
from src.data.vcf_parser import Variant, VariantType


def test_basic_inference():
    """Test basic MedGemma inference"""
    print("=" * 70)
    print("TEST 1: Basic MedGemma 4B Inference (bfloat16)")
    print("=" * 70)
    print()

    print("Loading MedGemma 4B model (this may take 30-60 seconds)...")
    inference = MedGemmaInference(
        model_path="/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma-1.5-4b-model",
        use_4bit=True,
        temperature=0.0,  # Use greedy decoding for stability
    )

    print("✓ Model loaded successfully")
    print()

    # Test prompt
    prompt = """Analyze this BRCA1 variant for clinical significance:

Gene: BRCA1
Variant: chr17:41234470 A>G (c.185A>G)
Type: Missense

Consider:
1. Hereditary breast/ovarian cancer syndrome implications
2. Pathogenicity prediction
3. Functional impact on DNA repair

Provide classification (Pathogenic/Likely Pathogenic/VUS/Likely Benign/Benign) with confidence percentage and brief reasoning."""

    print("Prompt:")
    print("-" * 70)
    print(prompt)
    print("-" * 70)
    print()

    print("Generating response...")
    response = inference.generate(prompt, max_new_tokens=256)

    print("\nMedGemma Response:")
    print("=" * 70)
    print(response)
    print("=" * 70)
    print()


def test_agent_with_real_model():
    """Test agent using real MedGemma"""
    print("=" * 70)
    print("TEST 2: BRCA Agent with Real MedGemma 4B")
    print("=" * 70)
    print()

    # Create inference function
    print("Creating inference function...")
    inference_fn = create_inference_function(
        model_path="/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma-1.5-4b-model",
        use_4bit=True,
    )

    # Create agent with real model
    print("Initializing BRCA agent with real MedGemma...")
    agent = BRCAAgent(model_inference_fn=inference_fn)

    # Test variant
    variant = Variant(
        chromosome="chr17",
        position=41234470,
        ref_allele="A",
        alt_allele="G",
        gene="BRCA1",
        variant_type=VariantType.MISSENSE,
        hgvs_nomenclature="NM_007294.3:c.185A>G",
    )

    print(f"Analyzing variant: {variant.gene} {variant.chromosome}:{variant.position}")
    print()

    # Run analysis
    result = agent.run([variant])

    print("Agent Results:")
    print("=" * 70)
    print(f"Status: {result.status.value}")
    print(f"Variants analyzed: {result.variants_analyzed}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print()

    if result.predictions:
        print("Predictions:")
        for pred in result.predictions:
            print(f"  • Gene: {pred['gene']}")
            print(f"    Classification: {pred['prediction']}")
            print(f"    Confidence: {pred['confidence']:.1%}")
            print(f"    Reasoning: {pred['reasoning'][:200]}...")
            print()

    if result.clinical_insights:
        print("Clinical Insights:")
        for insight in result.clinical_insights:
            print(f"  • {insight}")
        print()


def test_multi_agent_with_real_model():
    """Test multi-agent workflow with real MedGemma"""
    print("=" * 70)
    print("TEST 3: Multi-Agent Workflow with Real MedGemma")
    print("=" * 70)
    print()

    # Create inference function
    print("Loading MedGemma for multi-agent system...")
    inference_fn = create_inference_function(use_4bit=True)

    # Set up supervisor with specialized agents
    supervisor = SupervisorAgent(max_parallel_agents=3)

    print("Registering agents...")
    supervisor.register_agent(BRCAAgent(model_inference_fn=inference_fn))
    supervisor.register_agent(EGFRAgent(model_inference_fn=inference_fn))
    supervisor.register_agent(TP53Agent(model_inference_fn=inference_fn))

    print(f"✓ {len(supervisor.agents)} agents registered")
    print()

    # Test variants
    variants = [
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
            chromosome="chr7",
            position=55249071,
            ref_allele="G",
            alt_allele="A",
            gene="EGFR",
            variant_type=VariantType.MISSENSE,
            hgvs_nomenclature="NM_005228.5:c.2573G>A (L858R)",
        ),
        Variant(
            chromosome="chr17",
            position=7577548,
            ref_allele="C",
            alt_allele="T",
            gene="TP53",
            variant_type=VariantType.MISSENSE,
            hgvs_nomenclature="NM_000546.5:c.524C>T (R175H)",
        ),
    ]

    print(f"Analyzing {len(variants)} variants with real MedGemma...")
    print()

    # Run multi-agent analysis
    result = supervisor.analyze_variants(variants)

    print("Multi-Agent Results:")
    print("=" * 70)
    print(f"Total variants analyzed: {result.total_variants}")
    print(f"Agents completed: {result.agents_completed}/{len(result.agent_results)}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print()

    print("Agent Performance:")
    for agent_result in result.agent_results:
        status_icon = "✓" if agent_result.status.value == "completed" else "✗"
        print(
            f"{status_icon} {agent_result.agent_name}: {agent_result.variants_analyzed} variants, {agent_result.execution_time:.2f}s"
        )
    print()

    if result.critical_findings:
        print(f"Critical Findings: {len(result.critical_findings)}")
        for i, finding in enumerate(result.critical_findings[:3], 1):
            print(f"\n{i}. {finding['gene']}")
            print(f"   Classification: {finding['classification']}")
            print(f"   Confidence: {finding['confidence']:.1%}")
            print(f"   Priority Score: {finding['priority_score']}")

    print("\n" + "=" * 70)
    print("✓ All tests completed successfully")
    print("=" * 70)


def main():
    """Run all tests"""
    import argparse

    parser = argparse.ArgumentParser(description="Test real MedGemma integration")
    parser.add_argument(
        "--test",
        choices=["basic", "agent", "multi", "all"],
        default="all",
        help="Which test to run",
    )

    args = parser.parse_args()

    try:
        if args.test in ["basic", "all"]:
            test_basic_inference()
            print("\n")

        if args.test in ["agent", "all"]:
            test_agent_with_real_model()
            print("\n")

        if args.test in ["multi", "all"]:
            test_multi_agent_with_real_model()

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
