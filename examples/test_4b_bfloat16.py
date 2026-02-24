#!/usr/bin/env python3
"""Test 4B model with bfloat16 compute dtype (not float16)"""

import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)


def test_4b_bfloat16():
    """Test 4B model with bfloat16 compute dtype"""
    print("Loading 4B model with bfloat16 compute...")

    model_path = "/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma-1.5-4b-model"

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=True
    )

    # KEY FIX: use torch.bfloat16 for compute_dtype, not torch.float16
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,  # FIXED
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=quant_config,
        device_map="auto",
        local_files_only=True,
        trust_remote_code=True,
    )

    print("✓ Model loaded")
    print()

    # Test with chat template
    print("Test: Medical question with chat template")
    messages = [
        {"role": "system", "content": "You are a helpful medical assistant."},
        {
            "role": "user",
            "content": "What is the clinical significance of a BRCA1 c.5266dupC variant?",
        },
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    input_len = inputs["input_ids"].shape[-1]
    print(f"Input length: {input_len} tokens")

    with torch.inference_mode():
        generation = model.generate(**inputs, max_new_tokens=200, do_sample=False)
        generation = generation[0][input_len:]

    print(f"Generated token IDs (first 20): {generation[:20].tolist()}")
    print(f"All pad tokens? {all(tid == tokenizer.pad_token_id for tid in generation)}")

    decoded = tokenizer.decode(generation, skip_special_tokens=True)
    print(f"\nOutput:\n{decoded}\n")


if __name__ == "__main__":
    test_4b_bfloat16()
