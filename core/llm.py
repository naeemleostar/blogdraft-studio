"""Optional writers besides Gemini: OpenAI and Anthropic (Claude). Same small interface as core.gemini.Gemini:
generate(prompt, system) and generate_json(prompt, system, temperature). Research always stays on Gemini,
because it is grounded in Google Search."""
import base64
import json
import re
import time

import requests

from .gemini import Gemini, GeminiError, parse_json_loose


class LLMError(RuntimeError):
    pass


def _retry_post(url, headers, body, timeout=240, retries=3):
    last = ""
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
        except requests.RequestException as e:
            last = str(e)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 529):
            if "insufficient_quota" in r.text or "credit balance" in r.text:
                raise LLMError(f"QUOTA: no credit left on this key (HTTP {r.status_code}). Add billing or credit.")
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            time.sleep(4 * (attempt + 1))
            continue
        if not r.ok:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:500]}")
        return r.json()
    raise LLMError(f"Request failed after retries: {last}")


def _record(provider, model, tin, tout, images=0):
    try:
        from .system import record
        record(provider, model, tin, tout, images)
    except Exception:  # noqa: BLE001
        pass


class OpenAIWriter:
    name = "openai"

    def __init__(self, api_key: str, model: str, image_model: str = "gpt-image-1"):
        if not api_key:
            raise LLMError("OpenAI API key missing (Settings).")
        if not model:
            raise LLMError("OpenAI model not set. Click 'Detect models' next to the OpenAI key.")
        self.key, self.model, self.image_model = api_key.strip(), model, image_model or "gpt-image-1"

    def _headers(self):
        return {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def generate(self, prompt, system="", json_mode=False, temperature=0.7):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = {"model": self.model, "messages": msgs}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = _retry_post("https://api.openai.com/v1/chat/completions", self._headers(), body)
        u = data.get("usage") or {}
        _record("openai", self.model, u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""

    def generate_json(self, prompt, system="", temperature=0.7):
        return parse_json_loose(self.generate(prompt + "\n\nAnswer with JSON only.", system, json_mode=True))

    def generate_image(self, prompt, aspect_ratio="16:9"):
        size = "1536x1024" if aspect_ratio == "16:9" else "1024x1024"
        data = _retry_post("https://api.openai.com/v1/images/generations", self._headers(),
                           {"model": self.image_model, "prompt": prompt, "size": size, "n": 1})
        item = (data.get("data") or [{}])[0]
        if not item.get("b64_json"):
            raise LLMError("OpenAI returned no image.")
        _record("openai", self.image_model, 0, 0, 1)
        return base64.b64decode(item["b64_json"]), "image/png"

    def list_models(self):
        r = requests.get("https://api.openai.com/v1/models", headers=self._headers(), timeout=30)
        if not r.ok:
            raise LLMError(f"Could not list OpenAI models (HTTP {r.status_code}): {r.text[:200]}")
        return sorted(m["id"] for m in r.json().get("data", []))


class AnthropicWriter:
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError("Anthropic (Claude) API key missing (Settings).")
        if not model:
            raise LLMError("Claude model not set. Click 'Detect models' next to the Claude key.")
        self.key, self.model = api_key.strip(), model

    def _headers(self):
        return {"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"}

    def generate(self, prompt, system="", json_mode=False, temperature=0.7):
        body = {"model": self.model, "max_tokens": 16000, "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        data = _retry_post("https://api.anthropic.com/v1/messages", self._headers(), body)
        u = data.get("usage") or {}
        _record("anthropic", self.model, u.get("input_tokens", 0), u.get("output_tokens", 0))
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    def generate_json(self, prompt, system="", temperature=0.7):
        return parse_json_loose(self.generate(prompt + "\n\nAnswer with one JSON object only, no other text.", system))

    def list_models(self):
        r = requests.get("https://api.anthropic.com/v1/models", headers=self._headers(), timeout=30,
                         params={"limit": 100})
        if not r.ok:
            raise LLMError(f"Could not list Claude models (HTTP {r.status_code}): {r.text[:200]}")
        return [m["id"] for m in r.json().get("data", [])]


def pick_openai(names: list) -> str:
    bad = ("audio", "realtime", "image", "embedding", "tts", "transcribe", "search", "moderation", "dall-e",
           "whisper", "instruct", "codex", "computer", "babbage", "davinci", "nano")
    cands = [n for n in names if n.startswith(("gpt-", "o")) and not any(b in n for b in bad)
             and not re.search(r"\d{4}-\d{2}-\d{2}", n)]

    def key(n):
        m = re.search(r"gpt-(\d+(?:\.\d+)?)", n)
        return (float(m.group(1)) if m else 0, "mini" not in n, -len(n))
    cands.sort(key=key, reverse=True)
    return cands[0] if cands else ""


def pick_anthropic(names: list) -> str:
    for want in ("sonnet", "opus", "haiku"):
        for n in names:          # the API lists newest first
            if want in n:
                return n
    return names[0] if names else ""


def make_writer(cfg: dict, gemini: Gemini):
    """The text writer chosen in Settings (falls back to Gemini)."""
    p = cfg.get("writer_provider") or "gemini"
    if p == "openai":
        return OpenAIWriter(cfg.get("openai_api_key", ""), cfg.get("openai_model", ""), cfg.get("openai_image_model"))
    if p == "anthropic":
        return AnthropicWriter(cfg.get("anthropic_api_key", ""), cfg.get("anthropic_model", ""))
    return gemini


__all__ = ["OpenAIWriter", "AnthropicWriter", "LLMError", "make_writer", "pick_openai", "pick_anthropic",
           "GeminiError"]
