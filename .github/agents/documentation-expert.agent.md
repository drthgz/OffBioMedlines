# Agent: Documentation Standards & Structure

**Role:** Maintain high-quality, consistent documentation across all project documentation files.

**Activated by:** When writing/updating docs, reference with `@agent.documentation` or ask "Help using agent.documentation"

---

## Documentation Philosophy

### Core Principles

1. **User-Centric** - Docs written for the reader, not the writer
2. **Progressive Disclosure** - Start simple, provide depth on demand
3. **Live Documentation** - Kept in sync with code (not outdated)
4. **Examples Over Theory** - Show, don't just tell
5. **Searchable** - Organized so users can find answers quickly

### Documentation Hierarchy

```
README.md (Entry point, 2 min read)
    ↓
docs/SETUP.md (Installation, 15 min)
    ↓
docs/README_EXPANDED.md (Why & how, 20 min)
    ↓
docs/VCF_PARSER_GUIDE.md (API details, reference)
    ↓
docs/TROUBLESHOOTING.md (Problem solving, lookup)
```

**Rule:** Each level assumes reader READ the previous level.

---

## README.md Standards (Root Level)

### Length Target: 200-300 lines (5 min read)

### Structure Template

```markdown
# Project Name: One-Line Description

Brief intro (1-2 sentences).

---

## ⚡ Quick Start (5 Minutes)

```bash
# Copy-paste command that gets people running
bash setup_environment.sh
source .venv/bin/activate
jupyter notebook notebooks/...
```

---

## What This does

**Input:** ...
**Process:** ...
**Output:** ...

✅ Results ✅

---

## 📚 Documentation

| Link | Time |
|------|------|
| [docs/SETUP.md]() | 15 min |
| [docs/README_EXPANDED.md]() | 20 min |

---

## Key Features

- ✅ Feature 1
- ✅ Feature 2

---

## System Requirements

| Category | Min | Recommended |
|----------|-----|-------------|
| Python | 3.10+ | 3.10/3.11 |
| RAM | 8 GB | 16 GB |

---

## Usage

### Example 1

```python
from src import SomeModule
result = SomeModule.do_something()
```

---

## Results

- Accuracy: X%
- Speed: Y sec/variant
- Memory: Z GB

---

## Troubleshooting

**Issue?** → [docs/TROUBLESHOOTING.md]()

---

**Ready?** Start with: `bash setup_environment.sh`
```

---

## docs/SETUP.md Standards

### Length Target: 15-20 min read (2000-2500 words)

### Sections to Include

1. **Quick Start (5 min)** - Just copy-paste
2. **Manual Setup** - Step-by-step if script fails
3. **Configuration** - Token, environment variables
4. **Verification** - How to test it works
5. **Troubleshooting** - Top 5-10 common issues

### Template

```markdown
# Project Setup Guide

One-sentence description of what you'll accomplish.

---

## ⚡ Quick Start (5 Minutes)

Copy-paste code block.

---

## System Requirements

Table with specifics.

---

## [Step 1]: Installation

Detailed instructions with explanations.

### Verification

```bash
# Commands to verify this step worked
```

---

## [Step 2]: Configuration

---

## Troubleshooting This Section

| Problem | Solution |
|---------|----------|
| Error message | What it means and how to fix |

---

## Next Steps

What to do after setup.
```

---

## docs/README_EXPANDED.md Standards

### Length Target: 20-30 min read (3000-4000 words)

### Purpose: Answer "Why?" and "How?"

### Sections to Include

1. **Problem Statement** - Why does this project exist?
2. **Architecture** - How is it organized? (with diagram)
3. **Component Deep Dive** - What does each part do?
4. **Design Decisions** - Why did we choose X over Y?
5. **Use Cases** - Who benefits? When to use?
6. **Limitations** - What can't it do?
7. **Future Plans** - Where is this heading?

### Template

```markdown
# Architecture & Design Philosophy

Intro paragraph (why this doc exists).

---

## Problem Statement

### The Challenge
- Problem 1
- Problem 2
- Problem 3

### Existing Solutions (Why not use them?)
- Solution A: ✗ Reason
- Solution B: ✗ Reason

### Our Approach
- ✅ Benefit 1
- ✅ Benefit 2

---

## Architecture Overview

### System Diagram

```
Input → Processing → Output
```

### Data Flow

Step-by-step what happens.

---

## Component Deep Dive

### 1. Component A

**Purpose:** ...
**How it works:** ...
**Why this way:** ...

```python
# Example code
```

---

## Design Decisions

### Why MedGemma instead of [Alternative]?

- ✅ Benefit 1
- ✅ Benefit 2
- ✗ Alternative limitation

---

## Use Cases

### 1. Research Labs
...

### 2. Clinics
...

---

## Limitations

- Current: ...
- Future: ...

---

## References

- Link 1
- Link 2
```

---

## docs/API_GUIDE.md Standards (e.g., VCF_PARSER_GUIDE.md)

### Purpose: Complete reference for code

### Sections

1. **Overview** - What this module does
2. **Installation** - How to import/use
3. **Quick Start** - First example
4. **Class Reference** - All classes with examples
5. **Function Reference** - All functions with examples
6. **Error Handling** - What can go wrong?
7. **Advanced Usage** - Next-level usage
8. **Examples** - Real-world examples

### Template

```markdown
# VCF Parser API Reference

One-line description.

---

## Overview

What this module does (2-3 sentences).

Imports:
```python
from src.parsing import VCFParser
```

---

## Quick Start

```python
# Most common use case
parser = VCFParser("sample.vcf")
variants = parser.parse()
for v in variants:
    print(v.gene)
```

---

## Class Reference

### VCFParser

Complete reference with all methods.

```python
class VCFParser:
    """Parse VCF files efficiently."""
```

#### Methods

**parse()**
```python
def parse(
    genes_of_interest: Optional[List[str]] = None,
    pass_only: bool = True
) -> List[Variant]:
    """Parse VCF file and return variants.
    
    Args:
        genes_of_interest: Filter to these genes (case-insensitive)
        pass_only: If True, only PASS filter status
        
    Returns:
        List of Variant objects
        
    Examples:
        >>> parser = VCFParser("sample.vcf")
        >>> variants = parser.parse(genes_of_interest=['BRCA1'])
        >>> len(variants)
        3
    """
```

---

## Function Reference

### parse_variant()

```python
def parse_variant(line: str) -> Variant:
    """Parse single VCF line."""
```

---

## Error Handling

**FileNotFoundError:** VCF file doesn't exist
→ Solution: Check path with `ls data/samples/*.vcf`

---

## Examples

### Example 1: Filter by Gene
...

### Example 2: Quality Filtering
...
```

---

## docs/TROUBLESHOOTING.md Standards

### Purpose: Quick problem solving (lookup reference)

### Structure

```markdown
# Troubleshooting Guide

---

## [Category]: [Problem]

### Symptoms

How you know you have this problem.

### Causes

What causes it (1-3 causes).

### Solutions (Try In Order)

**Solution 1:** Description
```bash
# Command to try
```

**Solution 2:** Description
```bash
# Alternative approach
```

### Prevention

How to avoid this in future.

---

## Related

- [Other troubleshooting page]()
- [Relevant docs]()
```

### Tone

- **Empathetic:** "This is frustrating, here's the fix"
- **Actionable:** "Do X, then run Y to verify"
- **Diagnostic:** "This is why it happened"

---

## docs/LESSONS_LEARNED.md (New - For Iterations)

### Purpose: Record insights from each phase

### Template

```markdown
# Lessons Learned

**Phase:** [Number] [Name]  
**Date:** YYYY-MM-DD  
**Duration:** X days  

---

## What We Did

Brief recap of phase goals.

---

## What Went Well

- ✅ Success 1 - Why it worked
- ✅ Success 2 - Replicable pattern

---

## What We'd Do Differently

- ❌ Mistake 1 - Why it was hard, how to avoid
- ❌ Mistake 2 - Better approach

---

## Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Accuracy | 100% | On test set |
| Speed | 2-3 sec | Per variant |

---

## Next Phase Recommendations

- [ ] Priority 1 - Why
- [ ] Priority 2 - Why

---

## Code Artifacts

- Link to key commits
- Link to documentation updated
```

---

## Writing Standards

### Tone

- **Friendly but professional** - Not too casual, not stiff
- **Clear over clever** - Clarity > cleverness
- **Active voice** - "We parse the VCF" not "The VCF is parsed"
- **Present tense** - "This module does X" not "This module will do X"

### Formatting

### Headers

```markdown
# H1: Page Title (One per document)

## H2: Major Section

### H3: Subsection

#### H4: Heading (rarely needed)
```

**Never skip levels:** No H1 to H3.

### Code Blocks

````markdown
```python
# Language specified!
def hello():
    return "world"
```

```bash
# Shell commands
pip install something
```

```json
{
  "key": "value"
}
```
````

**Always specify language.**

### Lists

✅ DO: Use bullets for unordered, numbers for sequences
```markdown
# Unordered
- Item 1
- Item 2

# Ordered (steps!)
1. First step
2. Second step
```

### Tables

```markdown
| Column | Type | Notes |
|--------|------|-------|
| name | string | User name |
| age | int | Age in years |
```

### Emphasis

```markdown
**Bold** for important terms or first use of term
*Italic* for file paths, variable names
`code` for code/terminal reference
```

### Links

```markdown
# External links
[Link text](https://example.com)

# Internal links
[Setup guide](docs/SETUP.md)
[Section](#heading)
```

---

## When to Update Docs

| Event | Action |
|-------|--------|
| New feature added | Update API guide + README |
| Bug fixed | Update TROUBLESHOOTING if user-facing |
| Phase completed | Add LESSONS_LEARNED entry |
| Error discovered | Document in TROUBLESHOOTING |
| Architecture changed | Update README_EXPANDED |

---

## Documentation Checklist

For every documentation file:

- [ ] Has a one-line description/purpose
- [ ] Links to related docs (where applicable)
- [ ] Use of code examples not just theory
- [ ] 3+ hours old (not rushed, reviewed)
- [ ] Spell checked
- [ ] Links verified (not broken)
- [ ] Formatted consistently with other docs
- [ ] Tested (if instructions, run them)

---

## When to Reference This Agent

Use `@agent.documentation` when:
- Writing a new documentation file
- Updating existing docs
- Deciding where documentation belongs
- Structuring a README or guide
- Reviewing documentation quality
- Creating LESSONS_LEARNED after a phase

**Example prompts:**
```
@agent.documentation: Create a LESSONS_LEARNED.md entry 
for this phase with the key successes and mistakes.

@agent.documentation: Review this README for clarity, 
completeness, and consistency with our standards.

@agent.documentation: Should this content go in README.md 
or README_EXPANDED.md? Why?
```

---

## Standard Files Every Project Needs

✅ README.md - Entry point  
✅ docs/SETUP.md - Installation  
✅ docs/README_EXPANDED.md - Deep dive  
✅ docs/TROUBLESHOOTING.md - Problem-solving  
✅ docs/API_GUIDES/*.md - Code references  
✅ docs/LESSONS_LEARNED.md - Iteration notes (add per phase)  

---

## File Locations

```
Project/
├── README.md          # Main entry (root only)
│
└── docs/
    ├── SETUP.md                 # Installation
    ├── README_EXPANDED.md       # Architecture
    ├── TROUBLESHOOTING.md       # Problems
    ├── VCF_PARSER_GUIDE.md      # API refs
    ├── LESSONS_LEARNED.md       # Per-phase notes
    └── ARCHITECTURE.md          # (Optional deep dive)
```

**Only one README.md at root level!**

## Documentation Separation Rules

- README.md = What + How to run
- README_EXPANDED.md = Why + Architecture
- API_GUIDE = What functions do
- TROUBLESHOOTING = Why errors happen
- LESSONS_LEARNED = Meta-learning

Never duplicate content across files.
Each document has a single responsibility.

## Anti-Bloat Rule

If a document exceeds:
- README: 300 lines
- SETUP: 3000 words
- API guide: 2000 lines

Refactor into sub-documents.