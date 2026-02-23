# Troubleshooting Guide

Quick reference for common issues and solutions.

---

## Environment Setup Issues

### "command not found: python3"
**Problem:** Python 3 not installed or not in PATH

**Solution:**
```bash
# Check Python installation
python --version
python3 --version

# On macOS (using Homebrew)
brew install python@3.10

# On Ubuntu/Debian
sudo apt install python3.10 python3.10-venv

# On Windows
# Download from https://www.python.org/downloads/
```

### "ModuleNotFoundError: No module named 'venv'"
**Problem:** venv module not available

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# macOS (Homebrew)
brew install python@3.10

# Windows: Use native Python installer
```

### ".venv/bin/activate: No such file"
**Problem:** Virtual environment not created or corrupted

**Solution:**
```bash
# Recreate virtualenv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# Or use setup script
bash setup_environment.sh
```

### "pip: command not found after activation"
**Problem:** Virtual environment not properly activated

**Solution:**
```bash
# Check activation
echo $VIRTUAL_ENV
# Should show: /path/to/.venv

# If empty, activate properly
source .venv/bin/activate

# Verify
which pip
# Should show: /path/to/.venv/bin/pip
```

---

## Dependency Installation Issues

### "Failed building wheel for torch"
**Problem:** PyTorch build requires C++ compiler

**Solution:**
```bash
# On Ubuntu/Debian
sudo apt install build-essential python3-dev

# On macOS
xcode-select --install

# Or use pre-built wheels (recommended)
pip install --no-cache-dir torch

# For GPU support with specific CUDA version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### "CUDA out of memory" during model loading
**Problem:** Not enough GPU memory for 4B model

**Solutions:**

**Option 1: Use smaller model**
```python
MODEL_NAME = "google/medgemma-1.1-2b-it"  # 2B instead of 4B (1.5GB vs 3.5GB)
```

**Option 2: Use 8-bit quantization instead of 4-bit**
```python
bnb_4bit_quant_type = "int8"  # Lower precision, less VRAM
```

**Option 3: Use CPU mode**
```python
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Force CPU
# Then reload model
```

### "No module named 'src'"
**Problem:** Running notebook from wrong directory

**Solution:**
```bash
# Ensure you're in project root
pwd  # Should show: /home/shiftmint/Documents/kaggle/medAi_google

# Check structure
ls -la src/parsing/vcf_parser.py

# Then run from correct location
cd /home/shiftmint/Documents/kaggle/medAi_google
source .venv/bin/activate
jupyter notebook notebooks/vcf_medgemma_integration.ipynb
```

---

## HuggingFace Authentication Issues

### "HUGGINGFACE_TOKEN not found"
**Problem:** Token not set in environment or .env file

**Solution:**

**Option 1: Export environment variable**
```bash
export HUGGINGFACE_TOKEN="hf_your_token_here_XXXXXXXXXXXXXXXX"

# Verify
echo $HUGGINGFACE_TOKEN
```

**Option 2: Create .env file**
```bash
cp .env.example .env
nano .env
# Edit: HUGGINGFACE_TOKEN=hf_your_token_here_XXXXXXXXXXXXXXXX

# Load in terminal
set -a
source .env
set +a
```

**Option 3: Set in Jupyter cell**
```python
import os
os.environ['HUGGINGFACE_TOKEN'] = 'hf_your_token_here_XXXXXXXXXXXXXXXX'
```

### "Model access requires authentication"
**Problem:** Token doesn't have access to MedGemma model

**Solution:**
1. Go to https://huggingface.co/settings/tokens
2. Ensure "read" permission is selected
3. Accept model license at https://huggingface.co/google/medgemma-1.5-4b-it
4. Create new token if needed
5. Replace HUGGINGFACE_TOKEN with new token

### "401 Unauthorized" when downloading model
**Problem:** Invalid or expired token

**Solution:**
```bash
# Generate new token
huggingface-cli login

# Or manually set
export HUGGINGFACE_TOKEN="hf_new_token_here"

# Test authentication
python3 -c "from huggingface_hub import model_info; print(model_info('google/medgemma-1.5-4b-it'))"
```

---

## Notebook Execution Issues

### "Cell execution never completes / hangs"
**Problem:** Model is still loading or inference is slow

**Solution:**
```python
# Check progress
# First cell may take 60+ seconds for model download

# Force CPU if GPU is hanged
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Restart kernel and re-run
# (Ctrl+Shift+P → "Restart Kernel")
```

### "RuntimeError: CUDA runtime error"
**Problem:** GPU memory error or CUDA mismatch

**Solution:**
```bash
# Check CUDA version
nvidia-smi

# Verify PyTorch CUDA support
python3 -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"

# If mismatch, reinstall PyTorch
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### "OSError: No such file or directory: 'data/test_samples/sample_001.vcf'"
**Problem:** Test data not present or wrong path

**Solution:**
```bash
# Check file exists
ls -la data/test_samples/sample_001.vcf

# If missing, use test samples from repository
python3 -c "
from src.data.vcf_parser import VCFParser
parser = VCFParser('data/test_samples/sample_001.vcf')
print('✓ VCF file found and readable')
"

# Or verify you're in project root
pwd  # Must be: /home/shiftmint/Documents/kaggle/medAi_google
```

### "ValueError: No variants found after filtering"
**Problem:** VCF file filtered too strictly

**Solution:**
```python
# Check filtering parameters
parser = VCFParser(
    filter_pass_only=False,  # Allow FILTER != PASS
    min_quality=0            # No quality filtering
)
variants = parser.parse('your_file.vcf')
print(f"Found {len(variants)} variants")
```

---

## Test Suite Issues

### "pytest: command not found"
**Problem:** pytest not installed or virtualenv not activated

**Solution:**
```bash
# Activate virtualenv
source .venv/bin/activate

# Install pytest
pip install pytest pytest-cov

# Run tests
pytest tests/ -v
```

### "31 tests fail with import errors"
**Problem:** Tests running in wrong directory or without .venv

**Solution:**
```bash
# Ensure in project root
cd /home/shiftmint/Documents/kaggle/medAi_google

# Activate virtualenv
source .venv/bin/activate

# Run with explicit path
pytest tests/ -v --tb=short

# Or run setup script first
bash setup_environment.sh
source .venv/bin/activate
pytest tests/ -v
```

### "Some tests pass, some fail intermittently"
**Problem:** GPU memory or resource contention

**Solution:**
```bash
# Run with single process
pytest tests/ -v --co  # Show all tests first

# Run specific test
pytest tests/test_vcf_parser.py::test_parse_vcf_file -v

# Force CPU for tests
export CUDA_VISIBLE_DEVICES=""
pytest tests/ -v
```

---

## Performance Issues

### "Model inference is too slow"
**Problem:** Running on CPU or suboptimal settings

**Solution:**

**Check GPU:**
```python
import torch
print("GPU Available:", torch.cuda.is_available())
print("Device:", torch.cuda.get_device_name() if torch.cuda.is_available() else "CPU")
print("VRAM:", torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else "N/A")
```

**Force GPU:**
```python
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use first GPU

# Or with device_map
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto"  # Automatic GPU placement
)
```

**Optimize inference:**
```python
# Use smaller model
MODEL_NAME = "google/medgemma-1.1-2b-it"

# Or batch process
results = []
for variant in variants:
    result = model.generate(input_ids, max_new_tokens=100)
    results.append(result)
```

### "Disk space warning"
**Problem:** Model download or outputs consuming space

**Check disk:**
```bash
df -h
du -sh .venv
du -sh ~/.cache/huggingface
```

**Clean up:**
```bash
# Remove old models
rm -rf ~/.cache/huggingface/transformers

# Or specific model
cd ~/.cache/huggingface/hub
rm -rf models--google--medgemma-1.5-4b-it

# Note: Model will re-download when needed
```

---

## Platform-Specific Issues

### macOS: "error: command 'gcc' not found"
**Solution:**
```bash
xcode-select --install
```

### Windows WSL2: "CUDA not available"
**Solution:**
```bash
# Ensure NVIDIA drivers installed
nvidia-smi

# Install WSL2 GPU support
# See: https://docs.microsoft.com/en-us/windows/wsl/tutorials/gui-apps

# Test CUDA
python3 -c "import torch; print(torch.cuda.is_available())"
```

### Ubuntu 20.04: "Python 3.10 not found"
**Solution:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-venv
```

---

## Getting Help

**Still stuck?**

1. Check detailed setup guide: [SETUP_GUIDE.md](SETUP_GUIDE.md)
2. Run full setup script: `bash setup_environment.sh`
3. Check log files: Look in notebooks for error messages
4. Verify installation: `pytest tests/ -v`
5. Review example code: See `tests/` directory

**For specific issues:**
- VCF parsing: See [VCF_PARSER_GUIDE.md](VCF_PARSER_GUIDE.md)
- MedGemma integration: See [VCF_INTEGRATION_DEMO.md](VCF_INTEGRATION_DEMO.md)
- Environment: See [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

**Report bugs or ask questions in Issues section!**
