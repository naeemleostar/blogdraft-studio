"""Minimal Gemini API client (REST, no SDK) for text, grounded research and images."""
import base64
import json
import re
import time

import requests

BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(RuntimeError):
    pass


class Gemini:
    def __init__(self, api_key: str, text_model: str = "", image_model: str = "", timeout: int = 180):
        if not api_key:
            raise GeminiError("Gemini API key missing (Settings tab).")
        self.key = api_key.strip()
        self.text_model = text_model
        self.image_model = image_model
        self.timeout = timeout

    # ---------- low level ----------
    def _post(self, model: str, body: dict, retries: int = 3) -> dict:
        url = f"{BASE}/models/{model}:generateContent"
        last = None
        for attempt in range(retries):
            try:
                r = requests.post(url, headers={"x-goog-api-key": self.key, "Content-Type": "application/json"},
                                  data=json.dumps(body), timeout=self.timeout)
            except requests.RequestException as e:
                last = str(e)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 429 and ("exceeded your current quota" in r.text or "limit: 0" in r.text):
                raise GeminiError("QUOTA: This Gemini key has no quota left for model "
                                  f"'{model}'. Image models usually need billing enabled in "
                                  "aistudio.google.com, or switch Image source to 'pexels'.")
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}: {r.text[:300]}"
                time.sleep(4 * (attempt + 1))
                continue
            if not r.ok:
                raise GeminiError(f"Gemini error HTTP {r.status_code}: {r.text[:500]}")
            data = r.json()
            try:
                from .system import record
                um = data.get("usageMetadata") or {}
                imgs = sum(1 for c in data.get("candidates", []) for p in c.get("content", {}).get("parts", [])
                           if p.get("inlineData") or p.get("inline_data"))
                record("gemini", model, um.get("promptTokenCount", 0), um.get("candidatesTokenCount", 0), imgs)
            except Exception:  # noqa: BLE001 - usage tracking must never break writing
                pass
            return data
        raise GeminiError(f"Gemini request failed after retries: {last}")

    @staticmethod
    def _text_of(resp: dict) -> str:
        cands = resp.get("candidates") or []
        if not cands:
            fb = resp.get("promptFeedback", {})
            raise GeminiError(f"No answer from Gemini (blocked? {fb})")
        parts = cands[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

    # ---------- models ----------
    def list_models(self) -> list:
        r = requests.get(f"{BASE}/models", params={"pageSize": 1000},
                         headers={"x-goog-api-key": self.key}, timeout=30)
        if not r.ok:
            raise GeminiError(f"Could not list models (HTTP {r.status_code}): {r.text[:300]}")
        models = []
        for m in r.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                models.append(m["name"].split("/", 1)[-1])
        return models

    @staticmethod
    def pick_models(names: list) -> tuple:
        """Choose a good text model and an image model from what this key can use."""
        def version(n):
            m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
            return float(m.group(1)) if m else 0.0
        bad = ("image", "tts", "embedding", "audio", "live", "lite", "preview", "exp", "learnlm", "gemma", "robotics", "computer")
        text = [n for n in names if n.startswith("gemini") and not any(b in n for b in bad)]
        text_pref = sorted(text, key=lambda n: (version(n), "pro" in n, "flash" in n), reverse=True)
        # prefer newest "flash" (fast, cheap, works on free tier), else newest "pro"
        pro = [n for n in text_pref if "pro" in n]
        flash = [n for n in text_pref if "flash" in n]
        text_model = (flash or pro or text_pref or [""])[0]
        imgs = [n for n in names if "image" in n and "preview" not in n and "edit" not in n]
        img_pref = sorted(imgs, key=lambda n: (version(n), "flash" in n and "lite" not in n), reverse=True)
        image_model = img_pref[0] if img_pref else ""
        return text_model, image_model

    # ---------- text ----------
    def generate(self, prompt: str, system: str = "", json_mode: bool = False, temperature: float = 0.7) -> str:
        if not self.text_model:
            raise GeminiError("Text model not set. Click 'Detect models' in Settings.")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        return self._text_of(self._post(self.text_model, body))

    def generate_json(self, prompt: str, system: str = "", temperature: float = 0.7) -> dict:
        raw = self.generate(prompt, system, json_mode=True, temperature=temperature)
        return parse_json_loose(raw)

    def research(self, prompt: str, system: str = "") -> tuple:
        """Google-Search-grounded answer. Returns (text, [(title, url), ...])."""
        if not self.text_model:
            raise GeminiError("Text model not set. Click 'Detect models' in Settings.")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}],
                "generationConfig": {"temperature": 0.3}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        resp = self._post(self.text_model, body)
        text = self._text_of(resp)
        sources = []
        meta = (resp.get("candidates") or [{}])[0].get("groundingMetadata", {}) or {}
        for ch in meta.get("groundingChunks", []) or []:
            web = ch.get("web") or {}
            if web.get("uri"):
                sources.append((web.get("title") or "", web["uri"]))
        return text, sources

    # ---------- images ----------
    def generate_image(self, prompt: str, aspect_ratio: str = "16:9") -> tuple:
        """Returns (bytes, mime_type)."""
        if not self.image_model:
            raise GeminiError("Image model not set. Click 'Detect models' in Settings.")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                                     "imageConfig": {"aspectRatio": aspect_ratio}}}
        try:
            resp = self._post(self.image_model, body)
        except GeminiError as e:
            if "imageConfig" in str(e) or "aspect" in str(e).lower():
                body["generationConfig"].pop("imageConfig", None)
                resp = self._post(self.image_model, body)
            else:
                raise
        for cand in resp.get("candidates", []):
            for p in cand.get("content", {}).get("parts", []):
                data = p.get("inlineData") or p.get("inline_data")
                if data and data.get("data"):
                    return base64.b64decode(data["data"]), data.get("mimeType") or data.get("mime_type") or "image/png"
        raise GeminiError("Gemini returned no image for this prompt.")


def resolve_url(url: str, timeout: int = 12) -> str:
    """Grounding links are Google redirect URLs; follow them to the real article URL."""
    if "grounding-api-redirect" not in url and "vertexaisearch" not in url:
        return url
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        if r.url and "vertexaisearch" not in r.url:
            return r.url
        r = requests.get(url, allow_redirects=True, timeout=timeout, stream=True)
        return r.url if "vertexaisearch" not in r.url else ""
    except requests.RequestException:
        return ""


def parse_json_loose(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    try:
        return json.loads(raw)
    except ValueError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise GeminiError("Gemini did not return valid JSON. Try again.")
