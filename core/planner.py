"""Content calendar: planned topics per site, stored on this computer."""
import datetime as dt
import json
import secrets
import threading

from . import config

_lock = threading.Lock()
STATUSES = ("planned", "written", "draft", "published")


def _file():
    return config.CONFIG_DIR / "plan.json"


def _read() -> dict:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(data: dict) -> None:
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def _valid_date(s: str) -> str:
    try:
        return dt.date.fromisoformat(str(s)[:10]).isoformat()
    except ValueError:
        return dt.date.today().isoformat()


def items(profile: str) -> list:
    return sorted(_read().get(profile, []), key=lambda x: (x.get("date", ""), x.get("id", "")))


def add(profile: str, date: str, topic: str, angle: str = "", note: str = "") -> dict:
    topic = " ".join((topic or "").split())[:200]
    if not topic:
        raise ValueError("Enter a topic.")
    item = {"id": secrets.token_hex(4), "date": _valid_date(date), "topic": topic, "angle": angle[:300],
            "note": note[:500], "status": "planned", "draft": ""}
    with _lock:
        data = _read()
        data.setdefault(profile, []).append(item)
        _write(data)
    return item


def update(profile: str, item_id: str, fields: dict) -> dict:
    with _lock:
        data = _read()
        for it in data.get(profile, []):
            if it["id"] == item_id:
                if "date" in fields:
                    it["date"] = _valid_date(fields["date"])
                if fields.get("status") in STATUSES:
                    it["status"] = fields["status"]
                for k in ("topic", "angle", "note", "draft"):
                    if k in fields:
                        it[k] = str(fields[k])[:500]
                _write(data)
                return it
    raise KeyError(item_id)


def delete(profile: str, item_id: str) -> None:
    with _lock:
        data = _read()
        data[profile] = [x for x in data.get(profile, []) if x["id"] != item_id]
        _write(data)


def rename_profile(old: str, new: str) -> None:
    with _lock:
        data = _read()
        if old in data:
            data[new] = data.pop(old)
            _write(data)


def week_suggestion(posts_per_week: int, start: dt.date = None) -> list:
    """Spread N posts over the next 7 days (e.g. 3 → Mon, Wed, Fri)."""
    start = start or dt.date.today()
    n = max(1, min(7, int(posts_per_week or 3)))
    step = 7 / n
    return [(start + dt.timedelta(days=round(i * step))).isoformat() for i in range(n)]
