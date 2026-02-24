#!/usr/bin/env python3
"""Test 27B without chat template"""

import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


def test_raw_generation():
    """Test generation without chat template"""
    print("Loading 27B model...")

    model_path = "/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma-27b-text-model"

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=True
    )

    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=quant_config,
        device_map="auto",
        local_files_only=True,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )

    print("✓ Model loaded")
    print()

    # Test 1: Simple continuation
    print("Test 1: Simple continuation")
    text = "BRCA1 is a"
    inputs = tokenizer(text, return_tensors="pt").to("cuda")

    print(f"Input: {text}")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=30,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"Output: {generated}")
    print()

    # Test 2: Medical question
    print("Test 2: Medical question")
    text = "Q: What is the function of BRCA1? A:"
    inputs = tokenizer(text, return_tensors="pt").to("cuda")

    print(f"Input: {text}")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"Output: {generated}")
    print()

    # Test 3: Look at token IDs
    print("Test 3: Token ID analysis")
    output_ids = outputs[0]
    input_len = inputs["input_ids"].shape[1]
    generated_ids = output_ids[input_len:]

    print(f"Generated token IDs: {generated_ids.tolist()}")
    print(
        f"Are all pad tokens? {all(tid == tokenizer.pad_token_id for tid in generated_ids)}"
    )


if __name__ == "__main__":
    test_raw_generation()
