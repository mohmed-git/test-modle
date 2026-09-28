# MT Model Arena (معلب تقييم ومقارنة نماذج الترجمة الفورية)

منصة معيارية مستقلة وموحدة لتقييم واختبار أحدث نماذج الترجمة والـ MoE (إصدارات 2026) على بطاقات **NVIDIA 24GB (RTX 3090 / 4090 / A5000)**.

---

## 🎯 النماذج المستهدفة في حلبة المقارنة (Candidate Models):

| المعرّف (Preset) | اسم النموذج | المعمارية والحجم | الباراميترات النشطة | حجم VRAM المقدر | الهدف من الاختبار |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `hy-mt2-7b` | **Tencent Hy-MT2-7B** | Dedicated MT (Dense 7B) | 7B Dense | ~5.0 GB | بديل فائق لـ Qwen-7B متخصص حصراً بالترجمة |
| `hy-mt2-30b-a3b` | **Tencent Hy-MT2-30B-A3B** | Dedicated MT (MoE 30B) | 3B Active | ~18.0 GB | عملاق الترجمة المتخصص بسرعة نموذج 3B |
| `qwen3-30b-a3b` | **Alibaba Qwen3-30B-A3B** | General MoE 30B | 3.3B Active | ~18.6 GB | قفزة Qwen3 في الاستيعاب وسرعة التوليد |
| `qwen3.6-35b-a3b` | **Alibaba Qwen3.6-35B-A3B** | General MoE 35B | 3.0B Active | ~19.5 GB | أحدث معمارية MoE لـ Qwen3.6 |
| `gemma4-26b-a4b` | **Google Gemma 4 26B-A4B** | DeepMind MoE 26B | 3.8B Active | ~14.4 GB | توازن الحجم والسرعة من Google DeepMind |
| `gemma4-e4b` | **Google Gemma 4 E4B** | Edge Dense 4B | 4B Dense | ~4.5 GB | بديل فائق الخفة والسرعة للنموذج الصغير 1.5B |
| `gemma4-e2b` | **Google Gemma 4 E2B** | Ultra-Edge 2B | 2B Dense | ~2.9 GB | أقصى خفة ممكنة لأجهزة الطرفية |

---

## 📊 المقاييس التي يتم اختبارها علمياً (Evaluation Metrics):

1. **الذاكرة العتادية (VRAM Footprint):**
   * الذاكرة قبل التحميل، بعد التحميل، وأثناء ذروة التوليد (Peak VRAM).
   * إمكانية العمل الآمن بجانب Whisper على كروت 24GB دون OOM.
2. **سرعة المعالجة الصافية (Throughput & Latency):**
   * زمن أول توكن (TTFT - Time to First Token).
   * معدل سرعة التوليد الصافي (Tokens / Second).
   * زمن الترجمة للجمل القصيرة (<=6 كلمات) والجمل الحوارية الطويلة (28-35 كلمة).
3. **الدقة اللغوية وحفظ اللهجات (Dialect & Idiom Preservation):**
   * فهم مصطلحات العامية السعودية المركبة في البودكاست (مثل: "على قولة كوتش"، "صاحب ميدان"، "والله باخذ كتاب").
   * فهم العامية الأردنية والشامية والمصرية ومنع الترجمة الحرفية.
4. **منع تسريب الهوية والثرثرة (Zero Chatter & Persona Check):**
   * التأكد من إخراج الترجمة الصافية فقط، دون مقدمات مثل "Here is the translation:".

---

## 🚀 طريقة التشغيل السريعة (Quick Start):

### 1. تثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

### 2. تشغيل اختبار أي نموذج:
```bash
# تشغيل نموذج Hy-MT2-7B (المتخصص)
python run_arena.py --preset hy-mt2-7b

# تشغيل عملاق الـ MoE لـ Qwen3
python run_arena.py --preset qwen3-30b-a3b

# أو تشغيل أي نموذج عبر مسار Hugging Face المباشر
python run_arena.py --model "tencent/Hy-MT2-7B" --name "hy-mt2-custom"
```

### 3. توليد جدول الترتيب المقارن النهائي (Leaderboard):
```bash
python generate_leaderboard.py
```
يقوم هذا الأمر بقراءة كافة نتائج النماذج التي تم اختبارها في مجلد `results/` وتوليد ملف `LEADERBOARD.md` للمقارنة الشاملة وجهاً لوجه!
