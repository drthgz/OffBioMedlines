"""
MedGemma Inference Module

Loads and manages Google's MedGemma biomedical language model for variant
interpretation and clinical reasoning.

Features:
- Local model loading (no internet required)
- 4-bit quantization support for memory efficiency
- Batched inference for throughput
- Clinical prompt templates
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

logger = logging.getLogger(__name__)


class MedGemmaInference:
    """
    MedGemma model inference engine

    Loads Google's MedGemma medical language model and provides inference
    for clinical variant interpretation.

    Example:
        >>> inference = MedGemmaInference(model_path="data/models/medgemma")
        >>> response = inference.generate("Analyze BRCA1 c.185A>G variant...")
        >>> print(response)
    """

    def __init__(
        self,
        model_path: str = "/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma/models--google--medgemma-1.5-4b-it/snapshots/e9792da5fb8ee651083d345ec4bce07c3c9f1641",
        use_4bit: bool = True,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        device: Optional[str] = None,
    ):
        """
        Initialize MedGemma inference engine

        Args:
            model_path: Path to downloaded MedGemma model
            use_4bit: Use 4-bit quantization (reduces memory from 16GB to 4GB)
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing MedGemma from {model_path}")
        logger.info(f"Device: {self.device}")
        logger.info(f"4-bit quantization: {use_4bit}")

        # Load tokenizer
        self.tokenizer = self._load_tokenizer()

        # Load model
        self.model = self._load_model(use_4bit=use_4bit)

        logger.info("MedGemma loaded successfully")

    def _load_tokenizer(self) -> AutoTokenizer:
        """Load MedGemma tokenizer"""
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, local_files_only=True, trust_remote_code=True
            )

            # Set padding token if not defined
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            logger.info("Tokenizer loaded successfully")
            return tokenizer

        except Exception as e:
            logger.error(f"Failed to load tokenizer: {str(e)}")
            raise

    def _load_model(self, use_4bit: bool = True) -> AutoModelForCausalLM:
        """Load MedGemma model with optional quantization"""
        try:
            # Configure quantization
            quantization_config = None
            if use_4bit and self.device == "cuda":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                logger.info("Using 4-bit quantization (NF4)")

            # Load model
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                quantization_config=quantization_config,
                device_map="auto" if self.device == "cuda" else None,
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )

            # Move to device if CPU
            if self.device == "cpu":
                model = model.to(self.device)

            model.eval()  # Set to evaluation mode

            logger.info(f"Model loaded on {self.device}")
            return model

        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

    def generate(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate response from MedGemma

        Args:
            prompt: Input prompt for variant analysis
            max_new_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            Generated text response
        """
        max_tokens = max_new_tokens or self.max_new_tokens
        temp = temperature or self.temperature

        try:
            # Format prompt using chat template
            messages = [{"role": "user", "content": prompt}]
            formatted_prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            # Tokenize input
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,  # MedGemma context window
            ).to(self.device)

            # Generate response - use greedy decoding for stability
            with torch.no_grad():
                if temp <= 0.1:  # Greedy decoding
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_tokens,
                        do_sample=False,
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )
                else:  # Sampling with safer parameters
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_tokens,
                        temperature=temp,
                        do_sample=True,
                        top_p=0.95,
                        top_k=50,
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )

            # Decode response
            # Debug: print token counts
            input_length = inputs["input_ids"].shape[1]
            output_length = outputs[0].shape[0]
            generated_length = output_length - input_length
            logger.info(
                f"Generated {generated_length} tokens (input: {input_length}, output: {output_length})"
            )

            # Decode full output for debugging
            full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
            logger.debug(f"Full output with special tokens: {full_output[:200]}")

            # Decode only new tokens
            response = self.tokenizer.decode(
                outputs[0][input_length:],  # Only new tokens
                skip_special_tokens=True,
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            return f"Error during inference: {str(e)}"

    def batch_generate(
        self,
        prompts: List[str],
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> List[str]:
        """
        Generate responses for multiple prompts (batched)

        Args:
            prompts: List of input prompts
            max_new_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            List of generated responses
        """
        max_tokens = max_new_tokens or self.max_new_tokens
        temp = temperature or self.temperature

        try:
            # Tokenize all prompts
            inputs = self.tokenizer(
                prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048,
            ).to(self.device)

            # Generate responses
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temp,
                    do_sample=True if temp > 0 else False,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            # Decode all responses
            responses = []
            for i, output in enumerate(outputs):
                response = self.tokenizer.decode(
                    output[inputs["input_ids"][i].shape[0] :], skip_special_tokens=True
                )
                responses.append(response.strip())

            return responses

        except Exception as e:
            logger.error(f"Batch generation failed: {str(e)}")
            return [f"Error during inference: {str(e)}"] * len(prompts)


# Global model instance (singleton pattern)
_global_inference_engine: Optional[MedGemmaInference] = None


def get_inference_engine(
    model_path: Optional[str] = None, use_4bit: bool = True, force_reload: bool = False
) -> MedGemmaInference:
    """
    Get or create global MedGemma inference engine

    Args:
        model_path: Path to model (uses default if None)
        use_4bit: Use 4-bit quantization
        force_reload: Force reload even if already loaded

    Returns:
        MedGemmaInference instance
    """
    global _global_inference_engine

    if _global_inference_engine is None or force_reload:
        if model_path is None:
            model_path = "/home/shiftmint/Documents/kaggle/medAi_google/data/models/medgemma/models--google--medgemma-1.5-4b-it/snapshots/e9792da5fb8ee651083d345ec4bce07c3c9f1641"

        _global_inference_engine = MedGemmaInference(
            model_path=model_path, use_4bit=use_4bit
        )

    return _global_inference_engine


def create_inference_function(model_path: Optional[str] = None, use_4bit: bool = True):
    """
    Create inference function for agents

    Args:
        model_path: Path to MedGemma model
        use_4bit: Use 4-bit quantization

    Returns:
        Callable that takes prompt and returns response
    """
    engine = get_inference_engine(model_path=model_path, use_4bit=use_4bit)

    def inference_fn(prompt: str) -> str:
        return engine.generate(prompt)

    return inference_fn


# Convenience function for simple usage
def medgemma_inference(prompt: str, model_path: Optional[str] = None) -> str:
    """
    Simple inference function - loads model on first call

    Args:
        prompt: Input prompt
        model_path: Optional path to model

    Returns:
        Generated response
    """
    engine = get_inference_engine(model_path=model_path)
    return engine.generate(prompt)
