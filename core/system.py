"""Log file, usage/cost tracking, update check and the problem report."""
import json
import logging
import logging.handlers
import platform
import sys
import threading
import time

import requests

from . import config

log = logging.getLogger("blogdraft")
_lock = threading.Lock()


def setup_logging() -> None:
    if log.handlers:
        return
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(config.LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


# ----------------------------------------------------------------------------- usage / cost

def _usage_file():
    return config.CONFIG_DIR / "usage.json"


def record(provider: str, model: str, tokens_in: int = 0, tokens_out: int = 0, images: int = 0) -> None:
    """Count API use per month. Called from the AI clients after every successful request."""
    month = time.strftime("%Y-%m")
    with _lock:
        try:
            data = json.loads(_usage_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        m = data.setdefault(month, {})
        key = f"{provider}:{model or '?'}"
        row = m.setdefault(key, {"requests": 0, "tokens_in": 0, "tokens_out": 0, "images": 0})
        row["requests"] += 1
        row["tokens_in"] += int(tokens_in or 0)
        row["tokens_out"] += int(tokens_out or 0)
        row["images"] += int(images or 0)
        try:
            config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            _usage_file().write_text(json.dumps(data, indent=1), encoding="utf-8")
        except OSError:
            pass


def usage_summary(cfg: dict) -> dict:
    try:
        data = json.loads(_usage_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    month = time.strftime("%Y-%m")
    rows = data.get(month, {})
    tin = sum(r["tokens_in"] for r in rows.values())
    tout = sum(r["tokens_out"] for r in rows.values())
    imgs = sum(r["images"] for r in rows.values())
    reqs = sum(r["requests"] for r in rows.values())
    pin, pout, pimg = (float(cfg.get(k) or 0) for k in ("price_in_per_m", "price_out_per_m", "price_image"))
    cost = tin / 1e6 * pin + tout / 1e6 * pout + imgs * pimg
    return {"month": month, "requests": reqs, "tokens_in": tin, "tokens_out": tout, "images": imgs,
            "cost": round(cost, 2), "priced": bool(pin or pout or pimg),
            "by_model": [{"model": k, **v} for k, v in sorted(rows.items())]}


# ----------------------------------------------------------------------------- updates

def _vtuple(v: str) -> tuple:
    out = []
    for part in str(v).split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def check_update(cfg: dict, timeout: int = 8) -> dict:
    url = (cfg.get("update_url") or config.UPDATE_URL or "").strip()
    if not url:
        return {"available": False, "configured": False, "current": config.APP_VERSION}
    r = requests.get(url, timeout=timeout, headers={"User-Agent": f"BlogDraftStudio/{config.APP_VERSION}"})
    r.raise_for_status()
    info = r.json()
    latest = str(info.get("version", ""))
    link = str(info.get("url", ""))
    return {"available": bool(latest) and _vtuple(latest) > _vtuple(config.APP_VERSION),
            "configured": True, "current": config.APP_VERSION, "latest": latest,
            "url": link if link.startswith("https://") else "", "notes": str(info.get("notes", ""))[:500]}


# ----------------------------------------------------------------------------- problem report

def problem_report(cfg: dict, jobs: dict) -> str:
    try:
        lines = config.LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]
    except OSError:
        lines = []
    recent = [f"[{j['label']}] {j['status']}: {j['error']}" for j in list(jobs.values())[-15:] if j.get("error")]
    secrets = [cfg.get(k) for k in config.SECRETS if cfg.get(k)]
    text = "\n".join([
        f"{config.APP_NAME} {config.APP_VERSION}",
        f"Python {sys.version.split()[0]} on {platform.platform()}",
        f"Frozen exe: {bool(getattr(sys, 'frozen', False))}",
        "",
        "Settings (keys hidden):",
        json.dumps(config.masked(cfg), indent=1, default=str),
        "",
        "Recent errors:",
        *(recent or ["(none)"]),
        "",
        "Log (last lines):",
        *lines,
    ])
    for s in secrets:                       # belt and braces: never leak a key
        if len(s) > 4:
            text = text.replace(s, "•••")
    return text
