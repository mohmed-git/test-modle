"""Candidate Models Configuration for MT Model Arena.

Maps presets to exact Hugging Face model IDs, default quantizations, and prompt templates.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelCandidate:
    preset_id: str
    display_name: str
    hf_model_id: str
    architecture_type: str  # "moe", "dense", "dedicated_mt", "multimodal"
    active_params: str
    total_params: str
    recommended_quant: Optional[str]  # "fp8", "awq", "none"
    notes: str
    system_prompt_type: str  # "translation_prompt", "raw_mt"


CANDIDATE_MODELS = {
    "hy-mt2-7b": ModelCandidate(
        preset_id="hy-mt2-7b",
        display_name="Tencent Hy-MT2-7B",
        hf_model_id="tencent/Hy-MT2-7B",
        architecture_type="dedicated_mt",
        active_params="7B",
        total_params="7B",
        recommended_quant="none",  # ~15.4 GB in bf16
        notes="Dedicated Translation model by Tencent Hunyuan. Zero chatter, native MT.",
        system_prompt_type="raw_mt",
    ),
    "hy-mt2-30b-a3b": ModelCandidate(
        preset_id="hy-mt2-30b-a3b",
        display_name="Tencent Hy-MT2-30B-A3B",
        hf_model_id="tencent/Hy-MT2-30B-A3B",
        architecture_type="dedicated_mt",
        active_params="3B",
        total_params="30B",
        recommended_quant="fp8",  # ~18 GB
        notes="Tencent Hunyuan MoE dedicated MT. Massive vocabulary with 3B active inference.",
        system_prompt_type="raw_mt",
    ),
    "qwen3-30b-a3b": ModelCandidate(
        preset_id="qwen3-30b-a3b",
        display_name="Alibaba Qwen3-30B-A3B",
        hf_model_id="Qwen/Qwen3-30B-A3B-Instruct-2507-FP8",
        architecture_type="moe",
        active_params="3.3B",
        total_params="30.5B",
        recommended_quant="fp8",  # ~20.88 GB
        notes="Alibaba next-gen MoE. Strong reasoning & dialect understanding.",
        system_prompt_type="translation_prompt",
    ),
    "qwen3.6-35b-a3b": ModelCandidate(
        preset_id="qwen3.6-35b-a3b",
        display_name="Alibaba Qwen3.6-35B-A3B",
        hf_model_id="Qwen/Qwen3.6-35B-A3B",
        architecture_type="moe",
        active_params="3.0B",
        total_params="35B",
        recommended_quant="fp8",  # ~19.5 GB
        notes="Updated 2026 MoE from Qwen with multimodal and agentic improvements.",
        system_prompt_type="translation_prompt",
    ),
    "gemma4-26b-a4b": ModelCandidate(
        preset_id="gemma4-26b-a4b",
        display_name="Google Gemma 4 26B-A4B-it",
        hf_model_id="google/gemma-4-26B-A4B-it",
        architecture_type="multimodal_moe",
        active_params="3.8B",
        total_params="25.2B",
        recommended_quant="fp8",  # ~14.4 GB
        notes="Google DeepMind 2026 MoE architecture with 140+ language support.",
        system_prompt_type="translation_prompt",
    ),
    "gemma4-e4b": ModelCandidate(
        preset_id="gemma4-e4b",
        display_name="Google Gemma 4 E4B-it",
        hf_model_id="google/gemma-4-E4B-it",
        architecture_type="multimodal_dense",
        active_params="4B",
        total_params="4B",
        recommended_quant="none",  # ~5 GB in bf16
        notes="Google DeepMind Edge model. Lightweight, high token throughput.",
        system_prompt_type="translation_prompt",
    ),
    "gemma4-e2b": ModelCandidate(
        preset_id="gemma4-e2b",
        display_name="Google Gemma 4 E2B-it",
        hf_model_id="google/gemma-4-E2B-it",
        architecture_type="multimodal_dense",
        active_params="2B",
        total_params="2B",
        recommended_quant="none",  # ~3 GB in bf16
        notes="Ultra-lightweight edge model. Minimal VRAM footprint.",
        system_prompt_type="translation_prompt",
    ),
    "gemma-4-e2b": ModelCandidate(
        preset_id="gemma-4-e2b",
        display_name="Google Gemma 4 E2B",
        hf_model_id="google/gemma-4-E2B",
        architecture_type="multimodal_dense",
        active_params="2B",
        total_params="2B",
        recommended_quant="none",
        notes="Ultra-lightweight base edge model.",
        system_prompt_type="translation_prompt",
    ),
}
