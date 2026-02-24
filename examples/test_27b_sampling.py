#!/usr/bin/env python3
"""Test with 4-bit quantization but bfloat16 compute dtype (not float16)"""

import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


def test_with_sampling():
    """Test with 4-bit quantization + bfloat16 compute dtype (official HF approach)"""
    print("Loading 27B model with 4-bit quantization + bfloat16 compute...")

    model_path = "/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma-27b-text-model"

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=True
    )

    # Key fix: use torch.bfloat16 for compute_dtype, not torch.float16
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,  # FIXED: was float16
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    # Reserve some GPU memory for inference, offload if needed
    max_memory = {0: "20GiB", "cpu": "32GiB"}

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=quant_config,
        device_map="auto",
        max_memory=max_memory,
        local_files_only=True,
        trust_remote_code=True,
    )

    print("✓ Model loaded")
    print()

    # Test 1: Official HF example approach
    print("Test 1: Medical question (official approach)")
    messages = [
        {"role": "system", "content": "You are a helpful medical assistant."},
        {
            "role": "user",
            "content": "How do you differentiate bacterial from viral pneumonia?",
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

    decoded = tokenizer.decode(generation, skip_special_tokens=True)
    print(f"Output:\n{decoded}\n")

    # Test 2: Cancer genomics question
    print("Test 2: BRCA1 variant interpretation")
    messages2 = [
        {"role": "system", "content": "You are a helpful medical assistant."},
        {
            "role": "user",
            "content": "What is the clinical significance of a BRCA1 c.5266dupC (p.Gln1756fs) variant?",
        },
    ]

    inputs2 = tokenizer.apply_chat_template(
        messages2,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    input_len2 = inputs2["input_ids"].shape[-1]

    with torch.inference_mode():
        generation2 = model.generate(**inputs2, max_new_tokens=200, do_sample=False)
        generation2 = generation2[0][input_len2:]

    decoded2 = tokenizer.decode(generation2, skip_special_tokens=True)
    print(f"Output:\n{decoded2}\n")


if __name__ == "__main__":
    test_with_sampling()
