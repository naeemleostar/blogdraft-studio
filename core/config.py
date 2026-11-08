"""Settings stored locally on this computer (never uploaded anywhere).

config.json keeps API keys once ("global") and one settings block per blog ("profiles"), so one person can
run several WordPress sites with different niches.
"""
import json
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "BlogDraft Studio"
APP_VERSION = "3.0.2"
# Where the app looks for a newer version: a small JSON file {"version": "3.1", "url": "...", "notes": "..."}.
# Put the address of your own file here (for example a GitHub raw link) before sharing the app.
UPDATE_URL = "https://raw.githubusercontent.com/naeemleostar/blogdraft-studio/main/latest.json"

CONFIG_DIR = Path(os.environ.get("BLOGDRAFT_HOME", Path.home() / ".blogdraft_studio"))
CONFIG_FILE = CONFIG_DIR / "config.json"
DRAFTS_DIR = CONFIG_DIR / "drafts"
MEDIA_DIR = CONFIG_DIR / "media"
LOG_FILE = CONFIG_DIR / "app.log"
OLD_DIR = Path.home() / ".techkrak_writer"   # settings of the earlier TechKrak Writer version

GLOBAL_DEFAULTS = {
    "gemini_api_key": "",
    "pexels_api_key": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "text_model": "",           # Gemini text model, filled by "Detect models"
    "image_model": "",          # Gemini image model, filled by "Detect models"
    "writer_provider": "gemini",  # who writes the article: gemini | openai | anthropic (research is always Gemini)
    "openai_model": "",
    "anthropic_model": "",
    "openai_image_model": "gpt-image-1",
    "price_in_per_m": 0.0,      # optional, your price per 1M input tokens (USD), for the cost estimate
    "price_out_per_m": 0.0,
    "price_image": 0.0,         # optional, your price per AI image (USD)
    "update_url": "",           # overrides UPDATE_URL
    "check_updates": True,
}

PROFILE_DEFAULTS = {
    # WordPress
    "wp_url": "",
    "wp_user": "",
    "wp_app_password": "",
    # Blog profile
    "site_name": "",
    "author_name": "",
    "author_location": "",
    "niches": ["tech"],         # ids from core.niches.NICHES
    "niche_custom": "",         # optional extra description, e.g. "budget Android phones"
    "audience": "everyday readers in the United States who are not experts",
    "language": "English",
    "tone": "friendly",         # friendly | professional | simple
    "trends_geo": "US",
    "ai_trend_filter": True,    # ask Gemini to double-check which trends fit the niche
    "posts_per_week": 3,        # the app warns above this
    # Article
    "target_words": 1400,
    "inline_images": 2,         # images inside the article, besides the featured image
    "featured_image": True,
    "image_source": "pexels_then_gemini",  # gemini | pexels | pexels_then_gemini | openai | none
    "ai_caption": "AI-generated image",
    "faq": True,
    "sources_section": True,
    "experience_section": True,
    "max_internal_links": 4,
    "max_external_links": 4,
}

DEFAULTS = {**GLOBAL_DEFAULTS, **PROFILE_DEFAULTS}
SECRETS = ("wp_app_password", "gemini_api_key", "pexels_api_key", "openai_api_key", "anthropic_api_key")

TONES = {
    "friendly": "a knowledgeable friend explaining clearly",
    "professional": "a calm, professional expert",
    "simple": "a patient teacher using very simple words for beginners",
}


def resource_dir() -> Path:
    """Folder with the app's own files (also inside a packaged .exe)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


# ----------------------------------------------------------------------------- file format

def _read_raw() -> dict:
    if not CONFIG_FILE.exists():
        _migrate_old()
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _normalise(raw: dict) -> dict:
    """Turn any older flat config into {"global":…, "profiles":…, "active":…}."""
    if "profiles" in raw and isinstance(raw.get("profiles"), dict) and raw["profiles"]:
        raw.setdefault("global", {})
        if raw.get("active") not in raw["profiles"]:
            raw["active"] = next(iter(raw["profiles"]))
        return raw
    g = {k: raw[k] for k in GLOBAL_DEFAULTS if k in raw}
    p = {k: raw[k] for k in PROFILE_DEFAULTS if k in raw}
    name = (raw.get("site_name") or "My Blog").strip() or "My Blog"
    return {"global": g, "profiles": {name: p}, "active": name}


def _write_raw(raw: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_FILE)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


# ----------------------------------------------------------------------------- public API

def load() -> dict:
    raw = _normalise(_read_raw())
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in raw["global"].items() if k in GLOBAL_DEFAULTS})
    cfg.update({k: v for k, v in raw["profiles"][raw["active"]].items() if k in PROFILE_DEFAULTS})
    cfg["profile"] = raw["active"]
    cfg["profiles"] = list(raw["profiles"])
    return cfg


def save(cfg: dict) -> None:
    raw = _normalise(_read_raw())
    name = cfg.get("profile") or raw["active"]
    raw["global"] = {k: cfg.get(k, v) for k, v in GLOBAL_DEFAULTS.items()}
    raw["profiles"][name] = {k: cfg.get(k, v) for k, v in PROFILE_DEFAULTS.items()}
    raw["active"] = name
    _write_raw(raw)


def switch_profile(name: str) -> dict:
    raw = _normalise(_read_raw())
    if name not in raw["profiles"]:
        raise KeyError(name)
    raw["active"] = name
    _write_raw(raw)
    return load()


def add_profile(name: str, copy_from_current: bool = True) -> dict:
    name = " ".join((name or "").split())[:60]
    if not name:
        raise ValueError("Give the site a name.")
    raw = _normalise(_read_raw())
    if name in raw["profiles"]:
        raise ValueError("A site with this name already exists.")
    base = dict(raw["profiles"][raw["active"]]) if copy_from_current else {}
    for k in ("wp_url", "wp_user", "wp_app_password", "site_name"):   # connection is never copied
        base.pop(k, None)
    base["site_name"] = name
    raw["profiles"][name] = base
    raw["active"] = name
    _write_raw(raw)
    return load()


def rename_profile(old: str, new: str) -> dict:
    new = " ".join((new or "").split())[:60]
    raw = _normalise(_read_raw())
    if old not in raw["profiles"] or not new or new in raw["profiles"]:
        raise ValueError("Choose a new, unused name.")
    raw["profiles"] = {(new if k == old else k): v for k, v in raw["profiles"].items()}
    if raw["active"] == old:
        raw["active"] = new
    _write_raw(raw)
    return load()


def delete_profile(name: str) -> dict:
    raw = _normalise(_read_raw())
    if name not in raw["profiles"] or len(raw["profiles"]) == 1:
        raise ValueError("You can't delete your only site.")
    del raw["profiles"][name]
    if raw["active"] == name:
        raw["active"] = next(iter(raw["profiles"]))
    _write_raw(raw)
    return load()


def _migrate_old() -> None:
    """Carry keys and drafts over from the earlier TechKrak Writer app, if present."""
    old = OLD_DIR / "config.json"
    if "BLOGDRAFT_HOME" in os.environ or not old.exists():
        return
    try:
        data = json.loads(old.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    flat = {k: data[k] for k in ("wp_url", "wp_user", "wp_app_password", "gemini_api_key", "pexels_api_key",
                                  "text_model", "image_model", "site_name", "author_name", "audience",
                                  "trends_geo", "target_words", "inline_images", "image_source", "ai_caption")
            if data.get(k) not in (None, "")}
    _write_raw(_normalise(flat))
    if (OLD_DIR / "drafts").is_dir():
        shutil.copytree(OLD_DIR / "drafts", DRAFTS_DIR, dirs_exist_ok=True)


def public(cfg: dict) -> dict:
    """Config for the browser: secrets are never sent back, only whether they are set."""
    out = dict(cfg)
    for k in SECRETS:
        v = cfg.get(k) or ""
        out[k] = ""
        out[k + "_set"] = bool(v)
        out[k + "_hint"] = ("…" + v[-4:]) if len(v) > 8 else ""
    return out


def masked(cfg: dict) -> dict:
    """Config for a problem report: no secrets, no passwords."""
    out = {k: v for k, v in cfg.items() if k not in SECRETS}
    for k in SECRETS:
        out[k] = "set" if cfg.get(k) else "empty"
    return out
