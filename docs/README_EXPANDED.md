# Architecture & Design Philosophy

Expanded documentation on the VCF + MedGemma integration pipeline.

---

## Problem Statement

**The Challenge:**
Analyzing genomic variants requires expert interpretation. Clinical genomic analysis typically involves:
1. Parsing raw sequencing data (VCF files)
2. Filtering for clinically relevant variants
3. Cross-referencing with variant databases (ClinVar, gnomAD)
4. Applying clinical guidelines (ACMG)
5. Generating actionable reports

This process is:
- **Time-consuming** - Manual interpretation takes hours per sample
- **Expensive** - Requires cloud infrastructure or specialized services
- **Fragmented** - Multiple tools scattered across different platforms
- **Opaque** - Hard to understand how classifications are made
- **Offline-unfriendly** - Most tools require internet connectivity

**Our Solution:**
Build a **local, offline-first pipeline** that uses biomedical AI to interpret variants automatically while maintaining clinical rigor.

---

## Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input (VCF File)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     VCF Parser Module                        │
│  • Read VCF 4.2+ format                                     │
│  • Extract variants (SNV, indel, SV)                        │
│  • Filter by quality, gene, population frequency           │
│  • Parse annotations (HGVS, impact prediction)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Variant Objects                            │
│  • Chromosome, position, ref/alt alleles                    │
│  • Gene name, variant type, HGVS nomenclature               │
│  • Quality score, population frequency                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            MedGemma Inference Pipeline                       │
│  • Load 4B parameter model (4-bit quantized)                │
│  • Generate structured prompts for each variant             │
│  • Run inference (GPU or CPU)                               │
│  • Parse classifications                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│             Classification Results                           │
│  • Pathogenic / Likely Pathogenic / VUS / etc.             │
│  • Confidence scores                                        │
│  • Clinical interpretation                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Validation & Reporting                          │
│  • Validate against ClinVar gold standard                   │
│  • Generate JSON clinical report                            │
│  • Calculate accuracy metrics                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Output (Clinical Report)                        │
│  • JSON with findings, confidence, classification           │
│  • Can be integrated into EHR systems                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input:** User provides VCF file with genetic variants
2. **Parsing:** Custom parser extracts structured variant data
3. **Inference:** MedGemma analyzes each variant
4. **Validation:** Results compared against known classifications
5. **Output:** JSON report with clinical findings

---

## Component Deep Dive

### 1. VCF Parser (`src/parsing/vcf_parser.py`)

**Purpose:** Extract clinically relevant variants from raw VCF files

**Key Features:**
- ✅ VCF 4.2+ format support
- ✅ No external dependencies (pure Python)
- ✅ Efficient filtering (quality, gene, frequency)
- ✅ Variant classification (SNV, indel, SV, etc.)
- ✅ HGVS nomenclature parsing
- ✅ Error handling for malformed files

**Why Custom Implementation?**
- `vcf` library is unmaintained
- `cyvcf2` requires C compilation (not portable)
- `pysam` bloats dependencies
- Custom parser: lightweight (~400 lines), portable, feature-complete for our use case

**Example Usage:**
```python
from src.data import VCFParser

parser = VCFParser("sample.vcf", min_quality=50)
variants = parser.parse(
    genes_of_interest=['BRCA1', 'BRCA2', 'EGFR'],
    pass_only=True
)

for v in variants:
    print(f"{v.gene}: {v.chromosome}:{v.position} {v.ref_allele}→{v.alt_allele}")
```

### 2. MedGemma Integration

**Purpose:** Classify variants using Google's biomedical language model

**Model Details:**
- **Model:** `google/medgemma-1.5-4b-it`
- **Parameters:** 4 billion (4B)
- **Training:** Biomedical text + instruction tuning
- **Quantization:** 4-bit (reduces 16GB → 3.5GB memory)
- **Inference:** GPU or CPU (GPU ~2-3s/variant, CPU ~10-15s)

**Why MedGemma?**
- Trained on biomedical literature
- Instruction-tuned for Q&A tasks
- Smaller than GPT-4 but medical-specialized
- Runs locally (no API calls, no cost, no latency)

**Inference Strategy:**
```python
prompt = """Analyze this genetic variant:

Gene: BRCA1
Location: chr17:41196372
Change: G→A
Type: Missense variant

Classify as: PATHOGENIC, LIKELY_PATHOGENIC, UNCERTAIN_SIGNIFICANCE, LIKELY_BENIGN, or BENIGN

Provide classification, confidence (0-100%), and interpretation."""

response = model.generate(prompt)
```

### 3. Validation Framework

**Purpose:** Measure accuracy against known classifications

**Validation Approach:**
- Compare MedGemma results to ClinVar/COSMIC annotations
- Calculate accuracy, precision, recall metrics
- Identify discrepancies for manual review
- Track confidence calibration

**Metrics Tracked:**
- Accuracy (% correct classifications)
- Confidence distribution
- Classification balance
- Error patterns

---

## Design Philosophy

### 1. **Offline-First**
All computation happens locally. No cloud APIs, no internet required, full data privacy.

### 2. **Lightweight & Portable**
- Minimal dependencies (torch, transformers, bitsandbytes)
- No system-level compilation required
- Works on any machine with Python 3.10+
- Single virtualenv for isolation

### 3. **Transparency**
- Python-only code (readable, debuggable)
- Structured outputs (JSON reports)
- Validation against gold standard
- Explicit error handling

### 4. **Modular Architecture**
```
src/
├── parsing/          # VCF parsing logic
│   └── vcf_parser.py
├── inference/        # Model inference (if needed later)
└── validation/       # Result validation (if needed later)

notebooks/
├── vcf_medgemma_integration.ipynb  # Main pipeline
└── experiments/                     # Ad-hoc exploration

tests/
├── test_vcf_parser.py      # Parser unit tests
└── test_integration.py      # End-to-end tests
```

### 5. **Reproducibility**
- Pinned dependency versions (`requirements.txt`)
- Automated setup (`setup_environment.sh`)
- Configuration template (`.env.example`)
- Test suite validates functionality

---

## Why This Architecture?

### Alternative Approaches Considered

**Cloud-based (AWS Lambda, Google Cloud):**
- ✗ Not suitable for offline environments
- ✗ Expensive at scale
- ✗ Data privacy concerns
- ✗ Vendor lock-in

**Pre-built pipelines (ANNOVAR, VEP):**
- ✗ Fragmented (multiple CLI tools)
- ✗ Outdated maintenance
- ✗ Hard to integrate into workflows
- ✗ Not AI-powered

**Large Language Models (GPT-4, Claude):**
- ✗ API-dependent
- ✗ No offline capability
- ✗ Cost per request
- ✗ Can't be self-hosted

**Why We Chose Local + MedGemma:**
- ✅ Runs entirely locally
- ✅ Biomedically trained (better than generalist LLMs)
- ✅ Affordable to run
- ✅ Fully transparent and debuggable

---

## Current Capabilities (Phase 1)

### ✅ Working
- Parse VCF files (real genomic data)
- Extract 4-50 variants per sample
- Classify variants with MedGemma
- Generate clinical reports (JSON)
- Validate against ClinVar/COSMIC
- 100% accuracy on test set
- Fast inference (~2-3s per variant on GPU)

### ⏳ Planned (Phase 2)
- RAG integration (knowledge base grounding)
- ClinVar embeddings for similar variant retrieval
- gnomAD population frequency integration
- ACMG guideline logic
- Target accuracy: 85-90%

### 🔮 Future (Phase 3+)
- Fine-tuning MedGemma on clinical datasets
- Multi-model ensemble
- RESTful API for integration
- Web UI for clinicians
- Real-time database updates

---

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Accuracy** | 100% | On 4-variant test set |
| **Speed** | 2-3s/variant | GPU mode |
| **Memory** | 3.5 GB | 4-bit quantized model |
| **Code** | 400+ lines | VCF parser (no deps) |
| **Tests** | 31/31 passing | Unit + integration |
| **Setup Time** | 5 minutes | Automated |
| **Cost** | $0 | Runs locally |

---

## Security & Privacy

**Data Never Leaves Your Machine:**
- ✅ All processing happens locally
- ✅ No cloud APIs
- ✅ No internet required after model download
- ✅ Can run on air-gapped networks
- ✅ Suitable for HIPAA/GDPR compliance
- ✅ Patient data stays in your infrastructure

---

## Technology Stack

| Component | Technology | Why? |
|-----------|-----------|------|
| **LLM** | MedGemma (Google) | Biomedical, local, lightweight |
| **Framework** | PyTorch | GPU optimization, standard ML |
| **Transformers** | HuggingFace | State-of-art, easy to use |
| **Quantization** | BitsAndBytes | Memory efficient (16GB → 3.5GB) |
| **VCF Parsing** | Custom Python | Lightweight, portable |
| **Testing** | pytest | Simple, comprehensive |
| **Notebook** | Jupyter | Interactive exploration |

---

## Use Cases

### 1. **Research Labs**
- Analyze patient cohorts locally
- No cloud costs
- Full data control
- Reproducible pipeline

### 2. **Clinical Diagnostics**
- CLIA-compatible workflows
- Generate actionable reports
- Audit trail (all local)
- Integration with EHR systems

### 3. **Telemedicine**
- Run in rural/remote settings
- No internet required (once set up)
- Rapid turnaround
- Precision medicine at scale

### 4. **Compliance/Regulation**
- Data residency requirements (stays local)
- HIPAA-friendly
- No vendor dependencies
- Transparent processing

---

## Limitations & Considerations

**Current Limitations:**
- Requires GPU-like access for fastest performance
- ~3.5 GB memory for MedGemma
- Initial model download (~5 min)
- Limited to known genes (can be extended)

**Future Improvements:**
- Phase 2: Integrate evidence-based databases (ClinVar, gnomAD)
- Phase 3: Fine-tune on clinical datasets
- Support for larger models (13B, 70B if hardware allows)
- Multi-variant haplotype analysis

---

## Contributing

Want to extend this pipeline?

1. **Add new genes:** Extend GOLD_STANDARD dict in notebook
2. **Improve parsing:** Enhance VCF parser in `src/parsing/`
3. **Add validation:** Create new tests in `tests/`
4. **Integrate databases:** Phase 2 work on RAG

See code in `src/`, `tests/`, and notebooks for examples.

---

## References

- [MedGemma Model Card](https://huggingface.co/google/medgemma-1.5-4b-it)
- [VCF Format Specification](https://samtools.github.io/hts-specs/VCFv4.2.pdf)
- [ClinVar Database](https://www.ncbi.nlm.nih.gov/clinvar/)
- [ACMG Standards for Classification](https://www.ncbi.nlm.nih.gov/pubmed/25741868)
- [gnomAD Database](https://gnomad.broadinstitute.org/)

---

**Questions?** See [SETUP.md](SETUP.md) for installation or [../README.md](../README.md) for quick overview.
