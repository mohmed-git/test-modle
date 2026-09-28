"""MT Model Arena Benchmark Runner.

Executes the standardized canonical translation benchmark on any model and logs results.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from models_config import CANDIDATE_MODELS, ModelCandidate
from engine import ArenaInferenceEngine, get_vram_info

ARENA_DIR = Path(__file__).resolve().parent
DATASET_PATH = ARENA_DIR / "dataset" / "canonical_suite.jsonl"
RESULTS_DIR = ARENA_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CHATTER_SNIPPETS = [
    "as an ai", "i am an ai", "language model", "i cannot", "i apologize",
    "here is the translation", "translation:", "الترجمة:", "أنا نموذج", "ذكاء اصطناعي",
]


def format_prompt(item: dict[str, Any], candidate: ModelCandidate) -> str:
    """Format prompt based on model candidate type."""
    src = item.get("src", "ar")
    dst = item.get("dst", "en")
    text = item.get("text", "")

    lang_names = {
        "ar": "Arabic",
        "en": "English",
        "tr": "Turkish",
        "zh": "Chinese",
        "es": "Spanish",
    }
    src_name = lang_names.get(src, src)
    dst_name = lang_names.get(dst, dst)

    if candidate.system_prompt_type == "raw_mt":
        # Dedicated MT models (like Hy-MT2) often use direct prompt format
        return f"Translate from {src_name} to {dst_name}:\n{text}\nTranslation:"
    else:
        # Standard instruction-tuned LLMs
        return (
            f"You are a professional real-time speech translator. "
            f"Translate the following spoken {src_name} utterance into fluent, natural {dst_name}. "
            f"Preserve the tone, colloquial idioms, and intent accurately. "
            f"Output ONLY the direct translation without any explanation, markdown, or commentary.\n\n"
            f"Source: {text}\n"
            f"Translation:"
        )


def evaluate_sample(
    item: dict[str, Any],
    gen_result: dict[str, Any],
) -> dict[str, Any]:
    raw_output = gen_result["text"].strip()
    # Strip common prefixes if any
    clean_text = raw_output
    for pfx in ["Translation:", "الترجمة:", "Output:"]:
        if clean_text.lower().startswith(pfx.lower()):
            clean_text = clean_text[len(pfx):].strip()

    # Persona leak / chatter check
    lower_out = clean_text.lower()
    has_leak = any(snip in lower_out for snip in CHATTER_SNIPPETS)

    # Idiom preservation check
    key_idioms = item.get("key_idioms", [])
    lost_idioms = []
    # Check for known historical failure cases
    warn_hallucination = False
    if "والله باخذ كتاب" in item.get("text", ""):
        if "god took a book" in lower_out:
            warn_hallucination = True
            lost_idioms.append("Catastrophic: 'God took a book' literal translation")

    return {
        "id": item["id"],
        "category": item["category"],
        "src": item["src"],
        "dst": item["dst"],
        "input_text": item["text"],
        "output_text": clean_text,
        "latency_ms": gen_result["latency_ms"],
        "tokens": gen_result["tokens"],
        "tokens_per_sec": gen_result["tokens_per_sec"],
        "peak_vram_mb": gen_result["peak_vram_mb"],
        "is_leak": has_leak,
        "warn_hallucination": warn_hallucination,
        "key_idioms": key_idioms,
        "lost_idioms": lost_idioms,
    }


def run_benchmark(preset_id: str, custom_model_id: str = "", quant: str = ""):
    if preset_id in CANDIDATE_MODELS:
        candidate = CANDIDATE_MODELS[preset_id]
    else:
        candidate = ModelCandidate(
            preset_id=preset_id,
            display_name=preset_id,
            hf_model_id=custom_model_id or preset_id,
            architecture_type="unknown",
            active_params="unknown",
            total_params="unknown",
            recommended_quant=quant or "none",
            notes="Custom model execution",
            system_prompt_type="translation_prompt",
        )

    print("\n" + "=" * 90)
    print(f" [MT MODEL ARENA: EVALUATING {candidate.display_name.upper()}]")
    print(f" Model ID     : {candidate.hf_model_id}")
    print(f" Architecture : {candidate.architecture_type} ({candidate.active_params} active / {candidate.total_params} total)")
    print(f" Quantization : {quant or candidate.recommended_quant}")
    print("=" * 90)

    # Load Model
    engine = ArenaInferenceEngine(
        model_id=candidate.hf_model_id,
        quantization=quant or candidate.recommended_quant,
    )

    # Warmup
    print("\n[*] Warming up engine with 2 passes...")
    for _ in range(2):
        engine.generate("Translate: مرحبا -> Hello")

    # Load canonical dataset
    items = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))

    print(f"\n[*] Running {len(items)} canonical test cases...")
    print(f"{'ID':<18} | {'Cat':<22} | {'Tokens':<6} | {'MT(ms)':<8} | {'Tok/s':<7} | {'Leak':<6} | Output Snippet")
    print("-" * 105)

    sample_results = []
    short_latencies = []
    long_latencies = []
    all_latencies = []
    all_tps = []
    total_leaks = 0

    for it in items:
        prompt = format_prompt(it, candidate)
        gen_res = engine.generate(prompt)
        eval_res = evaluate_sample(it, gen_res)
        sample_results.append(eval_res)

        all_latencies.append(eval_res["latency_ms"])
        all_tps.append(eval_res["tokens_per_sec"])
        if eval_res["is_leak"]:
            total_leaks += 1

        if "SHORT_SPEED" in it["id"]:
            short_latencies.append(eval_res["latency_ms"])
        else:
            long_latencies.append(eval_res["latency_ms"])

        leak_str = "[LEAK]" if eval_res["is_leak"] else "CLEAN"
        snippet = eval_res["output_text"][:38].replace("\n", " ")
        print(f"{it['id']:<18} | {it['category'][:22]:<22} | {eval_res['tokens']:<6} | {eval_res['latency_ms']:<8.1f} | {eval_res['tokens_per_sec']:<7.1f} | {leak_str:<6} | {snippet}")

    # Summary Statistics
    avg_total_ms = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
    avg_short_ms = sum(short_latencies) / len(short_latencies) if short_latencies else 0.0
    avg_long_ms = sum(long_latencies) / len(long_latencies) if long_latencies else 0.0
    avg_tps = sum(all_tps) / len(all_tps) if all_tps else 0.0

    vram_after = get_vram_info()
    vram_used_gb = vram_after["used_gb"]
    vram_fit_24gb = "PASS (Safe)" if vram_used_gb <= 18.0 else ("TIGHT (18-21GB)" if vram_used_gb <= 21.0 else "DANGER / OOM")

    print("\n" + "=" * 90)
    print(f" [SUMMARY METRICS: {candidate.display_name}]")
    print(f" Resident VRAM        : {vram_used_gb:.2f} GB / {vram_after['total_gb']:.2f} GB ({vram_fit_24gb})")
    print(f" Avg Short MT Latency : {avg_short_ms:.1f} ms  (<=3 words)")
    print(f" Avg Long MT Latency  : {avg_long_ms:.1f} ms   (Complex / Dialects)")
    print(f" Overall Avg Latency  : {avg_total_ms:.1f} ms")
    print(f" Generation Speed     : {avg_tps:.1f} tokens/second")
    print(f" Persona Leaks        : {total_leaks} / {len(items)} ({(total_leaks/len(items))*100:.1f}%)")
    print("=" * 90)

    summary = {
        "preset_id": candidate.preset_id,
        "display_name": candidate.display_name,
        "hf_model_id": candidate.hf_model_id,
        "architecture_type": candidate.architecture_type,
        "active_params": candidate.active_params,
        "total_params": candidate.total_params,
        "backend": engine.backend_name,
        "quantization": quant or candidate.recommended_quant,
        "vram_used_gb": vram_used_gb,
        "vram_total_gb": vram_after["total_gb"],
        "vram_verdict_24gb": vram_fit_24gb,
        "avg_short_latency_ms": round(avg_short_ms, 1),
        "avg_long_latency_ms": round(avg_long_ms, 1),
        "overall_avg_latency_ms": round(avg_total_ms, 1),
        "avg_tokens_per_sec": round(avg_tps, 1),
        "persona_leaks_count": total_leaks,
        "total_cases": len(items),
        "leak_percentage": round((total_leaks / len(items)) * 100, 1),
        "timestamp": int(time.time()),
        "sample_evaluations": sample_results,
    }

    out_file = RESULTS_DIR / f"{candidate.preset_id}_eval.json"
    out_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[+] Saved evaluation results to: {out_file}")

    # Auto-generate leaderboard
    from generate_leaderboard import update_leaderboard
    update_leaderboard()


def main():
    parser = argparse.ArgumentParser(description="MT Model Arena Runner")
    parser.add_argument("--preset", choices=list(CANDIDATE_MODELS.keys()), default="hy-mt2-7b", help="Candidate model preset")
    parser.add_argument("--model", default="", help="Custom HuggingFace model path")
    parser.add_argument("--quant", default="", help="Quantization override (fp8, awq, none)")
    args = parser.parse_args()

    run_benchmark(preset_id=args.preset, custom_model_id=args.model, quant=args.quant)


if __name__ == "__main__":
    main()
