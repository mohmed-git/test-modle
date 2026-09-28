"""Unified Model Inference Engine for MT Arena.

Supports:
  - vLLM (high throughput, where supported)
  - Transformers AutoModelForCausalLM (traditional text LLMs: Hy-MT2, Qwen)
  - Transformers AutoModelForMultimodalLM & AutoProcessor (Gemma 4 Any-to-Any)
Tracks:
  - Exact VRAM before and after loading
  - Peak inference VRAM
  - Pure generation latency & tokens/sec
"""

import time
from typing import Any, Optional
import torch

try:
    from vllm import LLM, SamplingParams
    HAS_VLLM = True
except ImportError:
    HAS_VLLM = False

from transformers import (
    AutoConfig,
    AutoModelForCausalLM,
    AutoProcessor,
    AutoTokenizer,
)

try:
    from transformers import AutoModelForMultimodalLM
    HAS_MULTIMODAL_LM = True
except ImportError:
    HAS_MULTIMODAL_LM = False


def get_vram_info() -> dict[str, float]:
    """Return current VRAM usage in MB and GB."""
    if not torch.cuda.is_available():
        return {"used_gb": 0.0, "total_gb": 0.0, "free_gb": 0.0}
    free_b, total_b = torch.cuda.mem_get_info()
    used_b = total_b - free_b
    return {
        "used_mb": round(used_b / (1024**2), 1),
        "free_mb": round(free_b / (1024**2), 1),
        "total_mb": round(total_b / (1024**2), 1),
        "used_gb": round(used_b / (1024**3), 2),
        "free_gb": round(free_b / (1024**3), 2),
        "total_gb": round(total_b / (1024**3), 2),
    }


def is_multimodal_model(model_id: str, config: Any) -> bool:
    """Detect if model requires Multimodal / ConditionalGeneration architecture."""
    mid = model_id.lower()
    if "gemma-4" in mid or "gemma4" in mid:
        return True
    if config:
        archs = getattr(config, "architectures", []) or []
        model_type = getattr(config, "model_type", "").lower()
        if "gemma4" in model_type:
            return True
        for a in archs:
            if "ConditionalGeneration" in a or "Multimodal" in a:
                return True
    return False


class ArenaInferenceEngine:
    def __init__(
        self,
        model_id: str,
        quantization: Optional[str] = None,
        prefer_vllm: bool = True,
        max_model_len: int = 1024,
    ):
        self.model_id = model_id
        self.quantization = quantization
        self.prefer_vllm = prefer_vllm and HAS_VLLM
        self.max_model_len = max_model_len
        self.backend_name = "unknown"
        self.llm = None
        self.tokenizer = None
        self.processor = None
        self.model = None
        self.is_multimodal = False

        self.initial_vram = get_vram_info()
        self.loaded_vram = {}
        self.load_model()

    def load_model(self):
        print(f"[*] Initial VRAM before load: {self.initial_vram['used_gb']} GB / {self.initial_vram['total_gb']} GB")
        t0 = time.perf_counter()

        if self.prefer_vllm:
            try:
                print(f"[*] Attempting load via vLLM: {self.model_id} (quant={self.quantization})...")
                vllm_kwargs: dict[str, Any] = {
                    "model": self.model_id,
                    "max_model_len": self.max_model_len,
                    "trust_remote_code": True,
                    "enforce_eager": True,
                }
                if self.quantization and self.quantization.lower() != "none":
                    vllm_kwargs["quantization"] = self.quantization.lower()

                self.llm = LLM(**vllm_kwargs)
                self.tokenizer = self.llm.get_tokenizer()
                self.backend_name = "vllm"
                print(f"[+] Loaded successfully via vLLM in {time.perf_counter() - t0:.2f}s")
            except Exception as exc:
                print(f"[!] vLLM load failed ({exc}). Falling back to Transformers...")
                self.llm = None

        if self.llm is None:
            print(f"[*] Loading via Transformers: {self.model_id}...")
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

            try:
                config = AutoConfig.from_pretrained(self.model_id, trust_remote_code=True)
            except Exception as exc:
                print(f"[!] Warning reading AutoConfig: {exc}")
                config = None

            self.is_multimodal = is_multimodal_model(self.model_id, config)

            if self.is_multimodal:
                print(f"[*] Detected Multimodal Architecture ({self.model_id}). Initializing AutoProcessor & AutoModelForMultimodalLM...")
                try:
                    self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
                except Exception as pe:
                    print(f"[!] AutoProcessor failed ({pe}), will fallback to tokenizer...")
                    self.processor = None

                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
                except Exception:
                    self.tokenizer = getattr(self.processor, "tokenizer", None)

                loaded = False
                if HAS_MULTIMODAL_LM:
                    try:
                        print("[*] Attempting AutoModelForMultimodalLM.from_pretrained...")
                        self.model = AutoModelForMultimodalLM.from_pretrained(
                            self.model_id,
                            device_map="auto",
                            torch_dtype=dtype,
                            trust_remote_code=True,
                        )
                        loaded = True
                    except Exception as me:
                        print(f"[!] AutoModelForMultimodalLM failed: {me}")

                if not loaded:
                    print("[*] Attempting AutoModelForCausalLM / AutoModel fallback...")
                    try:
                        self.model = AutoModelForCausalLM.from_pretrained(
                            self.model_id,
                            device_map="auto",
                            torch_dtype=dtype,
                            trust_remote_code=True,
                        )
                    except Exception:
                        from transformers import AutoModel
                        self.model = AutoModel.from_pretrained(
                            self.model_id,
                            device_map="auto",
                            torch_dtype=dtype,
                            trust_remote_code=True,
                        )
            else:
                print(f"[*] Loading standard CausalLM: {self.model_id}...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
                self.processor = None
                try:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        device_map="auto",
                        torch_dtype=dtype,
                        trust_remote_code=True,
                    )
                except Exception as me:
                    if HAS_MULTIMODAL_LM and ("keys" in str(me).lower() or "conditional" in str(me).lower()):
                        print(f"[!] CausalLM threw multimodal error. Switching to AutoModelForMultimodalLM...")
                        self.model = AutoModelForMultimodalLM.from_pretrained(
                            self.model_id,
                            device_map="auto",
                            torch_dtype=dtype,
                            trust_remote_code=True,
                        )
                        self.is_multimodal = True
                        try:
                            self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
                        except Exception:
                            self.processor = None
                    else:
                        raise me

            self.backend_name = "transformers"
            print(f"[+] Loaded successfully via Transformers in {time.perf_counter() - t0:.2f}s")

        self.loaded_vram = get_vram_info()
        print(f"[*] Resident VRAM after load: {self.loaded_vram['used_gb']} GB ({self.loaded_vram['used_gb'] - self.initial_vram['used_gb']:.2f} GB delta)")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 128,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate translation and track latency & throughput."""
        torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()

        if self.backend_name == "vllm":
            sampling = SamplingParams(
                max_tokens=max_tokens,
                temperature=temperature,
            )
            outputs = self.llm.generate([prompt], sampling)
            gen_time = (time.perf_counter() - t0) * 1000.0
            generated_text = outputs[0].outputs[0].text.strip()
            num_tokens = len(outputs[0].outputs[0].token_ids)
        elif self.is_multimodal and self.processor is not None:
            inputs = None
            if hasattr(self.processor, "apply_chat_template"):
                try:
                    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                    try:
                        inputs = self.processor.apply_chat_template(
                            messages,
                            tokenize=True,
                            return_dict=True,
                            return_tensors="pt",
                            add_generation_prompt=True,
                            enable_thinking=False,
                        )
                    except TypeError:
                        inputs = self.processor.apply_chat_template(
                            messages,
                            tokenize=True,
                            return_dict=True,
                            return_tensors="pt",
                            add_generation_prompt=True,
                        )
                except Exception:
                    inputs = None

            if inputs is None:
                try:
                    inputs = self.processor(text=prompt, return_tensors="pt")
                except Exception:
                    inputs = self.tokenizer(prompt, return_tensors="pt")

            device = getattr(self.model, "device", "cuda")
            inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in inputs.items()}
            inputs.pop("token_type_ids", None)
            input_len = inputs["input_ids"].shape[-1]

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=False,
                    temperature=None,
                    top_p=None,
                )
            gen_time = (time.perf_counter() - t0) * 1000.0
            gen_tokens = outputs[0][input_len:]

            if hasattr(self.processor, "decode"):
                raw_decoded = self.processor.decode(gen_tokens, skip_special_tokens=True)
                if hasattr(self.processor, "parse_response"):
                    try:
                        parsed = self.processor.parse_response(raw_decoded)
                        generated_text = parsed.get("text", raw_decoded) if isinstance(parsed, dict) else str(parsed)
                    except Exception:
                        generated_text = raw_decoded
                else:
                    generated_text = raw_decoded
            else:
                generated_text = self.tokenizer.decode(gen_tokens, skip_special_tokens=True)

            generated_text = generated_text.strip()
            num_tokens = len(gen_tokens)
        else:
            inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
            inputs.pop("token_type_ids", None)
            input_len = inputs["input_ids"].shape[1]
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=False,
                    temperature=None,
                    top_p=None,
                )
            gen_time = (time.perf_counter() - t0) * 1000.0
            gen_tokens = outputs[0][input_len:]
            generated_text = self.tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
            num_tokens = len(gen_tokens)

        tok_per_sec = (num_tokens / (gen_time / 1000.0)) if gen_time > 0 else 0.0
        peak_vram_mb = torch.cuda.max_memory_allocated() / (1024**2)

        return {
            "text": generated_text,
            "latency_ms": round(gen_time, 2),
            "tokens": num_tokens,
            "tokens_per_sec": round(tok_per_sec, 2),
            "peak_vram_mb": round(peak_vram_mb, 1),
        }
