"""Auto-generates comparative Markdown LEADERBOARD.md from all evaluated models."""

import json
from pathlib import Path

ARENA_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = ARENA_DIR / "results"
DEFAULT_LEADERBOARD_PATH = ARENA_DIR / "LEADERBOARD.md"


def update_leaderboard(results_dir=None, output_path=None):
    r_dir = Path(results_dir) if results_dir else DEFAULT_RESULTS_DIR
    out_path = Path(output_path) if output_path else DEFAULT_LEADERBOARD_PATH

    if not r_dir.exists():
        print(f"[!] Results dir {r_dir} does not exist.")
        return

    json_files = list(r_dir.glob("*_eval.json"))
    if not json_files:
        print(f"[!] No evaluation result files found in {r_dir}")
        return

    evals = []
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
                evals.append(data)
        except Exception as e:
            print(f"[!] Error reading {jf}: {e}")

    # Sort by P50 latency (lower is faster)
    evals.sort(key=lambda x: x.get("p50_ms", x.get("avg_ms", 999999.0)))

    md = []
    md.append("# 🏆 MT Model Arena — Official Comparative Leaderboard")
    md.append("\nتم توليد هذا الجدول آلياً بناءً على قياسات الأداء الفعلي لنماذج الترجمة في حلبة الاختبار الحية على بطاقات 24GB VRAM.\n")
    md.append("| الترتيب | اسم النموذج | المحرك | استهلاك VRAM | زمن P50 (ms) | أسرع جملة (ms) | السرعة (Tokens/s) | الهلوسة | تسريب الهوية | التقييم |")
    md.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    rank_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

    for idx, e in enumerate(evals):
        icon = rank_icons[idx] if idx < len(rank_icons) else f"#{idx+1}"
        model_name = e.get("model_id", "Unknown")
        backend = e.get("backend", "transformers")
        vram_gb = e.get("vram_gb", 0.0)
        total_vram = e.get("total_vram_gb", 24.0)
        vram_str = f"{vram_gb:.1f} / {total_vram:.0f} GB"

        p50 = f"{e.get('p50_ms', 0.0):.1f} ms"

        # Calculate fastest short sentence
        samples = e.get("results", [])
        short_samples = [s.get("latency_ms", 9999) for s in samples if "Ultra-Short" in s.get("category", "")]
        min_short = f"{min(short_samples):.1f} ms" if short_samples else "-"

        tps = f"{e.get('throughput_tok_s', 0.0):.1f} t/s"

        cat_count = e.get("catastrophic_count", 0)
        cat_badge = "✅ 0/20" if cat_count == 0 else f"❌ {cat_count}/20"

        leak_count = e.get("leak_count", 0)
        leak_badge = "✅ 0/20" if leak_count == 0 else f"⚠️ {leak_count}/20"

        # Overall verdict
        verdict = "🟢 Pass (Safe)" if vram_gb <= 18.0 else ("🟡 Tight" if vram_gb <= 21.0 else "🔴 Danger")

        md.append(f"| {icon} | **{model_name}** | `{backend}` | {vram_str} | **{p50}** | {min_short} | **{tps}** | {cat_badge} | {leak_badge} | {verdict} |")

    md.append("\n---\n")
    md.append("## 🔍 مقارنة وتحليل العينات الصعبة (Canonical Cases Breakdown)\n")

    for e in evals:
        model_name = e.get("model_id", "Unknown")
        md.append(f"### 📌 النموذج: `{model_name}`\n")
        md.append("| التصنيف | النص الأصلي | الترجمة الناتجة | زمن الاستجابة | الحالة |")
        md.append("| :--- | :--- | :--- | :---: | :---: |")

        for sample in e.get("results", []):
            cat = sample.get("category", "")
            src_text = sample.get("input_text", "").replace("|", "\\|")
            out_text = sample.get("output_text", "").replace("|", "\\|")
            lat = f"{sample.get('latency_ms', 0.0):.1f} ms"
            flag = "❌ Fail" if sample.get("warn_hallucination") else ("⚠️ Leak" if sample.get("is_leak") else "✅ OK")
            md.append(f"| {cat} | {src_text} | {out_text} | {lat} | {flag} |")
        md.append("\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"[+] Successfully wrote leaderboard to {out_path}")


if __name__ == "__main__":
    update_leaderboard()
