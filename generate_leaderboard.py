"""Auto-generates comparative Markdown LEADERBOARD.md from all evaluated models."""

import json
from pathlib import Path

ARENA_DIR = Path(__file__).resolve().parent
RESULTS_DIR = ARENA_DIR / "results"
LEADERBOARD_PATH = ARENA_DIR / "LEADERBOARD.md"


def update_leaderboard():
    if not RESULTS_DIR.exists():
        return

    json_files = list(RESULTS_DIR.glob("*_eval.json"))
    if not json_files:
        print("[!] No evaluation result files found yet in results/")
        return

    evals = []
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                evals.append(json.load(f))
        except Exception as e:
            print(f"[!] Error reading {jf}: {e}")

    # Sort primarily by overall latency (lower is faster)
    evals.sort(key=lambda x: x.get("overall_avg_latency_ms", 999999.0))

    md = []
    md.append("# 🏆 MT Model Arena — Official Comparative Leaderboard")
    md.append("\nتم توليد هذا الجدول آلياً بناءً على قياسات الأداء الفعلي لنماذج الترجمة على بطاقات 24GB VRAM.\n")
    md.append("| الترتيب | اسم النموذج | المعمارية | الحجم النشط | استهلاك VRAM | زمن القصير (ms) | زمن البودكاست (ms) | السرعة (Tokens/s) | تسريب الهوية | توافق 24GB |")
    md.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    rank_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

    for idx, e in enumerate(evals):
        icon = rank_icons[idx] if idx < len(rank_icons) else f"#{idx+1}"
        name = e.get("display_name", "Unknown")
        arch = e.get("architecture_type", "dense")
        active = e.get("active_params", "-")
        vram = f"{e.get('vram_used_gb', 0.0):.1f} GB"
        short_lat = f"{e.get('avg_short_latency_ms', 0.0):.1f} ms"
        long_lat = f"{e.get('avg_long_latency_ms', 0.0):.1f} ms"
        tps = f"{e.get('avg_tokens_per_sec', 0.0):.1f} t/s"
        leak = f"{e.get('leak_percentage', 0.0):.1f}%"
        verdict = e.get("vram_verdict_24gb", "UNKNOWN")

        # Color badges
        leak_badge = "✅ 0%" if e.get("persona_leaks_count", 0) == 0 else f"⚠️ {leak}"
        vram_badge = "🟢 Safe" if "Safe" in verdict else ("🟡 Tight" if "TIGHT" in verdict else "🔴 OOM Risk")

        md.append(f"| {icon} | **{name}** | `{arch}` | {active} | {vram} | {short_lat} | {long_lat} | **{tps}** | {leak_badge} | {vram_badge} |")

    md.append("\n---\n")
    md.append("## 🔍 مقارنة عينات حقيقية من اللهجات الصعبة (Head-to-Head Sample Inspection)\n")

    # Sample comparisons on key sentences
    for sample_id in ["PODCAST_SA_001", "PODCAST_SA_002", "LEV_JORDAN_01"]:
        md.append(f"\n### حالة الاختبار: `{sample_id}`")
        found_any = False
        for e in evals:
            samples = {s["id"]: s for s in e.get("sample_evaluations", [])}
            if sample_id in samples:
                s = samples[sample_id]
                if not found_any:
                    md.append(f"**النص العربي الأصلي:** *\"{s['input_text']}\"*\n")
                    found_any = True
                warn = " ⚠️ [Hallucination Detected]" if s.get("warn_hallucination") else ""
                md.append(f"* **{e['display_name']}** ({s['latency_ms']:.1f} ms): \"{s['output_text']}\"{warn}")

    LEADERBOARD_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"[+] Updated Leaderboard: {LEADERBOARD_PATH}")


if __name__ == "__main__":
    update_leaderboard()
