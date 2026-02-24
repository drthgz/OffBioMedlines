#!/usr/bin/env python3
"""Test without quantization"""

import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from transformers import AutoTokenizer, AutoModelForCausalLM


def test_fp16():
    """Test with FP16 (no quantization)"""
    print("Loading 27B model in FP16 (no quantization)...")

    model_path = "/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma-27b-text-model"

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=True
    )

    # Load in FP16 without quantization
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        local_files_only=True,
        trust_remote_code=True,
        dtype=torch.float16,
    )

    print("✓ Model loaded in FP16")
    print()

    # Simple test
    print("Test: Simple text completion")
    text = "The BRCA1 gene"
    inputs = tokenizer(text, return_tensors="pt").to("cuda")

    print(f"Input: {text}")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=30,
            do_sample=False,
            pad_token_id=0,
            eos_token_id=1,
        )

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"Output: {generated}")
    print()

    input_len = inputs["input_ids"].shape[1]
    generated_ids = outputs[0][input_len:]
    print(f"Generated token IDs: {generated_ids.tolist()}")


if __name__ == "__main__":
    test_fp16()
