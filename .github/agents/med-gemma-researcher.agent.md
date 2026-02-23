# Agent: MedGemma Research & Implementation

**Role:** Guide research, implementation, and problem-solving for MedGemma integration and biomedical variant classification.

**Activated by:** When researching MedGemma, implementing features, or troubleshooting model issues. Reference with `@agent.medgemma` or ask "Help using agent.medgemma"

---

## MedGemma Fundamentals

### Model Details

| Property | Value | Notes |
|----------|-------|-------|
| **Model Name** | google/medgemma-1.5-4b-it | From HuggingFace |
| **Parameters** | 4 billion (4B) | Smaller than Llama-2 7B |
| **Training Data** | Medical literature + instructions | Biomedically specialized |
| **Context Window** | 8,192 tokens | Enough for variant + context |
| **Quantization** | 4-bit NF4 | 16GB → 3.5GB memory |
| **Type** | Instruction-tuned LM | Optimized for Q&A |
| **License** | Open source | Can be self-hosted |
| **Access** | HuggingFace hub | Requires token |

### Key Characteristics

**Strengths:**
- ✅ Biomedically trained (better than GPT generalist)
- ✅ Runs locally (no API calls, no latency)
- ✅ 4B size fits on standard GPUs/laptops
- ✅ Instruction-tuned (follows prompts well)
- ✅ No API costs at scale

**Limitations:**
- ⚠️ Smaller than GPT-4 (more mistakes possible)
- ⚠️ Medical training data has cutoff (not real-time)
- ⚠️ Can hallucinate (needs validation)
- ⚠️ No fine-tuning on YOUR data without effort

---

## Setting Up MedGemma

### Version Requirements

**CRITICAL - Do NOT skip:**

```python
# REQUIRED versions for MedGemma compatibility:
torch >= 2.0.0     # GPU acceleration
transformers == 4.40.0  # EXACT version - 5.x breaks MedGemma
accelerate >= 0.24.0    # Multi-GPU/CPU fallback
bitsandbytes >= 0.41.0  # 4-bit quantization
```

**Why 4.40.0 exactly?**
- Transformers 5.0+ removed `GenericForSequenceClassification`
- MedGemma's Gemma3 model code still imports it
- Will be fixed in future MedGemma release
- For now: Lock to 4.40.0

### Loading the Model - Best Practices

```python
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)
import torch

MODEL_NAME = "google/medgemma-1.5-4b-it"

# 1. Configure 4-bit quantization
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,  # Inference dtype
    bnb_4bit_use_double_quant=True,        # Reduces memory further
    bnb_4bit_quant_type="nf4"              # Normalized float 4
)

# 2. Load tokenizer (fast, ~1s)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# 3. Load model with quantization (slow first time, ~60s + download)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=quantization_config,
    device_map="auto",                      # Auto place on GPU/CPU
    torch_dtype=torch.float16,
    trust_remote_code=True,                 # Required for MedGemma
)
```

### GPU vs CPU Mode

**GPU (Recommended)**
```python
# Explicitly use GPU 0
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# Verify GPU
import torch
print(torch.cuda.is_available())           # True
print(torch.cuda.get_device_name(0))       # GPU name
print(torch.cuda.get_device_properties(0)) # Full specs
torch.manual_seed(42)
torch.cuda.manual_seed_all(42)
```

**CPU Only (Fallback)**
```python
# Force CPU mode (10x slower)
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Verify CPU
print(torch.cuda.is_available())  # False
```

---

## Prompting Strategies for Variant Classification

### Format: Biomedical Q&A Structure

MedGemma is instruction-tuned. Structure prompts like real medical questions:

```python
def create_variant_prompt(variant: Variant) -> str:
    """Create structured prompt for variant classification."""
    
    prompt = f"""Analyze this genetic variant and provide clinical classification:

**Variant Details:**
Gene: {variant.gene}
Location: {variant.chromosome}:{variant.position}
Type: {variant.variant_type.value}
DNA Change: {variant.ref_allele} → {variant.alt_allele}
HGVS: {variant.hgvs or 'Not available'}
Quality Score: {variant.quality_score}

**Task:**
Classify this variant's pathogenicity as ONE of:
- PATHOGENIC: Disease-causing mutation
- LIKELY_PATHOGENIC: Probably disease-causing  
- UNCERTAIN_SIGNIFICANCE: Unknown effect
- LIKELY_BENIGN: Probably harmless
- BENIGN: Clearly harmless

**Response Format:**
Classification: [CHOOSE ONE]
Confidence: [0-100]%
Reasoning: [2-3 sentence explanation]"""
    
    return prompt
```

### Temperature & Generation Settings

```python
def classify_variant(model, tokenizer, variant: Variant) -> Dict:
    """Classify variant using MedGemma."""
    
    prompt = create_variant_prompt(variant)
    
    # Format for instruction-tuned model
    formatted_prompt = f"""<start_of_turn>user
{prompt}<end_of_turn>
<start_of_turn>model
"""
    
    # Tokenize
    inputs = tokenizer(
        formatted_prompt,
        return_tensors="pt",
        truncation=True,
        max_length=2048
    ).to(model.device)
    
    # Generate with medical-appropriate settings
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,           # Enough for 2-3 sentences
            temperature=0.3,              # Lower = more deterministic (good for medical)
            top_p=0.95,                   # Nucleus sampling
            do_sample=True,               # Don't use greedy decoding
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract model's response (after the prompt)
    if "<start_of_turn>model" in response:
        response = response.split("<start_of_turn>model")[-1].strip()
    
    return parse_response(response)
```

### Temperature Explained

- **0.1-0.3:** Very deterministic, good for medical
- **0.5-0.7:** Balanced (default)
- **0.8-1.0:** Creative (not for medical!)

Medical use case: Use **0.3** (confident, consistent)

---

## Common Error Scenarios & Solutions

### Error: "ImportError: cannot import 'GenericForSequenceClassification'"

**Cause:** Transformers 5.x installed, MedGemma requires 4.x

**Solution:**
```bash
pip uninstall transformers
pip install transformers==4.40.0
```

Then restart notebook kernel.

### Error: "CUDA out of memory"

**Cause:** Not enough GPU VRAM

**Solutions (in order):**
1. Use smaller model: `google/medgemma-1.1-2b-it` (2B params, 1.5GB)
2. Lower batch size
3. Use 8-bit instead of 4-bit quantization
4. Fall back to CPU mode
5. Close other GPU applications

```python
# Option 1: Smaller model
MODEL_NAME = "google/medgemma-1.1-2b-it"  # 2B instead of 4B

# Option 2: Disable cache (loses speedup but saves memory)
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        use_cache=False,  # Disable KV cache
        max_new_tokens=100
    )
```

### Error: "Model download taking forever"

**Cause:** Large model (~3.5GB), first download

**Solutions:**
- Wait it out (60-120s typical for 3.5GB on good internet)
- Check internet speed: `speedtest-cli`
- Cache will be reused: `~/.cache/huggingface/hub/`

**To monitor:**
```python
import os
cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
print(sum(f.stat().st_size for f in cache_dir.rglob("*")) / 1e9, "GB")
```

### Error: "HUGGINGFACE_TOKEN not found"

**Cause:** Token not set in environment

**Solutions:**
```python
# 1. Check if set
import os
print(os.environ.get('HUGGINGFACE_TOKEN'))

# 2. Set explicitly
os.environ['HUGGINGFACE_TOKEN'] = 'hf_xxxxx'

# 3. Or load from .env
from dotenv import load_dotenv
load_dotenv()  # Reads .env file

# 4. Check token is valid
from huggingface_hub import login
login(token=os.environ['HUGGINGFACE_TOKEN'])
```

---

## Variant Classification Best Practices

### Prompt Engineering for Accuracy

**✅ DO: Provide Maximum Context**
```python
prompt = f"""Classify this BRCA1 variant:

Location: chr17:41196372 (exon 5 of BRCA1)
Change: c.68_69delAG (frameshift deletion)
Type: Loss-of-function variant
Population Frequency: 0.0001% (very rare)
Clinical Annotation: Known pathogenic in ClinVar
Gene Role: Tumor suppressor (DNA repair)

Classification: """
```

**❌ DON'T: Give Minimal Info**
```python
prompt = "Classify this variant: BRCA1 G>A at chr17:41196372"
```

### Handling Uncertainty

```python
def classify_with_confidence(model, tokenizer, variant) -> Dict:
    """Classify variant and estimate confidence."""
    
    response = classify_variant(model, tokenizer, variant)
    
    # MedGemma gives confidence in response
    # Extract and validate
    if response['confidence'] < 60:
        response['note'] = "LOW_CONFIDENCE - Consider manual review"
    elif response['confidence'] > 90:
        response['note'] = "HIGH_CONFIDENCE - Can use directly"
    else:
        response['note'] = "MODERATE_CONFIDENCE - Review recommended"
    
    return response
```

### Validation Against Gold Standards

```python
def validate_classification(model_pred: str, clinvar_annotation: str) -> bool:
    """Check if MedGemma agrees with ClinVar."""
    
    # Map classifications to consistency
    pathogenic_variants = {'pathogenic', 'likely_pathogenic'}
    benign_variants = {'benign', 'likely_benign'}
    
    model_is_pathogenic = model_pred.lower() in pathogenic_variants
    clinvar_is_pathogenic = clinvar_annotation.lower() in pathogenic_variants
    
    match = model_is_pathogenic == clinvar_is_pathogenic
    
    return match
```

---

## Integration with Notebook

### Notebook Cell Structure

```python
# Cell 1: Setup
import os
from dotenv import load_dotenv
load_dotenv()
hf_token = os.environ.get('HUGGINGFACE_TOKEN')

# Cell 2: Check Versions
import transformers, torch
print(f"Transformers: {transformers.__version__}")  # MUST be 4.40.0
print(f"PyTorch: {torch.__version__}")
assert transformers.__version__.startswith("4.40"), "CRITICAL: Update transformers"

# Cell 3: Load Model
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
# (model loading code)

# Cell 4: Test Single Variant
test_variant = Variant(...)
result = classify_variant(model, tokenizer, test_variant)
print(result)

# Cell 5: Batch Process
for variant in variants:
    result = classify_variant(model, tokenizer, variant)
```

---

## When to Use This Agent

Use `@agent.medgemma` when:
- Setting up MedGemma for the first time
- Troubleshooting model loading issues
- Optimizing prompts for better accuracy
- Researching MedGemma capabilities
- Implementing new variant classification logic
- Handling errors related to the model

**Example prompts:**
```
@agent.medgemma: Why is my MedGemma giving inconsistent 
classifications for the same variant?

@agent.medgemma: How can I improve classification accuracy 
beyond 75%? Should I fine-tune or use RAG?

@agent.medgemma: What's the best temperature setting for 
medical variant classification?
```

---

## Useful Resources

- **Model Card:** https://huggingface.co/google/medgemma-1.5-4b-it
- **Paper:** Search "MedGemma" on arXiv
- **HuggingFace Docs:** https://huggingface.co/docs/transformers/
- **BitsAndBytes:** https://github.com/TimDettmers/bitsandbytes
- **Your Implementation:** `notebooks/vcf_medgemma_integration.ipynb`

---

## Phase 2 (RAG Enhancement)

After basic classification works, enhance with:

1. **ClinVar Integration**
   - Embed known variants
   - Find most similar variants
   - Pass similarity scores to MedGemma

2. **gnomAD Integration**
   - Add population frequency
   - Variants < 1% frequency = more likely pathogenic

3. **ACMG Criteria**
   - Implement PVS1, PS1, PM2, etc.
   - Chain-of-thought reasoning

**Current Status:** Phase 1 working (basic classification)  
**Next:** Phase 2 (RAG) planned for increased accuracy

## Clinical Evidence Hierarchy

When classifying, prioritize evidence in this order:

1. Gold-standard annotations (ClinVar, curated databases)
2. Known loss-of-function in disease genes
3. Population frequency data (gnomAD thresholds)
4. Functional annotations
5. Model inference

Never allow model reasoning to override established gold-standard evidence.

## Reproducibility Mode (Competition Submission)
- Set all random seeds
- Use greedy decoding (temperature=0)
- Disable sampling
- Log model version and commit hash

## Model Skepticism Protocol

Before accepting output:
- Check for unsupported claims
- Cross-validate classification against structured rules
- Flag reasoning containing external facts not provided in prompt
- Never assume citation validity unless verified