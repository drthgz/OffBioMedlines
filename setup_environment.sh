#!/bin/bash
# ============================================================================
# Setup Script for VCF + MedGemma Integration Project
# Purpose: Create reproducible Python environment with virtualenv
# Usage: bash setup_environment.sh
# ============================================================================

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON_VERSION="3.10"

echo "============================================================================"
echo " VCF + MedGemma Integration - Environment Setup"
echo "============================================================================"
echo ""
echo "📍 Project Root: $PROJECT_ROOT"
echo "🐍 Python Version Required: 3.10+"
echo "📦 Virtualenv Location: $VENV_DIR"
echo ""

# Step 1: Check Python version
echo "Step 1: Checking Python version..."
PYTHON_CMD=$(command -v python3 || command -v python)
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION_ACTUAL=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION_ACTUAL"
echo ""

# Step 2: Create virtualenv
echo "Step 2: Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment already exists at $VENV_DIR"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        $PYTHON_CMD -m venv "$VENV_DIR"
        echo "✓ Virtual environment recreated"
    else
        echo "✓ Using existing virtual environment"
    fi
else
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at $VENV_DIR"
fi
echo ""

# Step 3: Activate virtualenv
echo "Step 3: Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo ""

# Step 4: Upgrade pip, setuptools, wheel
echo "Step 4: Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel
echo "✓ Pip upgraded"
echo ""

# Step 5: Install requirements
echo "Step 5: Installing dependencies from requirements.txt..."
echo "⏳ This may take several minutes (especially torch)..."
pip install -r "$PROJECT_ROOT/requirements.txt"
echo "✓ Dependencies installed"
echo ""

# Step 6: Create .env file if needed
echo "Step 6: Checking environment configuration..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  .env file not found"
    echo "Creating .env from .env.example..."
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo "✓ Created .env file"
        echo "📝 Please update .env with your HuggingFace token"
    else
        echo "Creating minimal .env..."
        cat > "$PROJECT_ROOT/.env" << 'EOF'
# Environment variables for VCF + MedGemma Integration
HUGGINGFACE_TOKEN=
PROJECT_ROOT=/home/shiftmint/Documents/kaggle/medAi_google
EOF
        echo "✓ Created minimal .env file"
        echo "📝 Add your HuggingFace token to .env"
    fi
else
    echo "✓ .env file exists"
fi
echo ""

# Step 7: Verify installation
echo "Step 7: Verifying installation..."
echo ""
echo "📊 Installed packages:"
pip list | grep -E "(torch|transformers|accelerate|bitsandbytes|pytest|jupyter)" || true
echo ""

# Step 8: Test imports
echo "Step 8: Testing critical imports..."
python3 -c "
import torch
print(f'✓ torch {torch.__version__} (CUDA available: {torch.cuda.is_available()})')
" || echo "❌ Failed to import torch"

python3 -c "
import transformers
print(f'✓ transformers {transformers.__version__}')
" || echo "❌ Failed to import transformers"

python3 -c "
from src.data import VCFParser
print('✓ VCF parser module')
" || echo "❌ Failed to import VCF parser"

echo ""

# Step 9: Run tests (optional)
echo "Step 9: Running tests (optional)..."
echo "Run: pytest tests/ -v"
echo ""

# Final summary
echo "============================================================================"
echo " ✅ SETUP COMPLETE!"
echo "============================================================================"
echo ""
echo "📝 Next steps:"
echo ""
echo "1️⃣  Activate the environment:"
echo "   source $VENV_DIR/bin/activate"
echo ""
echo "2️⃣  Update .env with your HuggingFace token:"
echo "   Edit: $PROJECT_ROOT/.env"
echo ""
echo "3️⃣  Run tests:"
echo "   pytest tests/ -v"
echo ""
echo "4️⃣  Start Jupyter notebook:"
echo "   jupyter notebook notebooks/vcf_medgemma_integration.ipynb"
echo ""
echo "5️⃣  Or run Python:"
echo "   python3 << 'EOF'"
echo "   from src.data import parse_vcf"
echo "   variants = parse_vcf('data/test_samples/sample_001.vcf')"
echo "   print(f'Extracted {len(variants)} variants')"
echo "   EOF"
echo ""
echo "⚠️  IMPORTANT:"
echo "   - Activate virtualenv before working: source .venv/bin/activate"
echo "   - Set HUGGINGFACE_TOKEN in .env before running MedGemma"
echo "   - GPU recommended for faster inference"
echo ""
echo "============================================================================"
