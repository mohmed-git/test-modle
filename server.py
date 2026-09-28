"""Lightweight FastAPI Server for RunPod Serverless MT Model Arena.

Reads model configuration from environment variables:
  - ARENA_MODEL: HuggingFace model ID (default: "tencent/Hy-MT2-7B")
  - ARENA_QUANT: Quantization format (e.g. "fp8", "awq", "none")
  - PORT: HTTP port (default: 8000)
"""

import os
import sys
import time
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import torch

from engine import ArenaInferenceEngine, get_vram_info
from models_config import CANDIDATE_MODELS, ModelCandidate
from run_arena import format_prompt, CHATTER_SNIPPETS

app = FastAPI(title="MT Model Arena Serverless Worker")

# Configuration from Environment Variables
MODEL_ID = os.getenv("ARENA_MODEL", "tencent/Hy-MT2-7B")
QUANT = os.getenv("ARENA_QUANT", "none")
if QUANT.lower() in ["none", "", "null"]:
    QUANT = None

ENGINE: Optional[ArenaInferenceEngine] = None
STARTUP_TIME = 0.0
STARTUP_ERROR = None


class TranslateRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    source: str = Field(default="ar", description="Source language code")
    target: str = Field(default="en", description="Target language code")
    max_tokens: int = Field(default=128, description="Max generated tokens")


@app.on_event("startup")
def startup_event():
    global ENGINE, STARTUP_TIME, STARTUP_ERROR
    print("\n" + "=" * 80)
    print(f"[*] Starting MT Arena Serverless Worker...")
    print(f"[*] Target Model : {MODEL_ID}")
    print(f"[*] Quantization : {QUANT}")
    print("=" * 80)

    t0 = time.perf_counter()
    try:
        ENGINE = ArenaInferenceEngine(
            model_id=MODEL_ID,
            quantization=QUANT,
            prefer_vllm=True,
        )
        # Warmup pass
        print("[*] Warming up worker...")
        ENGINE.generate("Translate: مرحبا -> Hello")
        STARTUP_TIME = time.perf_counter() - t0
        print(f"[+] Worker ready in {STARTUP_TIME:.2f}s!")
    except Exception as exc:
        STARTUP_ERROR = str(exc)
        print(f"[!] Startup failed: {exc}")


@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.get("/health")
def health():
    vram = get_vram_info()
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"

    if STARTUP_ERROR:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": STARTUP_ERROR, "vram": vram, "gpu_name": gpu_name},
        )
    if ENGINE is None:
        return JSONResponse(
            status_code=503,
            content={"status": "loading", "model": MODEL_ID, "vram": vram, "gpu_name": gpu_name},
        )

    return {
        "status": "ready",
        "model": MODEL_ID,
        "quantization": QUANT,
        "backend": ENGINE.backend_name,
        "gpu_name": gpu_name,
        "vram": vram,
        "startup_time_s": round(STARTUP_TIME, 2),
    }


@app.post("/translate")
def translate(req: TranslateRequest):
    if ENGINE is None:
        return JSONResponse(status_code=503, content={"error": "Model not ready"})

    # Check candidate prompt config
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

    item = {"src": req.source, "dst": req.target, "text": req.text}
    prompt = format_prompt(item, candidate)

    res = ENGINE.generate(prompt, max_tokens=req.max_tokens)
    clean_text = res["text"].strip()
    for pfx in ["Translation:", "الترجمة:", "Output:"]:
        if clean_text.lower().startswith(pfx.lower()):
            clean_text = clean_text[len(pfx):].strip()

    has_leak = any(snip in clean_text.lower() for snip in CHATTER_SNIPPETS)

    return {
        "translated_text": clean_text,
        "latency_ms": res["latency_ms"],
        "tokens": res["tokens"],
        "tokens_per_sec": res["tokens_per_sec"],
        "peak_vram_mb": res["peak_vram_mb"],
        "is_leak": has_leak,
        "model": MODEL_ID,
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")
