---
name: medical-validation
description: Validates MedGemma model outputs against clinical benchmarks and Kaggle competition criteria. Use this when evaluating fine-tuned model performance or checking notebook outputs for accuracy.
---

# Medical Validation Protocol

## 1. Clinical Accuracy Check
Evaluate the output against established medical benchmarks used for MedGemma 1.5:
- **Imaging Findings**: Must align with standard radiological report formats (e.g., identifying 18 conditions for CT-RATE or 5 for MIMIC CXR).
- **Histopathology**: Check if text generation aligns with ROUGE-L targets (baseline ~0.49 for MedGemma 1.5).
- **Localization**: Verify that anatomical features in X-rays are correctly localized (IOU benchmarks).

## 2. Competitive Rubric Alignment
Ensure the solution addresses these specific [Kaggle Hackathon criteria](https://www.kaggle.com/competitions/med-gemma-impact-challenge
):
- **Human-Centered AI**: Does the output provide reasoning/explanations, not just a label?
- **Agentic Workflow**: Is MedGemma being used as an "intelligent agent" or "callable tool"?
- **Practicality**: Does the documentation address deployment challenges and real-world usage beyond just benchmarking?

## 3. Technical Verification
- **Output Consistency**: Check for "single-token repetition" or "mode collapse" (common in 4B-IT fine-tuning).
- **Resource Efficiency**: Confirm optimizations for Kaggle's memory limits (e.g., 4-bit LoRA, frozen vision towers).

## 4. Safety & Ethics
- All outputs must include a disclaimer that they are not intended for direct clinical diagnosis.
- Ensure no PII (Personally Identifiable Information) is included in the evaluation examples.
