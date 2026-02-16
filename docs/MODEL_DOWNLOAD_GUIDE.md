# MedGemma Model Download Guide

## Quick Start

### 1. Prerequisites ✓
- ✅ `.env` file with `HUGGINGFACE_TOKEN=hf_...` 
- ✅ ~10-15 GB free disk space
- ✅ Internet connection (5-10 min download)

### 2. Run the Notebook in Order

**Step-by-step:**

1. **Section 1: Setup & Model Download** (runs first)
   ```
   Cell 1: Core imports
   Cell 2: Configure paths
   Cell 3: Check environment
   Cell 4: Validate token ← NEW! Downloads model here
   ```

2. **Section 2: Load MedGemma Model** (runs second)
   - Loads the cached model
   - Applies 4-bit quantization (~3-4 GB memory)
   - Ready for inference

3. **Section 3+**: Run analysis!

### 3. What the Download Section Does

The new **"Download Model from HuggingFace"** cell performs these steps:

```
Step 1: ✓ Validate your HuggingFace token from .env
Step 2: ✓ Authenticate with HuggingFace servers
Step 3: ✓ Download tokenizer (~100 MB)
Step 4: ✓ Download model weights (~8 GB)
        (takes 5-15 minutes depending on connection)
```

After download:
- Model cached in: `/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma/`
- **One-time only** - subsequent runs use cached version (instant!)
- Shows download progress and file status

### 4. Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| **Token not found** | Make sure `.env` has `HUGGINGFACE_TOKEN=hf_...` and restart kernel |
| **Download hangs** | Normal if slow connection (can take 15+ min) - give it time |
| **"License not accepted"** | Visit https://huggingface.co/google/medgemma-1.5-4b-it and click "I agree" |
| **Disk space error** | Free up 15 GB - model needs room to download and decompress |
| **Network timeout** | Restart that cell - it will resume from where it left off |

### 5. Understanding the Model Storage

```
data/models/medgemma/
├── config.json              (model configuration)
├── model.safetensors        (weights file - ~8 GB)
├── tokenizer.json           (vocabulary)
├── tokenizer.model          (BPE tokenizer)
└── ... (other metadata files)
```

**Key file: `model.safetensors`** (~8 GB) - contains the actual model weights

### 6. Next: Loading & Quantizing

Once downloaded, the next section (Section 2) will:

```python
1. Load model from cache (fast - already downloaded)
2. Apply 4-bit quantization (reduces 8GB → 3-4GB)
3. Move to GPU/CPU (ready for inference)
```

### 7. Offline Usage

**After first download, you can run offline!** 
- Model is cached locally
- No internet needed for inference
- Token only used for initial download

### 8. Kaggle vs Local

| Kaggle Notebook | Local Machine |
|----------------|---------------|
| Model pre-added as dataset | Need to download (this guide) |
| Instant access | ~5-15 min first-time download |
| HF token not needed | HF token required |
| Can submit directly | Need to export results |

---

## Progress Tracking

As you run the download cell, you'll see:

```
================================================================
🔐 Step 1: Validating HuggingFace Authentication
================================================================
✓ Token found (length: 37 chars)

================================================================
🔗 Step 2: Authenticating with HuggingFace
================================================================
✓ Successfully logged in to HuggingFace

================================================================
📥 Step 3: Downloading Tokenizer
================================================================
✓ Tokenizer downloaded successfully

================================================================
📥 Step 4: Downloading MedGemma Model
================================================================
⏳ This may take 5-15 minutes... ☕

✓ Model downloaded successfully!
  Model size: 8.50 GB (full precision)
  Parameters: 4.00B

================================================================
✅ Download Complete!
================================================================
```

## Storage Location

All models cached in: `~/.cache/huggingface/hub/` 

**But for this project, also stored in:**
```
/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma/
```

This keeps everything in your project directory—easier to backup & transfer!

---

## Tips

- 💡 **Speed up download**: Use ethernet instead of WiFi when possible
- 💾 **Save bandwidth**: Download on home networking, not mobile hotspot
- 🔄 **Resume interrupted**: Just re-run the cell - it picks up where it left off
- 📊 **Monitor progress**: Watch terminal output for status updates
- ☕ **Be patient**: First download is ~10 mins, totally normal

Ready? Run the notebook section-by-section! 🚀
