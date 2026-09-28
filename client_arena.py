"""Client Benchmarking Runner for MT Model Arena.

Connects to the remote RunPod Serverless endpoint (or local instance),
runs all 20 canonical benchmark items, measures exact latency and throughput,
evaluates translation quality and dialect fidelity, saves JSON, and updates LEADERBOARD.md.
"""

import argparse
import json
import os
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

DEFAULT_RUNPOD_KEY = os.getenv("RUNPOD_API_KEY", "")


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]+", "_", name.lower()).strip("_")


class ArenaClient:
    def __init__(self, target: str, token: str = ""):
        self.raw_target = target.strip()
        self.token = token.strip() or DEFAULT_RUNPOD_KEY
        self.is_runpod = False
        self.endpoint_id = ""
        self.runsync_url = ""
        self.status_base_url = ""
        self.http_base_url = ""

        self._resolve_target()

    def _resolve_target(self):
        target = self.raw_target
        # Check if user passed bare endpoint ID like 7huftovs9aage6
        if re.match(r"^[a-z0-9]{10,20}$", target):
            self.is_runpod = True
            self.endpoint_id = target
            self.runsync_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/runsync"
            self.status_base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status"
            return

        if "api.runpod.ai" in target:
            self.is_runpod = True
            m = re.search(r"/v2/([a-z0-9]+)", target)
            if m:
                self.endpoint_id = m.group(1)
            else:
                self.endpoint_id = "unknown"
            self.runsync_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/runsync"
            self.status_base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status"
            return

        # Direct HTTP mode (FastAPI or proxy)
        self.is_runpod = False
        self.http_base_url = target.rstrip("/")

    def call_endpoint(self, job_input: dict[str, Any], timeout_s: float = 120.0) -> dict[str, Any]:
        """Send job to endpoint and wait for completion."""
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        if not self.is_runpod:
            action = job_input.get("action", "translate")
            with httpx.Client(timeout=timeout_s) as client:
                if action == "health":
                    r = client.get(f"{self.http_base_url}/health", headers=headers)
                else:
                    r = client.post(f"{self.http_base_url}/translate", json=job_input, headers=headers)
                r.raise_for_status()
                return r.json()

        # RunPod Queue Mode
        with httpx.Client(timeout=60.0) as client:
            t0 = time.perf_counter()
            r = client.post(self.runsync_url, json={"input": job_input}, headers=headers)
            r.raise_for_status()
            data = r.json()

            status = data.get("status")
            if status == "COMPLETED":
                return data.get("output", {})

            job_id = data.get("id")
            if not job_id:
                raise RuntimeError(f"Unexpected response from RunPod: {data}")

            # Job is in progress / queued, poll status
            print(f"      [~] Job {job_id} status: {status}, polling...", end="", flush=True)
            status_url = f"{self.status_base_url}/{job_id}"
            while time.perf_counter() - t0 < timeout_s:
                time.sleep(2.5)
                sr = client.get(status_url, headers=headers)
                if sr.status_code == 200:
                    sdata = sr.json()
                    cur_status = sdata.get("status")
                    if cur_status == "COMPLETED":
                        print(" [Done]", flush=True)
                        return sdata.get("output", {})
                    elif cur_status in ["FAILED", "CANCELLED"]:
                        print(f" [{cur_status}]", flush=True)
                        raise RuntimeError(f"RunPod job {job_id} failed: {sdata.get('error')}")
                    else:
                        print(".", end="", flush=True)

            raise TimeoutError(f"Job {job_id} exceeded timeout of {timeout_s}s")


def evaluate_sample(item: dict[str, Any], resp_data: dict[str, Any], e2e_ms: float) -> dict[str, Any]:
    output_text = resp_data.get("translated_text", "").strip()
    latency_ms = float(resp_data.get("latency_ms", 0.0) or e2e_ms)
    tokens = int(resp_data.get("tokens", 0))
    tps = float(resp_data.get("tokens_per_sec", 0.0))
    is_leak = bool(resp_data.get("is_leak", False))

    lower_out = output_text.lower()
    warn_hallucination = False
    lost_idioms = []

    # Check known failure modes (e.g. God took a book)
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


def run_client_benchmark(target: str, token: str = ""):
    client = ArenaClient(target, token)

    print("\n" + "=" * 90)
    print(f" [MT MODEL ARENA: RUNNING BENCHMARK VIA RUNPOD SERVERLESS]")
    print(f" Target Mode    : {'RunPod Queue API' if client.is_runpod else 'Direct HTTP'}")
    if client.is_runpod:
        print(f" Endpoint ID    : {client.endpoint_id}")
        print(f" Runsync URL    : {client.runsync_url}")
    else:
        print(f" Base URL       : {client.http_base_url}")
    print("=" * 90)

    # 1. Health & Discovery
    print("[*] Checking endpoint health and discovering loaded model...")
    try:
        health = client.call_endpoint({"action": "health"}, timeout_s=90.0)
    except Exception as exc:
        print(f"[!] Health check failed: {exc}")
        return

    if health.get("status") != "ready":
        print(f"[!] Server is not ready yet. Status: {health.get('status')}, details: {health}")
        return

    model_name = health.get("model", "unknown_model")
    gpu_name = health.get("gpu_name", "Unknown GPU")
    vram = health.get("vram", {})
    used_gb = vram.get("used_gb", 0.0)
    total_gb = vram.get("total_gb", 0.0)
    backend = health.get("backend", "unknown")

    vram_verdict = "PASS (Safe)" if used_gb <= 18.0 else ("TIGHT (18-21GB)" if used_gb <= 21.0 else "DANGER / OOM")

    print(f"      Loaded Model : {model_name}")
    print(f"      Inference Eng: {backend}")
    print(f"      GPU Hardware : {gpu_name}")
    print(f"      VRAM Usage   : {used_gb:.2f} GB / {total_gb:.2f} GB ({vram_verdict})")

    # 2. Load benchmark suite
    items = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    print(f"\n[*] Starting benchmark on {len(items)} canonical test cases...\n")

    eval_results = []
    latencies = []
    total_tokens = 0
    t0_bench = time.perf_counter()

    for idx, item in enumerate(items, 1):
        print(f"[{idx:02d}/{len(items):02d}] {item['category']:<18} | {item['text'][:42]:<42}...", end="", flush=True)

        req_payload = {
            "action": "translate",
            "text": item["text"],
            "source": item["src"],
            "target": item["dst"],
            "max_tokens": 128,
        }

        t0_req = time.perf_counter()
        try:
            resp_data = client.call_endpoint(req_payload, timeout_s=60.0)
            e2e_ms = (time.perf_counter() - t0_req) * 1000.0
            sample_eval = evaluate_sample(item, resp_data, e2e_ms)
            eval_results.append(sample_eval)
            latencies.append(sample_eval["latency_ms"])
            total_tokens += sample_eval["tokens"]

            status_flag = "[FAIL]" if sample_eval["warn_hallucination"] else ("[LEAK]" if sample_eval["is_leak"] else "[OK]")
            print(f" -> {status_flag} {sample_eval['latency_ms']:.1f}ms | {sample_eval['output_text'][:35]}", flush=True)
        except Exception as exc:
            print(f" -> [ERROR]: {exc}", flush=True)

    bench_duration = time.perf_counter() - t0_bench

    if not latencies:
        print("\n[!] No successful benchmark runs recorded.")
        return

    # 3. Aggregate Metrics
    latencies.sort()
    n = len(latencies)
    avg_latency = sum(latencies) / n
    p50_latency = latencies[int(n * 0.50)]
    p95_latency = latencies[min(int(n * 0.95), n - 1)]
    overall_tps = total_tokens / (sum(latencies) / 1000.0) if sum(latencies) > 0 else 0.0

    catastrophic_count = sum(1 for r in eval_results if r["warn_hallucination"])
    leak_count = sum(1 for r in eval_results if r["is_leak"])

    model_slug = slugify(model_name)
    summary_file = RESULTS_DIR / f"{model_slug}_eval.json"

    eval_data = {
        "model_id": model_name,
        "preset_id": model_slug,
        "quantization": health.get("quantization", "none"),
        "backend": backend,
        "gpu_name": gpu_name,
        "vram_gb": used_gb,
        "total_vram_gb": total_gb,
        "vram_verdict": vram_verdict,
        "p50_ms": round(p50_latency, 1),
        "p95_ms": round(p95_latency, 1),
        "avg_ms": round(avg_latency, 1),
        "throughput_tok_s": round(overall_tps, 1),
        "catastrophic_count": catastrophic_count,
        "leak_count": leak_count,
        "total_samples": len(eval_results),
        "results": eval_results,
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(eval_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 90)
    print(f" [BENCHMARK COMPLETED: {model_name}]")
    print(f"  Latency P50 : {p50_latency:.1f} ms")
    print(f"  Latency P95 : {p95_latency:.1f} ms")
    print(f"  Throughput  : {overall_tps:.1f} tok/s")
    print(f"  Hallucination Failures : {catastrophic_count}/{len(eval_results)}")
    print(f"  Chatter/Leak Failures  : {leak_count}/{len(eval_results)}")
    print(f"  Resident VRAM          : {used_gb:.2f} GB ({vram_verdict})")
    print(f"  Saved Results To       : {summary_file}")
    print("=" * 90 + "\n")

    # 4. Refresh Leaderboard
    print("[*] Updating LEADERBOARD.md...")
    update_leaderboard(RESULTS_DIR, ARENA_DIR / "LEADERBOARD.md")
    print("[+] LEADERBOARD.md successfully updated!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MT Model Arena Benchmark Client")
    parser.add_argument(
        "--url",
        type=str,
        default="https://api.runpod.ai/v2/7huftovs9aage6/runsync",
        help="RunPod runsync URL, Endpoint ID, or local URL",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=DEFAULT_RUNPOD_KEY,
        help="RunPod API Key",
    )
    args = parser.parse_args()
    run_client_benchmark(target=args.url, token=args.token)
