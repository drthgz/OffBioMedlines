# HuggingFace Token Setup Guide

## Quick Steps

### 1. Get Your HuggingFace API Token

1. Visit: https://huggingface.co/settings/tokens
2. Click **"New token"** button
3. Fill in:
   - **Name**: `medgemma_token`
   - **Role**: **Select "read"** (dropdown on the right)
   - Other fields: Leave as default
4. Click **"Create token"**
5. Copy the token value (starts with `hf_`)

### 2. Create `.env` File

In your project root (`/home/shiftmint/Documents/kaggle/medAi_google/`), create a file named `.env`:

```text
HUGGINGFACE_TOKEN=hf_your_actual_token_here_XXXXXXXXXXXXXXXXXX
```

Replace `hf_your_actual_token_here_XXXXXXXXXXXXXXXXXX` with your actual token.

**Example (NOT real):**
```text
HUGGINGFACE_TOKEN=hf_AbC123dEfGhIjKlMnOpQrStUvWxYz789_aBc
```

### 3. Verify Setup

Run the first cell of `medgemma_integration.ipynb`. You should see:
```
✓ HuggingFace token loaded from .env
```

## Why "read" Permission Only?

| Permission | Use Case | Your Project |
|-----------|----------|--------------|
| **read** | Download models, datasets | ✅ You need this |
| **write** | Create/upload models | ❌ Not needed |
| **repo_write** | Upload to repos | ❌ Not needed |
| **inference** | Run inference APIs | ❌ Local only |
| **fine-grained** | Complex permissions | ❌ Unnecessary |

**"read"** is sufficient and follows the principle of least privilege (best security practice).

## What About `.env.example`?

The `.env.example` file shows the structure but isn't secret. It's safe to commit to git.
Your `.env` file (with real token) is **excluded from git** by `.gitignore` - kept private.

## Troubleshooting

**Q: Token not working?**
- Verify token starts with `hf_`
- Check for extra spaces in `.env` file
- Restart notebook kernel after creating `.env`

**Q: FileNotFoundError for .env?**
- Make sure `.env` is in project root (same folder as `notebooks/`, `docs/`, etc.)
- Run from project root, not subdirectories

**Q: Still can't download model?**
- Run: `huggingface-cli login` in terminal, paste token when prompted
- Or run: `python -c "from huggingface_hub import login; login()"`

## Security Best Practices

✅ **DO:**
- Keep `.env` in `.gitignore` (it already is)
- Rotate tokens periodically
- Use "read" permission (minimal privilege)
- Use environment variables instead of hardcoding

❌ **DON'T:**
- Commit `.env` to git
- Share your token publicly
- Use tokens in code/notebooks (use env vars instead)
- Use higher permissions than needed

## Next Steps

Once `.env` is set up:
1. Restart the notebook kernel
2. Run first cell - should show "✓ HuggingFace token loaded"
3. Run Section 2 cells to download/load medgemma-1.5-4b-it
4. Proceed with model testing and inference

Good luck! 🚀
