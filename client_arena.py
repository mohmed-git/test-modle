"""Client Benchmarking Runner for MT Model Arena.

Connects to the remote RunPod Serverless endpoint, runs all 20 canonical benchmark items,
measures latency, evaluates translation quality, saves JSON, and updates LEADERBOARD.md.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from generate_leaderboard import update_leaderboard

ARENA_DIR = Path(__file__).resolve().parent
DATASET_PATH = ARENA_DIR / "dataset" / "canonical_suite.jsonl"
RESULTS_DIR = ARENA_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]+", "_", name.lower()).strip("_")


def evaluate_sample(item: dict[str, Any], resp_data: dict[str, Any], e2e_ms: float) -> dict[str, Any]:
    output_text = resp_data.get("translated_text", "").strip()
    latency_ms = float(resp_data.get("latency_ms", 0.0) or e2e_ms)
    tokens = int(resp_data.get("tokens", 0))
    tps = float(resp_data.get("tokens_per_sec", 0.0))
    is_leak = bool(resp_data.get("is_leak", False))

    lower_out = output_text.lower()
    warn_hallucination = False
    lost_idioms = []

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
        "output_text": output_text,
        "latency_ms": latency_ms,
        "tokens": tokens,
        "tokens_per_sec": tps,
        "is_leak": is_leak,
        "warn_hallucination": warn_hallucination,
        "key_idioms": item.get("key_idioms", []),
        "lost_idioms": lost_idioms,
    }


def run_client_benchmark(url: str, token: str = ""):
    base_url = url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    print("\n" + "=" * 90)
    print(f" [MT MODEL ARENA: RUNNING BENCHMARK VIA SERVERLESS ENDPOINT]")
    print(f" Target Endpoint : {base_url}")
    print("=" * 90)

    # 1. Health & Model Discovery
    print("[*] Checking endpoint health and discovering model...")
    with httpx.Client(timeout=30.0) as client:
        try:
            r = client.get(f"{base_url}/health", headers=headers)
        except Exception as exc:
            print(f"[!] Failed to connect to {base_url}/health: {exc}")
            return

    if r.status_code != 200:
        print(f"[!] Server not ready. Status: HTTP {r.status_code} - {r.text}")
        return

    health = r.json()
    model_name = health.get("model", "unknown_model")
    gpu_name = health.get("gpu_name", "Unknown GPU")
    vram = health.get("vram", {})
    used_gb = vram.get("used_gb", 0.0)
    total_gb = vram.get("total_gb", 0.0)

    vram_verdict = "PASS (Safe)" if used_gb <= 18.0 else ("TIGHT (18-21GB)" if used_gb <= 21.0 else "DANGER / OOM")

    print(f"      Loaded Model : {model_name}")
    print(f"      GPU Hardware : {gpu_name}")
    print(f"      VRAM Usage   : {used_gb:.2f} GB / {total_gb:.2f} GB ({vram_verdict})")

    # 2. Load canonical dataset
    items = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))

    print(f"\n[*] Executing {len(items)} canonical test cases against endpoint...")
    print(f"{'ID':<18} | {'Cat':<22} | {'Tokens':<6} | {'MT(ms)':<8} | {'Tok/s':<7} | {'Leak':<6} | Output Snippet")
    print("-" * 105)

    sample_results = []
    short_latencies = []
    long_latencies = []
    all_latencies = []
    all_tps = []
    total_leaks = 0

    with httpx.Client(timeout=45.0) as client:
        for it in items:
            payload = {
                "text": it["text"],
                "source": it["src"],
                "target": it["dst"],
            }
            t0 = time.perf_counter()
            resp = client.post(f"{base_url}/translate", json=payload, headers=headers)
            e2e_ms = (time.perf_counter() - t0) * 1000.0

            if resp.status_code == 200:
                resp_data = resp.json()
            else:
                resp_data = {"translated_text": f"ERROR: HTTP {resp.status_code}", "latency_ms": e2e_ms}

            eval_res = evaluate_sample(it, resp_data, e2e_ms)
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

    # Summary
    avg_total_ms = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
    avg_short_ms = sum(short_latencies) / len(short_latencies) if short_latencies else 0.0
    avg_long_ms = sum(long_latencies) / len(long_latencies) if long_latencies else 0.0
    avg_tps = sum(all_tps) / len(all_tps) if all_tps else 0.0

    print("\n" + "=" * 90)
    print(f" [EVALUATION SUMMARY: {model_name}]")
    print(f" Resident VRAM        : {used_gb:.2f} GB / {total_gb:.2f} GB ({vram_verdict})")
    print(f" Avg Short MT Latency : {avg_short_ms:.1f} ms  (<=3 words)")
    print(f" Avg Long MT Latency  : {avg_long_ms:.1f} ms   (Complex / Dialects)")
    print(f" Overall Avg Latency  : {avg_total_ms:.1f} ms")
    print(f" Generation Speed     : {avg_tps:.1f} tokens/second")
    print(f" Persona Leaks        : {total_leaks} / {len(items)} ({(total_leaks/len(items))*100:.1f}%)")
    print("=" * 90)

    model_slug = slugify(model_name)
    summary = {
        "preset_id": model_slug,
        "display_name": model_name,
        "hf_model_id": model_name,
        "architecture_type": "moe" if "moe" in model_name.lower() or "a3b" in model_name.lower() or "a4b" in model_name.lower() else "dense",
        "active_params": "3B" if "a3b" in model_name.lower() else ("4B" if "a4b" in model_name.lower() or "e4b" in model_name.lower() else "7B"),
        "total_params": "30B" if "30b" in model_name.lower() else ("35B" if "35b" in model_name.lower() else "7B"),
        "backend": health.get("backend", "vllm"),
        "quantization": health.get("quantization", "none"),
        "vram_used_gb": used_gb,
        "vram_total_gb": total_gb,
        "vram_verdict_24gb": vram_verdict,
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

    out_file = RESULTS_DIR / f"{model_slug}_eval.json"
    out_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[+] Saved evaluation report to: {out_file}")

    # Auto-update leaderboard
    update_leaderboard()


def main():
    parser = argparse.ArgumentParser(description="MT Arena Serverless Client Runner")
    parser.add_argument("--url", required=True, help="Base URL of Serverless endpoint (e.g. https://xxxx.api.runpod.ai)")
    parser.add_argument("--token", default="", help="Authorization Bearer Token if required")
    args = parser.parse_args()

    run_client_benchmark(url=args.url, token=args.token)


if __name__ == "__main__":
    main()
