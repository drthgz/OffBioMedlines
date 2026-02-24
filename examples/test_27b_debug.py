#!/usr/bin/env python3
"""Debug 27B model output"""

import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model.medgemma_inference import MedGemmaInference


def debug_generation():
    """Test with detailed token inspection"""
    print("Loading 27B model...")

    inference = MedGemmaInference(
        model_path="/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma-27b-text-model",
        use_4bit=True,
        temperature=0.0,
    )

    print(f"✓ Model loaded")
    print(f"  Tokenizer: {inference.tokenizer.__class__.__name__}")
    print(f"  Pad token ID: {inference.tokenizer.pad_token_id}")
    print(f"  EOS token ID: {inference.tokenizer.eos_token_id}")
    print(f"  BOS token ID: {inference.tokenizer.bos_token_id}")
    print()

    # Simple test prompt
    prompt = "What is BRCA1?"

    messages = [
        {"role": "system", "content": "You are a helpful medical assistant."},
        {"role": "user", "content": prompt},
    ]

    # Test tokenization
    print(f"Prompt: {prompt}")
    print()

    inputs = inference.tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(inference.device)

    input_ids = inputs["input_ids"][0]
    print(f"Input length: {len(input_ids)} tokens")
    print(f"Input tokens: {input_ids[:20].tolist()}")
    print(f"Decoded input: {inference.tokenizer.decode(input_ids[:100])}")
    print()

    # Generate with manual settings
    print("Generating (greedy, max_new_tokens=50)...")
    with torch.no_grad():
        outputs = inference.model.generate(
            **inputs,
            max_new_tokens=50,
            do_sample=False,
            pad_token_id=inference.tokenizer.pad_token_id,
            eos_token_id=inference.tokenizer.eos_token_id,
        )

    output_ids = outputs[0]
    print(f"Output length: {len(output_ids)} tokens")
    print(f"Output tokens: {output_ids.tolist()}")
    print()

    # Check for pad/eos tokens
    generated_ids = output_ids[len(input_ids) :]
    print(f"Generated {len(generated_ids)} tokens")
    print(f"Generated tokens: {generated_ids.tolist()}")
    print()

    unique_tokens = set(generated_ids.tolist())
    print(f"Unique generated tokens: {unique_tokens}")
    print()

    # Decode
    generated_text = inference.tokenizer.decode(generated_ids, skip_special_tokens=True)
    print("Generated text:")
    print(f"'{generated_text}'")
    print()

    # Also try full decode
    full_text = inference.tokenizer.decode(output_ids, skip_special_tokens=False)
    print("Full output (with special tokens):")
    print(full_text)
    print()


if __name__ == "__main__":
    debug_generation()
