"""Gemini helpers for topic discovery: niche classification of trends and article ideas."""
from . import niches


def ai_classify(gemini, items: list) -> None:
    """Ask Gemini which niches each trend really belongs to; stores the answer on trend.ai_niches."""
    if not items:
        return
    ids = ", ".join(f"{k} ({v['label']})" for k, v in niches.NICHES.items())
    lines = "\n".join(f"{i}. {t.title} — " + "; ".join(n[0] for n in t.news[:2]) for i, t in enumerate(items))
    data = gemini.generate_json(
        "Classify each trending Google search by what it is actually ABOUT, using the headlines.\n"
        f"Allowed niche ids: {ids}.\n"
        "Rules: a sports match is only 'sports' even if it streams on an app; a celebrity story is only "
        "'entertainment'; give [] for politics, crime, tragedy or anything that fits no niche. "
        "Use at most 2 ids per item.\n\n"
        f"{lines}\n\nReturn JSON: {{\"items\": [{{\"i\": 0, \"niches\": [\"tech\"]}}]}}",
        temperature=0.1)
    by_label = {v["label"].lower(): k for k, v in niches.NICHES.items()}

    def to_id(x):
        x = str(x or "").strip().lower()
        return x if x in niches.NICHES else by_label.get(x) or next(
            (k for lab, k in by_label.items() if x and (x in lab or lab.split(" ")[0] == x)), None)

    got = {}
    for row in data.get("items", []) if isinstance(data, dict) else []:
        try:
            got[int(row.get("i"))] = [i for i in (to_id(n) for n in row.get("niches", [])) if i]
        except (TypeError, ValueError, AttributeError):
            continue
    if not got:
        return  # unusable answer: keep keyword matching
    for i, t in enumerate(items):
        if i in got:
            t.ai_niches = got[i]


def ai_ideas(gemini, items: list, selected: list, custom: str = "", count: int = 8) -> list:
    """Article ideas from today's trends that fit the selected niches."""
    niche = niches.niche_text(selected, custom)
    pool = [t for t in items if not t.blocked][:40]
    if not pool:
        return []
    lines = "\n".join(f"- {t.title}: " + "; ".join(n[0] for n in t.news[:2]) for t in pool)
    data = gemini.generate_json(
        f"These are today's trending Google searches:\n{lines}\n\n"
        f"Our blog is about: {niche}.\n"
        f"Pick up to {count} trends that genuinely belong to this blog's niche. Skip gambling or betting, "
        "crime, tragedy, adult topics and anything outside the niche, even if an angle could be invented. "
        "Returning zero ideas is fine. For each, propose one useful article topic people would search for. "
        'Return JSON: {"ideas": [{"trend": "...", "topic": "article topic", "angle": "one sentence on the useful angle"}]}',
        temperature=0.3)
    out = []
    for i in data.get("ideas", []):
        text = f"{i.get('topic', '')} {i.get('trend', '')} {i.get('angle', '')}"
        if i.get("topic") and not niches.is_blocked(text):
            out.append({"trend": i.get("trend", ""), "topic": i["topic"], "angle": i.get("angle", "")})
    return out


def evergreen_ideas(gemini, selected: list, custom: str = "", keyword: str = "", audience: str = "",
                    count: int = 10) -> list:
    """Evergreen topic ideas for the niche (useful when today's trends don't fit)."""
    niche = niches.niche_text(selected, custom)
    focus = f" focused on '{keyword}'" if keyword else ""
    data = gemini.generate_json(
        f"Suggest {count} evergreen blog post topics{focus} for a blog about {niche}. Readers: {audience}. "
        "Prefer specific how-to, comparison, explainer and problem-solving topics that people search for all year. "
        "No gambling, adult or tragedy topics. "
        'Return JSON: {"ideas": [{"topic": "...", "angle": "one sentence on the useful angle"}]}',
        temperature=0.6)
    return [{"trend": "", "topic": i["topic"], "angle": i.get("angle", "")}
            for i in data.get("ideas", []) if i.get("topic") and not niches.is_blocked(i["topic"])]
