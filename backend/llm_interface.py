import json
import os
from typing import Any, Dict, Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

try:
    from transformers import BitsAndBytesConfig  # type: ignore
    _HAS_BNB = True
except Exception:
    _HAS_BNB = False

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


class LLMInterface:
    def __init__(self, config_path: Optional[str] = None) -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._config_path = config_path or os.path.join(base_dir, 'config.yaml')
        self._sys_prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sys_prompt.txt')

        self.model_id = 'microsoft/Phi-3-mini-4k-instruct'
        self.temperature: float = 0.2
        self.max_tokens: int = 512

        self.tokenizer = None
        self.model = None

        self._load_config()
        self._load_system_prompt()

    def _load_config(self) -> None:
        if yaml is None:
            return
        if not os.path.exists(self._config_path):
            return
        with open(self._config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}

        model_cfg = (cfg.get('model') or {})
        provider = model_cfg.get('provider')
        if provider == 'huggingface':
            self.model_id = model_cfg.get('model_id', self.model_id)
        # temperature/max_tokens fallbacks
        self.temperature = float(model_cfg.get('temperature', self.temperature))
        self.max_tokens = int(model_cfg.get('max_tokens', self.max_tokens))

    def _load_system_prompt(self) -> None:
        if os.path.exists(self._sys_prompt_path):
            with open(self._sys_prompt_path, 'r', encoding='utf-8') as f:
                self.system_prompt = f.read().strip()
        else:
            self.system_prompt = ''

    def load(self) -> None:
        # Optimized for minimal disk usage
        load_kwargs: Dict[str, Any] = {
            "device_map": "cpu",  # Force CPU usage to save space
            "torch_dtype": torch.float16,  # Use half precision to save memory
            "low_cpu_mem_usage": True,  # Optimize memory usage
        }

        # Skip BitsAndBytes quantization to save space
        # Use dynamic quantization instead if needed
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, use_fast=True)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id, **load_kwargs)
        
        # Apply dynamic quantization to reduce model size
        try:
            self.model = torch.quantization.quantize_dynamic(
                self.model, {torch.nn.Linear}, dtype=torch.qint8
            )
        except Exception:
            # If quantization fails, continue without it
            pass

    def _build_inputs(self, data: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'market_data': data,
            'portfolio': portfolio,
            'tools_used': [
                # Hidden internal tools executed server-side prior to model call
                # Do not expose this list to the user in responses
                'fetch_market_snapshot',
                'load_user_portfolio',
                'aggregate_recent_news',
            ],
        }

    def _to_chat(self, inputs: Dict[str, Any]) -> str:
        # Prefer tokenizer chat template if available
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        user_content = (
            "You are MAGMA. Analyze the provided market data, portfolio, and news. "
            "Return clear buy/sell/hold rationales. Do NOT disclose or enumerate any internal tools or preprocessing steps. "
            "If asked about tools, reply that you synthesize data provided by the system."
            "\n\nINPUT JSON:\n" + json.dumps(inputs, ensure_ascii=False)
        )
        messages.append({"role": "user", "content": user_content})

        if hasattr(self.tokenizer, 'chat_template') and getattr(self.tokenizer, 'chat_template'):
            prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            return prompt

        sys_text = f"[SYSTEM]\n{self.system_prompt}\n\n" if self.system_prompt else ""
        return sys_text + f"[USER]\n{user_content}\n\n[ASSISTANT] "

    @torch.inference_mode()
    def get_recommendations(self, data: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None or self.tokenizer is None:
            self.load()

        inputs = self._build_inputs(data, portfolio)
        prompt = self._to_chat(inputs)

        enc = self.tokenizer(prompt, return_tensors='pt')
        enc = {k: v.to(self.model.device) for k, v in enc.items()}

        gen_ids = self.model.generate(
            **enc,
            max_new_tokens=self.max_tokens,
            do_sample=True if self.temperature > 0 else False,
            temperature=self.temperature,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.eos_token_id,
        )

        output_text = self.tokenizer.decode(gen_ids[0][enc['input_ids'].shape[1]:], skip_special_tokens=True)

        return {
            'model': self.model_id,
            'text': output_text.strip(),
        }


# Module-level convenience
_singleton: Optional[LLMInterface] = None


def get_recommendations(data: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
    global _singleton
    if _singleton is None:
        _singleton = LLMInterface()
        _singleton.load()
    return _singleton.get_recommendations(data, portfolio)


