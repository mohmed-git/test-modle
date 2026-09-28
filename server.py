"""Lightweight Worker for RunPod Serverless MT Model Arena.

Supports both:
  1. RunPod Serverless Queue Mode (native `runpod.serverless.start`)
  2. Local / Pod HTTP Mode (FastAPI / uvicorn)

Reads configuration from environment variables:
  - ARENA_MODEL: HuggingFace model ID (default: "tencent/Hy-MT2-7B")
  - ARENA_QUANT: Quantization format (e.g. "fp8", "awq", "none")
  - PORT: HTTP port (default: 8000)
"""

import os
import sys
import time
from typing import Any, Optional
import torch

try:
    import runpod
    HAS_RUNPOD = True
except ImportError:
    HAS_RUNPOD = False

from engine import ArenaInferenceEngine, get_vram_info
from models_config import CANDIDATE_MODELS, ModelCandidate
from run_arena import CHATTER_SNIPPETS

# Configuration from Environment Variables
MODEL_ID = os.getenv("ARENA_MODEL", "tencent/Hy-MT2-7B")
QUANT = os.getenv("ARENA_QUANT", "none")
if QUANT and QUANT.lower() in ["none", "", "null"]:
    QUANT = None

ENGINE: Optional[ArenaInferenceEngine] = None
STARTUP_TIME = 0.0
STARTUP_ERROR = None

print("\n" + "=" * 80)
print(f"[*] Initializing MT Model Arena Worker...")
print(f"[*] Target Model : {MODEL_ID}")
print(f"[*] Quantization : {QUANT}")
print("=" * 80, flush=True)

try:
    t0 = time.perf_counter()
    ENGINE = ArenaInferenceEngine(
        model_id=MODEL_ID,
        quantization=QUANT,
        prefer_vllm=True,
    )
    # Warmup pass
    print("[*] Performing engine warmup...", flush=True)
    ENGINE.generate("Translate: مرحبا -> Hello", max_tokens=16)
    STARTUP_TIME = time.perf_counter() - t0
    print(f"[+] Worker successfully initialized in {STARTUP_TIME:.2f}s!", flush=True)
except Exception as exc:
    STARTUP_ERROR = str(exc)
    print(f"[!] Engine startup failed: {exc}", flush=True)


def format_model_prompt(text: str, source: str, target: str, candidate: ModelCandidate) -> str:
    lang_names = {
        "ar": "Arabic",
        "en": "English",
        "tr": "Turkish",
        "zh": "Chinese",
        "es": "Spanish",
    }
    src_name = lang_names.get(source, source)
    dst_name = lang_names.get(target, target)

    if candidate.system_prompt_type == "raw_mt":
        messages = [{"role": "user", "content": f"Translate the following text into {dst_name}:\n{text}"}]
    else:
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a professional real-time speech translator. "
                    f"Translate spoken {src_name} into fluent, natural {dst_name}. "
                    f"Preserve tone and colloquial idioms accurately. "
                    f"Output ONLY the direct translation without explanation."
                ),
            },
            {"role": "user", "content": text},
        ]

    # Try applying processor / tokenizer chat template if available
    target_proc = (getattr(ENGINE, "processor", None) or getattr(ENGINE, "tokenizer", None)) if ENGINE else None
    if target_proc and hasattr(target_proc, "apply_chat_template"):
        try:
            try:
                return target_proc.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            except TypeError:
                return target_proc.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception:
            pass

    # Fallback to direct prompt
    if candidate.system_prompt_type == "raw_mt":
        return f"Translate the following text into {dst_name}:\n{text}\nTranslation:"
    else:
        return (
            f"You are a professional real-time speech translator. "
            f"Translate spoken {src_name} into fluent {dst_name}. "
            f"Output ONLY the direct translation.\n\n"
            f"Source: {text}\n"
            f"Translation:"
        )


def process_request(job_input: dict[str, Any]) -> dict[str, Any]:
    """Core translation and health processing logic."""
    action = job_input.get("action", "translate")

    vram = get_vram_info()
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"

    if action in ["health", "ping"]:
        if STARTUP_ERROR:
            return {
                "status": "error",
                "error": STARTUP_ERROR,
                "model": MODEL_ID,
                "vram": vram,
                "gpu_name": gpu_name,
            }
        if ENGINE is None:
            return {
                "status": "loading",
                "model": MODEL_ID,
                "vram": vram,
                "gpu_name": gpu_name,
            }
        return {
            "status": "ready",
            "model": MODEL_ID,
            "quantization": QUANT,
            "backend": ENGINE.backend_name,
            "gpu_name": gpu_name,
            "vram": vram,
            "startup_time_s": round(STARTUP_TIME, 2),
        }

    # Action is translate
    if STARTUP_ERROR or ENGINE is None:
        return {
            "error": f"Model failed to load or is not ready: {STARTUP_ERROR or 'Still loading'}",
            "status": "error",
        }

    text = job_input.get("text") or job_input.get("prompt", "")
    if not text:
        return {"error": "Missing 'text' or 'prompt' in input", "status": "bad_request"}

    source = job_input.get("source", "ar")
    target = job_input.get("target", "en")
    max_tokens = int(job_input.get("max_tokens", 128))

    candidate = None
    for cand in CANDIDATE_MODELS.values():
        if cand.hf_model_id.lower() == MODEL_ID.lower() or cand.preset_id.lower() in MODEL_ID.lower():
            candidate = cand
            break

    if candidate is None:
        candidate = ModelCandidate(
            preset_id="custom",
            display_name=MODEL_ID,
            hf_model_id=MODEL_ID,
            architecture_type="unknown",
            active_params="unknown",
            total_params="unknown",
            recommended_quant=QUANT,
            notes="",
            system_prompt_type="raw_mt" if "hy-mt" in MODEL_ID.lower() else "translation_prompt",
        )

    prompt = format_model_prompt(text, source, target, candidate)
    res = ENGINE.generate(prompt, max_tokens=max_tokens)
    clean_text = res["text"].strip()
    for pfx in ["Translation:", "الترجمة:", "Output:"]:
        if clean_text.lower().startswith(pfx.lower()):
            clean_text = clean_text[len(pfx):].strip()

    has_leak = any(snip in clean_text.lower() for snip in CHATTER_SNIPPETS)

    return {
        "status": "ready",
        "translated_text": clean_text,
        "latency_ms": res["latency_ms"],
        "tokens": res["tokens"],
        "tokens_per_sec": res["tokens_per_sec"],
        "peak_vram_mb": res["peak_vram_mb"],
        "vram": vram,
        "gpu_name": gpu_name,
        "is_leak": has_leak,
        "model": MODEL_ID,
        "backend": ENGINE.backend_name,
    }


def handler(job: dict[str, Any]) -> dict[str, Any]:
    """RunPod Serverless Handler."""
    job_input = job.get("input", {})
    return process_request(job_input)


if __name__ == "__main__":
    is_runpod_serverless = os.getenv("RUNPOD_POD_ID") is not None or HAS_RUNPOD
    if is_runpod_serverless:
        print("[*] Starting RunPod Serverless Queue Worker...", flush=True)
        runpod.serverless.start({"handler": handler})
    else:
        print("[*] Starting local FastAPI server on port 8000...", flush=True)
        from fastapi import FastAPI
        from pydantic import BaseModel
        import uvicorn

        app = FastAPI(title="MT Arena Local")

        class Req(BaseModel):
            text: str
            source: str = "ar"
            target: str = "en"
            max_tokens: int = 128

        @app.get("/health")
        def api_health():
            return process_request({"action": "health"})

        @app.post("/translate")
        def api_translate(r: Req):
            return process_request({
                "action": "translate",
                "text": r.text,
                "source": r.source,
                "target": r.target,
                "max_tokens": r.max_tokens,
            })

        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
