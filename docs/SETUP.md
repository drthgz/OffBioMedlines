# Project Setup Guide

Complete instructions for setting up the VCF + MedGemma integration pipeline.

---

## ⚡ Quick Start (5 Minutes)

```bash
# 1. Navigate to project
cd /home/shiftmint/Documents/kaggle/medAi_google

# 2. Automated setup (creates .venv, installs dependencies)
bash setup_environment.sh

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Set HuggingFace token
export HUGGINGFACE_TOKEN="hf_your_token_here"

# 5. Run tests to verify
pytest tests/ -v

# 6. Run notebook
jupyter notebook notebooks/vcf_medgemma_integration.ipynb
```

---

## System Requirements

### Minimum
- Python 3.10+
- 8 GB RAM
- 5 GB disk space
- Linux, macOS, or Windows (WSL2)

### Recommended
- Python 3.10-3.11
- 16 GB RAM
- 10 GB disk space
- NVIDIA GPU (RTX 3060+ with 6GB+ VRAM) - optional but 10x faster
- CUDA 12.1+ (if using GPU)

### Tested Platforms
- ✅ Ubuntu 22.04 + Python 3.10 + NVIDIA RTX 4090
- ✅ macOS 13 + Python 3.11 + Apple Silicon
- ✅ Windows 11 WSL2 + Python 3.10

---

## Manual Setup (If Script Fails)

### 1. Create Virtual Environment

```bash
# Create virtualenv
python3 -m venv .venv

# Activate it
source .venv/bin/activate          # Linux/macOS
# or
.venv\Scripts\activate             # Windows
```

### 2. Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

### 3. Install Dependencies

```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Verify critical packages
pip list | grep -E "torch|transformers|accelerate"
```

### 4. Verify Installation

```bash
# Test imports
python3 -c "import torch, transformers; print('✓ OK')"

# Run test suite
pytest tests/ -v
```

---

## Configure HuggingFace Token

**Required to download MedGemma model**

### Get Your Token

1. Visit https://huggingface.co/settings/tokens
2. Click "New token"
3. Set Role: "read"
4. Create and copy the token

### Set Token (Choose One Method)

**Option 1: Environment Variable (Temporary)**
```bash
export HUGGINGFACE_TOKEN="hf_your_token_here"
echo $HUGGINGFACE_TOKEN  # Verify it's set
```

**Option 2: .env File (Persistent)**
```bash
# Copy template
cp .env.example .env

# Edit with your token
nano .env
# Find: HUGGINGFACE_TOKEN=hf_your_token_here_XXXXXXXXXXXXXXXXXX
# Replace with actual token

# Load in terminal
set -a
source .env
set +a
```

**Option 3: In Python Code**
```python
import os
os.environ['HUGGINGFACE_TOKEN'] = 'hf_your_token_here'
```

---

## Run the Notebook

### Jupyter Notebook
```bash
source .venv/bin/activate
jupyter notebook notebooks/vcf_medgemma_integration.ipynb
```

### Jupyter Lab
```bash
source .venv/bin/activate
jupyter lab notebooks/vcf_medgemma_integration.ipynb
```

### VS Code
1. Open the notebook in VS Code
2. Press Ctrl+Shift+P
3. Select "Select Kernel" 
4. Choose ".venv" environment
5. Run cells

---

## GPU Configuration

### Check GPU Availability

```bash
# Check if CUDA is available
python3 -c "import torch; print(torch.cuda.is_available())"

# Check GPU details
nvidia-smi
```

### Force GPU Usage
```python
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use first GPU
```

### Force CPU Mode
```python
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""   # Use CPU only
```

---

## Troubleshooting Setup Issues

### "python3: command not found"
**Solution:** Install Python 3.10+
```bash
# Ubuntu/Debian
sudo apt install python3.10 python3.10-venv

# macOS (Homebrew)
brew install python@3.10

# Windows - Download from https://www.python.org/downloads/
```

### ".venv/bin/activate: No such file or directory"
**Solution:** Recreate virtualenv
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'torch'"
**Solution:** Ensure virtualenv is activated
```bash
# Check activation status
which python  # Should show path to .venv

# If not activated, activate it
source .venv/bin/activate
```

### "pip install" is slow
**Solution:** Use wheel cache
```bash
pip install --upgrade pip setuptools wheel
pip cache purge
pip install --no-cache-dir -r requirements.txt
```

### "transformers version error"
**Solution:** Ensure compatible version
```bash
pip install transformers==4.40.0
```

---

## Verify Setup

Run this checklist to ensure everything works:

```bash
# 1. Check Python version
python3 --version  # Should be 3.10+

# 2. Activate virtualenv
source .venv/bin/activate

# 3. Check packages
python3 -c "import torch, transformers, accelerate, bitsandbytes; print('✓ Core packages OK')"

# 4. Check GPU (if available)
python3 -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"

# 5. Run tests
pytest tests/ -v  # Should show 31/31 passing

# 6. Check VCF parser
python3 -c "from src.data import VCFParser; print('✓ VCF parser OK')"
```

**All ✓?** → Setup complete! Ready to run notebook.

---

## Update Dependencies

To update packages in the future:

```bash
# Update all
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade torch

# Check for outdated packages
pip list --outdated
```

---

## Deactivate Environment

When done working:

```bash
deactivate
```

---

## Next Steps

- **Run notebook:** `jupyter notebook notebooks/vcf_medgemma_integration.ipynb`
- **Run tests:** `pytest tests/ -v`
- **See troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **API reference:** [VCF_PARSER_GUIDE.md](VCF_PARSER_GUIDE.md)

---

**Still stuck?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for 30+ solutions.
