# Quick Start Guide - VCF + MedGemma Integration

**Get started in 5 minutes!**

---

## Prerequisites

- Python 3.10+
- NVIDIA GPU with 4GB+ VRAM (or CPU with patience)
- 8GB+ system RAM

---

## 1. Install Dependencies (2 minutes)

```bash
# Core packages
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers accelerate bitsandbytes
pip install pytest

# Verify installation
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
```

---

## 2. Run Tests (30 seconds)

```bash
cd /home/shiftmint/Documents/kaggle/medAi_google

# Run all tests
python -m pytest tests/ -v

# Expected output:
# ============================== 31 passed in 0.06s ==============================
```

✅ If all 31 tests pass, you're ready!

---

## 3. Parse Your First VCF (10 seconds)

```python
from src.parsing import parse_vcf

# Parse the test VCF
variants = parse_vcf(
    "data/test_samples/sample_001.vcf",
    genes=['BRCA1', 'BRCA2', 'TP53', 'EGFR'],
    min_quality=50,
    pass_only=True
)

print(f"✓ Extracted {len(variants)} variants")

for v in variants:
    print(f"{v.gene}: {v.variant_type.value} at {v.chromosome}:{v.position}")
```

**Expected Output:**
```
✓ Extracted 4 variants
BRCA1: frameshift at chr17:41196372
BRCA2: missense at chr13:32889611
EGFR: missense at chr7:55249071
TP53: missense at chr17:7577548
```

---

## 4. Run MedGemma Analysis (2 minutes)

### Option A: Jupyter Notebook (Recommended)
```bash
# Open the integration notebook
jupyter notebook notebooks/vcf_medgemma_integration.ipynb

# Or in VSCode
code notebooks/vcf_medgemma_integration.ipynb
```

Then **Run All Cells** (Kernel → Restart & Run All)

### Option B: Python Script
```python
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from src.parsing import parse_vcf

# 1. Parse VCF
print("📄 Parsing VCF...")
variants = parse_vcf(
    "data/test_samples/sample_001.vcf",
    genes=['BRCA1', 'BRCA2', 'TP53', 'EGFR'],
    pass_only=True
)
print(f"✓ Found {len(variants)} variants\n")

# 2. Load MedGemma
print("📥 Loading MedGemma...")
MODEL_NAME = "google/medgemma-1.5-4b-it"

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=quantization_config,
    device_map="auto"
)
print("✓ Model loaded\n")

# 3. Classify first variant (example)
print("🔬 Analyzing first variant...")
v = variants[0]

prompt = f"""Analyze this genetic variant:

Gene: {v.gene}
Type: {v.variant_type.value}
Location: {v.chromosome}:{v.position}
Change: {v.ref_allele} → {v.alt_allele}

Classify as: PATHOGENIC, LIKELY_PATHOGENIC, UNCERTAIN, LIKELY_BENIGN, or BENIGN.
Provide confidence (0-100%) and brief interpretation."""

formatted_prompt = f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"

inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.3)
response = tokenizer.decode(outputs[0], skip_special_tokens=True)

print(response)
```

---

## 5. View Results

**Expected Notebook Output:**
```
======================================================================
 MedGemma Analysis: VCF Sample 001
======================================================================

[1/4] BRCA1: chr17:41196372 G→A
   ✓ Classification: PATHOGENIC
   ✓ Confidence: 92.0%

[2/4] BRCA2: chr13:32889611 C→T
   ✓ Classification: LIKELY_PATHOGENIC
   ✓ Confidence: 85.0%

[3/4] EGFR: chr7:55249071 G→A
   ✓ Classification: PATHOGENIC
   ✓ Confidence: 90.0%

[4/4] TP53: chr17:7577548 C→T
   ✓ Classification: PATHOGENIC
   ✓ Confidence: 88.0%

======================================================================
✅ Analysis Complete - 4 findings
======================================================================

📊 Validation: 4/4 matches (100% accuracy vs ClinVar)
```

---

## Common Issues & Solutions

### Issue 1: CUDA Out of Memory
```python
# Use CPU (slower but works)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="cpu",
    torch_dtype=torch.float32
)
```

### Issue 2: Model Download Fails
```bash
# Set HuggingFace token
export HUGGINGFACE_TOKEN="your_token_here"

# Or create .env file
echo "HUGGINGFACE_TOKEN=your_token" > .env
```

See [`docs/HUGGINGFACE_SETUP.md`](HUGGINGFACE_SETUP.md) for token setup.

### Issue 3: Tests Fail
```bash
# Check project structure
ls -R src/ tests/ data/

# Re-run specific test
python -m pytest tests/test_vcf_parser.py::TestVCFParser::test_parse_vcf_with_filters -v
```

---

## What's Next?

### Analyze Your Own VCF
```python
from src.parsing import parse_vcf

# Your VCF file
variants = parse_vcf(
    "/path/to/your_sample.vcf",
    genes=['BRCA1', 'BRCA2', 'TP53', 'EGFR', 'KRAS', 'PTEN'],
    min_quality=30,
    pass_only=True
)

print(f"Extracted {len(variants)} variants for analysis")
```

### Customize Analysis
```python
# Adjust quality threshold
variants = parse_vcf("sample.vcf", min_quality=20)  # Lower threshold

# Get all variants (including LowQual)
variants = parse_vcf("sample.vcf", pass_only=False)

# Expand gene list
cancer_genes = ['BRCA1', 'BRCA2', 'TP53', 'EGFR', 'KRAS', 'PTEN', 
                'APC', 'MLH1', 'MSH2', 'ATM', 'CHEK2']
variants = parse_vcf("sample.vcf", genes=cancer_genes)
```

### Generate Reports
```python
import json

# After running MedGemma analysis (see notebook)
clinical_report = {
    'sample_id': 'PATIENT_001',
    'findings': [...],  # From analysis
    'summary': {...}
}

with open('report_PATIENT_001.json', 'w') as f:
    json.dump(clinical_report, f, indent=2)

print("✓ Report saved")
```

---

## Documentation

| Guide | Purpose | Read Time |
|-------|---------|-----------|
| [VCF_PARSER_GUIDE.md](VCF_PARSER_GUIDE.md) | Parser API & examples | 10 min |
| [VCF_INTEGRATION_DEMO.md](VCF_INTEGRATION_DEMO.md) | Full workflow walkthrough | 15 min |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phase 2 roadmap (RAG) | 20 min |
| [PHASE_1_SUMMARY.md](PHASE_1_SUMMARY.md) | Completion report | 30 min |

---

## Performance Expectations

### VCF Parsing
- **100 variants:** <0.01 seconds
- **1,000 variants:** <0.1 seconds
- **10,000 variants:** ~1 second

### MedGemma Analysis
- **Single variant:** 2-5 seconds (GPU) / 20-60 seconds (CPU)
- **10 variants:** ~30 seconds (GPU) / ~5 minutes (CPU)
- **100 variants:** ~5 minutes (GPU) / ~50 minutes (CPU)

**Tip:** Use GPU if possible! 10x faster.

---

## Getting Help

### Check Logs
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now see detailed parser logs
from src.parsing import parse_vcf
variants = parse_vcf("sample.vcf")
```

### Review Test Examples
```bash
# See how tests use the parser
cat tests/test_vcf_parser.py

# See integration examples
cat tests/test_integration.py
```

### Read Documentation
- **Parser issues?** → [`VCF_PARSER_GUIDE.md`](VCF_PARSER_GUIDE.md)
- **Integration questions?** → [`VCF_INTEGRATION_DEMO.md`](VCF_INTEGRATION_DEMO.md)
- **MedGemma setup?** → [`MODEL_DOWNLOAD_GUIDE.md`](MODEL_DOWNLOAD_GUIDE.md)

---

## Summary Checklist

- [ ] Installed dependencies (PyTorch, Transformers, etc.)
- [ ] Ran tests (31/31 passing)
- [ ] Parsed test VCF (4 variants extracted)
- [ ] Loaded MedGemma model (~3.5GB VRAM)
- [ ] Ran first classification (pathogenic/benign)
- [ ] Generated JSON report
- [ ] Tried own VCF file (optional)

**All checked?** 🎉 You're ready to use VCF + MedGemma!

---

**Next:** See [`VCF_INTEGRATION_DEMO.md`](VCF_INTEGRATION_DEMO.md) for advanced usage.

**Questions?** Review the [documentation](#documentation) or check test examples.
