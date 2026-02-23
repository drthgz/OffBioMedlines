# Agent: Python Coding Standards & Patterns

**Role:** Ensure all Python code follows project conventions, best practices, and maintains consistency.

**Activated by:** When writing/editing `.py` files, reference this with `@agent.python` or ask "Code this using agent.python standards"

---

## Core Principles

1. **Readability First** - Code is read 10x more than written
2. **Type Hints Always** - All functions/methods must have type hints
3. **No Magic Numbers** - Constants defined at module level with names
4. **DRY (Don't Repeat Yourself)** - Extract common patterns into functions
5. **One Responsibility** - Each function/class does one thing well

---

## Code Structure Template

### Imports (Strict Order)

```python
# 1. Standard library (alphabetical)
import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# 2. Third-party (alphabetical)
import numpy as np
import torch

# 3. Local imports
from src.data import VCFParser
```

### Module Organization

```python
"""Module docstring - what this module does (1-2 sentences).

Example:
    Typical usage example:
    
    >>> parser = VCFParser("sample.vcf")
    >>> variants = parser.parse()
"""

# Constants (UPPERCASE_WITH_UNDERSCORES)
DEFAULT_QUALITY_THRESHOLD = 50
MAX_VARIANTS_PER_SAMPLE = 1000

# Type aliases
VariantDict = Dict[str, any]

# Enums (PascalCase)
class VariantType(Enum):
    """Enumeration of variant types."""
    SNV = "snv"
    INDEL = "indel"
    SV = "sv"

# Dataclasses (before functions)
@dataclass
class Variant:
    """Immutable variant record."""
    chromosome: str
    position: int
    gene: str
    
    def __post_init__(self):
        """Validate after initialization."""
        if self.position < 0:
            raise ValueError("Position must be non-negative")

# Functions (lowercase_with_underscores)
def parse_variant(line: str) -> Variant:
    """Parse single variant from VCF line.
    
    Args:
        line: Raw VCF line as string
        
    Returns:
        Parsed Variant object
        
    Raises:
        ValueError: If line is malformed
    """
    ...

# Main entry point
if __name__ == "__main__":
    main()
```

---

## Function Signature Standards

```python
def analyze_variants(
    variants: List[Variant],
    gene_filter: Optional[str] = None,
    min_quality: int = DEFAULT_QUALITY_THRESHOLD,
    verbose: bool = False
) -> Dict[str, any]:
    """Analyze list of variants with optional filtering.
    
    This function takes variants, optionally filters by gene,
    and returns analysis results formatted as a dictionary.
    
    Args:
        variants: List of Variant objects to analyze
        gene_filter: Optional gene name to filter by (case-insensitive)
        min_quality: Minimum quality score threshold (default 50)
        verbose: If True, print processing details
        
    Returns:
        Dictionary with keys:
            - "total": Total variants processed
            - "passed": Variants passing filters
            - "results": List of analysis results
            
    Raises:
        TypeError: If variants is not a list
        ValueError: If min_quality is negative
        
    Examples:
        >>> variants = [v1, v2, v3]
        >>> results = analyze_variants(variants, gene_filter="BRCA1")
        >>> print(results["total"])
        3
    """
    if not isinstance(variants, list):
        raise TypeError("variants must be a list")
    if min_quality < 0:
        raise ValueError("min_quality must be non-negative")
    
    # Implementation
    ...
```

---

## Error Handling Standards

### ✅ DO: Be Specific

```python
# Good
try:
    model = load_model(model_name)
except FileNotFoundError as e:
    logger.error(f"Model file not found: {model_name}")
    raise ModelLoadError(f"Cannot load {model_name}") from e
except torch.cuda.OutOfMemoryError as e:
    logger.warning(f"GPU out of memory, falling back to CPU")
    model = load_model(model_name, device="cpu")
```

### ❌ DON'T: Catch Everything

```python
# Bad - too broad
try:
    result = do_something()
except Exception:
    pass
```

---

## Testing Standards

### Test File Structure

```python
# tests/test_variant_parser.py
"""Tests for variant parser module."""

import pytest
from src.data import VCFParser, Variant


class TestVCFParser:
    """Test VCFParser class functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return VCFParser("data/test_samples/sample_001.vcf")
    
    def test_parse_returns_list(self, parser):
        """Test that parse returns a list."""
        result = parser.parse()
        assert isinstance(result, list)
    
    def test_parse_variant_valid(self, parser):
        """Test parsing valid variant."""
        result = parser.parse()
        assert len(result) > 0
        assert isinstance(result[0], Variant)
    
    @pytest.mark.parametrize("value,expected", [
        (50, True),
        (100, False),
    ])
    def test_quality_filter(self, parser, value, expected):
        """Test quality filtering with different thresholds."""
        parser.min_quality = value
        result = parser.parse()
        # Assertions here
```

### Coverage Targets

- **Core logic (parsing, inference):** 90%+ coverage
- **Error handling:** 80%+ coverage
- **Utils/helpers:** 70%+ coverage
- **Overall target:** 85%+ coverage

---

## Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| **Classes** | PascalCase | `VCFParser`, `MedGemmaInference` |
| **Functions** | lowercase_snake_case | `parse_variant`, `classify_variant` |
| **Constants** | UPPERCASE_SNAKE_CASE | `MAX_TOKENS`, `DEFAULT_BATCH_SIZE` |
| **Private** | Leading underscore | `_internal_helper()` |
| **Variables** | lowercase_snake_case | `model_name`, `variant_list` |
| **Booleans** | is_/has_/can_ prefix | `is_valid`, `has_annotation` |

---

## Comments & Docstrings

### ✅ DO: Document "Why"

```python
# Good - explains the reason
# Use float16 to reduce memory footprint by 50% vs float32
# This allows 4B model to fit in 4GB VRAM with quantization
torch_dtype = torch.float16
```

### ❌ DON'T: Document "What"

```python
# Bad - duplicates code
# Set torch_dtype to float16
torch_dtype = torch.float16
```

### Docstring Quality

```python
def classify_variant(variant: Variant) -> str:
    """Classify variant pathogenicity using MedGemma.
    
    Uses the MedGemma biomedical language model to assess
    whether a genetic variant is pathogenic, benign, or
    of uncertain significance. Includes confidence scoring.
    
    Args:
        variant: Variant object with chromosome, position, ref/alt
        
    Returns:
        Classification as one of: "pathogenic", "likely_pathogenic",
        "uncertain_significance", "likely_benign", "benign"
        
    Raises:
        ValueError: If variant is missing required fields
        RuntimeError: If model fails to generate response
        
    Notes:
        - First time calling this loads the model (~60s)
        - Subsequent calls reuse cached model
        - Requires HUGGINGFACE_TOKEN env var set
    """
```

---

## Performance Standards

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed internal info")        # Dev debugging
logger.info("VCFParser initialized")          # User-facing progress
logger.warning("Using CPU (GPU unavailable)") # Degraded performance
logger.error("Failed to load model")          # Something failed
logger.critical("Out of memory - stopping")   # Fatal error
```

### Memory Efficiency

- **Generators for large files:** Don't load entire VCF into memory
- **Context managers:** Always use `with` for file operations
- **Delete large objects:** Explicitly `del` after use if memory-critical

```python
# Good - memory efficient
def parse_vcf_lines(vcf_path: str):
    """Yield variants one at a time (generator)."""
    with open(vcf_path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            yield parse_variant(line)

# Use it without loading entire file
for variant in parse_vcf_lines("huge_file.vcf"):
    process_variant(variant)
```

---

## Git Commit Standards

```
Type: Brief description (50 chars max)

Detailed explanation of what changed and why (wrap at 72 chars).
Reference issues and PRs if applicable.

Type options:
- feat: New feature
- fix: Bug fix  
- refactor: Code restructure (no behavior change)
- docs: Documentation updates
- test: Testing changes
- perf: Performance improvements
- chore: Dependencies, config, etc.

Example:
feat: Add FILTER column parsing to VCFParser

Previously, VCFParser only tracked PASS/FAIL status. Now it
captures the full FILTER column value (e.g., "LowQual,HighDP").

This allows filtering by specific failure reasons instead of
just binary pass/fail.

Fixes #42
```

---

## When to Reference This Agent

Use `@agent.python` when:
- Writing new Python modules in `src/`
- Refactoring existing code
- Setting up new test files
- Asking for code review suggestions
- Creating utility functions
- Defining data structures

**Example prompt:**
```
@agent.python: Write a function to validate variant records 
with proper type hints, docstrings, and error handling.
```

---

## Key Files to Follow

- `src/parsing/vcf_parser.py` - Reference implementation
- `tests/test_vcf_parser.py` - Reference test structure
- `requirements.txt` - Approved dependencies

---

- No business logic in notebooks
- src/ contains pure logic
- notebooks only orchestrate
- All public functions typed
- Exceptions are specific
- No silent failures

## Checklist Before Committing Code

- [ ] All functions have type hints
- [ ] All public functions have docstrings (Google format)
- [ ] No `except` without specific exception type
- [ ] No magic numbers (use named constants)
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Code follows naming conventions
- [ ] No `print()` statements (use logging)
- [ ] `TODO`, `FIXME` comments have context
- [ ] Commit message follows standards
