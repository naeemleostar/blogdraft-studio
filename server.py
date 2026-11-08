"""BlogDraft Studio: a local web dashboard (runs only on this computer, at http://127.0.0.1)."""
import base64
import html
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core import config, news, niches, planner, system, topics, updater
from core.gemini import Gemini
from core.llm import AnthropicWriter, OpenAIWriter, make_writer, pick_anthropic, pick_openai
from core.images import pexels_search
from core.trends import fetch_suggestions, fetch_trending
from core.wordpress import WordPress
from core.writer import Article, Pipeline, find_banned, find_fabrication, sanitize_html, seo_report, trim_meta

WEB = config.resource_dir() / "web"
TOKEN = secrets.token_urlsafe(24)
SECRETS = config.SECRETS
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}

STATE = {"cfg": config.load(), "trends": [], "lock": threading.Lock()}
JOBS = {}


# ----------------------------------------------------------------------------- helpers

class UserError(Exception):
    """A problem the user can fix; shown as a plain message, without a traceback."""


def cfg() -> dict:
    return STATE["cfg"]


def need(*keys):
    names = {"wp_url": "WordPress site address", "wp_user": "WordPress username",
             "wp_app_password": "WordPress Application Password", "gemini_api_key": "Gemini API key",
             "text_model": "Gemini text model (click 'Detect models')",
             "image_model": "Gemini image model (click 'Detect models')", "pexels_api_key": "Pexels API key"}
    missing = [names.get(k, k) for k in keys if not cfg().get(k)]
    if missing:
        raise UserError("Please fill in Settings first: " + ", ".join(missing) + ".")


def wp() -> WordPress:
    need("wp_url", "wp_user", "wp_app_password")
    c = cfg()
    return WordPress(c["wp_url"], c["wp_user"], c["wp_app_password"])


def article_from(d: dict) -> Article:
    fields = Article.__dataclass_fields__
    return Article(**{k: v for k, v in (d or {}).items() if k in fields})


def recheck(a: Article) -> Article:
    a.body_html = sanitize_html(a.body_html)
    w = [x for x in a.warnings if not x.startswith(("Generic AI", "Possible invented", "Meta description"))]
    bad = find_banned(a.body_html)
    if bad:
        w.append("Generic AI phrases found: " + ", ".join(bad))
    fab = find_fabrication(a.body_html)
    if fab:
        w.append("Possible invented first-person claims (remove or replace with your real experience): "
                 + " | ".join(fab))
    n = len(a.meta_description)
    if n and not 120 <= n <= 160:
        w.append(f"Meta description is {n} characters; aim for 120-160.")
    a.warnings = w
    a.seo_report = seo_report(a, cfg().get("language") or "English")
    return a


def topic_check(topic: str, angle: str = "") -> dict:
    text = f"{topic} {angle}"
    sel = cfg().get("niches") or []
    found = niches.niches_of(text)
    return {"blocked": niches.is_blocked(text), "niches": found,
            "fits": bool(set(found) & set(sel)) or not sel}


def run_job(label: str, fn) -> str:
    jid = secrets.token_hex(6)
    job = {"id": jid, "label": label, "status": "running", "logs": [], "result": None, "error": "",
           "started": time.time()}
    JOBS[jid] = job

    def log(msg):
        job["logs"].append(time.strftime("%H:%M:%S ") + str(msg))

    def worker():
        try:
            job["result"] = fn(log)
            job["status"] = "done"
        except UserError as e:
            job["error"] = str(e)
            job["status"] = "error"
            system.log.info("%s: %s", label, e)
        except Exception as e:  # noqa: BLE001
            job["error"] = f"{type(e).__name__}: {e}"
            job["status"] = "error"
            log(traceback.format_exc(limit=3))
            system.log.error("%s failed: %s\n%s", label, e, traceback.format_exc(limit=5))
    threading.Thread(target=worker, daemon=True).start()
    # forget old jobs
    for k in [k for k, j in JOBS.items() if time.time() - j["started"] > 3600]:
        JOBS.pop(k, None)
    return jid


def site_domain() -> str:
    return re.sub(r"^https?://(www\.)?", "", (cfg().get("wp_url") or "your-site.com")).rstrip("/")


# ----------------------------------------------------------------------------- API actions

def api_state(_body):
    return {"app": config.APP_NAME, "version": config.APP_VERSION, "config": config.public(cfg()),
            "niches": niches.public_list(), "drafts_dir": str(config.DRAFTS_DIR),
            "usage": system.usage_summary(cfg())}


def _reload(new_cfg: dict) -> dict:
    with STATE["lock"]:
        STATE["cfg"] = new_cfg
        STATE["trends"] = []
        STATE.pop("posts_cache", None)
    return api_state(None)


def api_profile(body):
    action = body.get("action")
    try:
        if action == "switch":
            return _reload(config.switch_profile(body.get("name", "")))
        if action == "add":
            return _reload(config.add_profile(body.get("name", ""), bool(body.get("copy", True))))
        if action == "rename":
            old = cfg()["profile"]
            st = _reload(config.rename_profile(old, body.get("name", "")))
            planner.rename_profile(old, cfg()["profile"])
            return st
        if action == "delete":
            return _reload(config.delete_profile(body.get("name", "")))
    except (KeyError, ValueError) as e:
        raise UserError(str(e).strip("'") or "Site not found.")
    raise UserError("Unknown site action.")


def api_save_config(body):
    c = dict(cfg())
    for k, default in config.DEFAULTS.items():
        if k not in body:
            continue
        v = body[k]
        if k in SECRETS:
            if body.get("clear_" + k):
                c[k] = ""
            elif isinstance(v, str) and v.strip():
                c[k] = v.strip()
            continue
        if isinstance(default, bool):
            v = bool(v)
        elif isinstance(default, float):
            try:
                v = max(0.0, float(v or 0))
            except (TypeError, ValueError):
                v = default
        elif isinstance(default, int):
            try:
                v = int(v)
            except (TypeError, ValueError):
                v = default
        elif isinstance(default, list):
            v = [x for x in (v or []) if isinstance(x, str)]
        else:
            v = str(v or "").strip()
        c[k] = v
    c["target_words"] = max(500, min(4000, c["target_words"]))
    c["inline_images"] = max(0, min(6, c["inline_images"]))
    c["wp_url"] = c["wp_url"].rstrip("/")
    if c["wp_url"] and not c["wp_url"].startswith("http"):
        c["wp_url"] = "https://" + c["wp_url"]
    c["niches"] = [n for n in c["niches"] if n in niches.NICHES]
    c["posts_per_week"] = max(1, min(21, c["posts_per_week"]))
    if c.get("writer_provider") not in ("gemini", "openai", "anthropic"):
        c["writer_provider"] = "gemini"
    with STATE["lock"]:
        STATE["cfg"] = c
        config.save(c)
    return api_state(None)


def job_test_wordpress(log):
    w = wp()
    me = w.whoami()
    log(f"Logged in as {me.get('name')} ({', '.join(me.get('roles', []))}).")
    bridge = w.bridge_installed()
    posts = w.published_posts()
    cats = w.categories()
    return {"user": me.get("name"), "roles": me.get("roles", []), "bridge": bridge, "posts": len(posts),
            "categories": [html.unescape(c["name"]) for c in cats]}


def job_detect_models(log):
    need("gemini_api_key")
    g = Gemini(cfg()["gemini_api_key"])
    names = g.list_models()
    text_m, img_m = Gemini.pick_models(names)
    log(f"{len(names)} models available for this key.")
    api_save_config({"text_model": text_m, "image_model": img_m})
    return {"text_model": text_m, "image_model": img_m,
            "text_models": [n for n in names if n.startswith("gemini") and "image" not in n],
            "image_models": [n for n in names if "image" in n]}


def job_test_image(log):
    need("gemini_api_key", "image_model")
    g = Gemini(cfg()["gemini_api_key"], image_model=cfg()["image_model"])
    data, mime = g.generate_image("A clean modern desk with a laptop and a notebook at sunrise, photorealistic, "
                                  "no text, no logos", "16:9")
    log(f"Image OK ({len(data) // 1024} KB).")
    return {"image": f"data:{mime};base64," + base64.b64encode(data).decode()}


def job_test_pexels(log):
    need("pexels_api_key")
    hits = pexels_search(cfg()["pexels_api_key"], "laptop desk", count=1)
    if not hits:
        raise UserError("Pexels answered but returned no photos. Try again later.")
    log("Pexels OK.")
    return {"image": hits[0]["download_url"], "credit": hits[0]["photographer"]}


def job_trends(body):
    def run(log):
        c = cfg()
        geo = (body.get("geo") or c.get("trends_geo") or "US").upper()
        items = fetch_trending(geo)
        log(f"{len(items)} trending searches loaded for {geo}.")
        if body.get("ai", c.get("ai_trend_filter")) and c.get("gemini_api_key") and c.get("text_model"):
            try:
                topics.ai_classify(Gemini(c["gemini_api_key"], c["text_model"]), [t for t in items if not t.blocked])
                log("AI checked which trends really fit each niche.")
            except Exception as e:  # noqa: BLE001
                log(f"AI filter skipped ({e}); using keyword matching.")
        STATE["trends"] = items
        sel = c.get("niches") or []
        out = []
        for t in items:
            d = t.to_dict()
            d["fits"] = t.fits(sel)
            out.append(d)
        return {"geo": geo, "trends": out, "fit_count": sum(d["fits"] for d in out),
                "blocked_count": sum(d["blocked"] for d in out), "source": "trends",
                "trends_url": news.trends_page_url(geo, sel)}
    return run


def job_hot(body):
    def run(log):
        c = cfg()
        geo = (body.get("geo") or c.get("trends_geo") or "US").upper()
        sel = c.get("niches") or []
        if not sel:
            raise UserError("Tick at least one niche first.")
        items = news.fetch_hot(sel, geo, c.get("niche_custom", ""))
        log(f"{len(items)} hot stories in your niche for {geo}.")
        STATE["trends"] = items
        out = []
        for t in items:
            d = t.to_dict()
            d["fits"] = True
            out.append(d)
        return {"geo": geo, "trends": out, "fit_count": len(out), "blocked_count": 0, "source": "news",
                "trends_url": news.trends_page_url(geo, sel)}
    return run


def job_ideas(body):
    def run(log):
        need("gemini_api_key", "text_model")
        c = cfg()
        g = Gemini(c["gemini_api_key"], c["text_model"])
        if body.get("source") == "trends":
            if not STATE["trends"]:
                STATE["trends"] = fetch_trending(c.get("trends_geo") or "US")
            ideas = topics.ai_ideas(g, STATE["trends"], c.get("niches") or [], c.get("niche_custom", ""))
        else:
            ideas = topics.evergreen_ideas(g, c.get("niches") or [], c.get("niche_custom", ""),
                                           body.get("keyword", ""), c.get("audience", ""))
        log(f"{len(ideas)} ideas.")
        return {"ideas": ideas}
    return run


def job_suggest(body):
    def run(log):
        kw = (body.get("keyword") or "").strip()
        if not kw:
            raise UserError("Type a keyword first.")
        items = [s for s in fetch_suggestions(kw, cfg().get("trends_geo") or "US") if not niches.is_blocked(s)]
        log(f"{len(items)} Google suggestions for “{kw}”.")
        return {"suggestions": items}
    return run


def _site_lists(log):
    """Categories and published posts of the site (cached for 10 minutes)."""
    cache = STATE.get("posts_cache")
    if cache and time.time() - cache[0] < 600:
        return cache[1], cache[2]
    cats, posts = [], []
    if cfg().get("wp_app_password") and cfg().get("wp_url"):
        try:
            w = wp()
            cats, posts = w.categories(), w.published_posts(300)
            log(f"Read {len(posts)} posts and {len(cats)} categories from your site.")
            STATE["posts_cache"] = (time.time(), cats, posts)
        except Exception as e:  # noqa: BLE001
            log(f"Could not read your WordPress posts ({e}); continuing without internal links.")
    return cats, posts


def _mark_plan(plan_id, status, draft=""):
    if plan_id:
        try:
            planner.update(cfg()["profile"], plan_id, {"status": status, "draft": draft})
        except KeyError:
            pass


def job_write(body):
    """mode "full": research + write. "outline": research + outline only. "from_outline": write from the
    article's (edited) outline and existing research."""
    def run(log):
        mode = body.get("mode") or "full"
        if mode == "from_outline":
            a = article_from(body.get("article"))
            a.experience_notes = body.get("experience_notes", a.experience_notes)
            if not a.notes:
                raise UserError("Make the outline first.")
        else:
            topic = (body.get("topic") or "").strip()
            angle = (body.get("angle") or "").strip()
            if not topic:
                raise UserError("Enter a topic first.")
            a = Article(topic=topic, angle=angle, experience_notes=body.get("experience_notes", ""),
                        profile=cfg()["profile"], own_images=body.get("own_images") or [])
        if topic_check(a.topic, a.angle)["blocked"]:
            raise UserError("This topic is about gambling, adult content, violence or a tragedy. "
                            "Topics like this break AdSense rules, so the app won't write them.")
        need("gemini_api_key", "text_model")
        p = Pipeline(cfg(), log)
        cats, posts = _site_lists(log)
        if mode != "from_outline":
            items = [(n.get("title", ""), n.get("url", ""), n.get("source", "")) for n in body.get("news") or []]
            p.research(a, items)
        if mode == "outline":
            p.outline(a)
            log(f"Saved on this computer: {a.save()}")
            return {"article": asdict(a)}
        p.write(a, posts, cats)
        log(f"Saved on this computer: {a.save()}")
        _mark_plan(body.get("plan_id"), "written", a.file)
        return {"article": asdict(a)}
    return run


def job_factcheck(body):
    def run(log):
        need("gemini_api_key", "text_model")
        a = article_from(body.get("article"))
        Pipeline(cfg(), log).fact_check(a)
        a.save()
        return {"article": asdict(a)}
    return run


def job_social(body):
    def run(log):
        need("gemini_api_key", "text_model")
        a = article_from(body.get("article"))
        Pipeline(cfg(), log).social(a, body.get("url") or "")
        a.save()
        return {"article": asdict(a)}
    return run


def _week_count(w) -> int:
    """Posts created on the site in the last 7 days (published, scheduled or draft)."""
    now = time.time()
    n = 0
    for p in w.recent_posts(limit=50):
        try:
            if (now - time.mktime(time.strptime(p["date"][:19], "%Y-%m-%dT%H:%M:%S"))) / 86400 <= 7:
                n += 1
        except ValueError:
            continue
    return n


def job_link_suggest(body):
    """Which older posts should link to this new post, and where."""
    def run(log):
        need("gemini_api_key", "text_model")
        a = article_from(body.get("article"))
        url = body.get("url") or ""
        if not url:
            raise UserError("Save the draft in WordPress first, then publish it, so it has a link.")
        w = wp()
        _, posts = _site_lists(log)
        cands = [p for p in updater.candidates_for_links(a.title, posts) if p["url"].rstrip("/") != url.rstrip("/")]
        writer = make_writer(cfg(), Gemini(cfg()["gemini_api_key"], cfg()["text_model"]))
        out = []
        for p in cands[:5]:
            full = w.get_post(p["id"])
            if url.rstrip("/") in full["content"]:
                continue
            sug = updater.suggest_link(writer, full, a.title, a.meta_description)
            if sug:
                out.append(sug)
        log(f"{len(out)} older post(s) could link to this one.")
        return {"suggestions": out, "url": url}
    return run


def job_link_apply(body):
    def run(log):
        w = wp()
        post = w.get_post(int(body["post_id"]))
        new = updater.insert_link(post["content"], int(body["index"]), body["anchor"], body["url"])
        w.update_post(post["id"], {"content": new})
        log(f"Link added in “{post['title']}”.")
        return {"ok": True}
    return run


def job_posts(body):
    def run(log):
        return {"posts": wp().search_posts(body.get("q", ""))}
    return run


def job_update_suggest(body):
    def run(log):
        need("gemini_api_key", "text_model")
        w = wp()
        post = w.get_post(int(body["post_id"]))
        if "elementor" in post["content"][:3000].lower():
            log("Note: this post looks like it was built with Elementor; edit it in Elementor after applying.")
        log(f"Opened “{post['title']}” ({len(updater.plain(post['content']).split())} words).")
        g = Gemini(cfg()["gemini_api_key"], cfg()["text_model"])
        log("Step 1/2: searching Google for what changed since the post was written…")
        t0 = time.time()
        notes, sources = updater.research_changes(g, post)
        log(f"Research done in {int(time.time() - t0)}s ({len(sources)} sources).")
        writer = make_writer(cfg(), g)
        log("Step 2/2: preparing suggested changes (the longest step)…")
        t0 = time.time()
        plan = updater.suggest_update(writer, post, notes)
        log(f"Suggestions ready in {int(time.time() - t0)}s.")
        new_html, done = updater.apply_update(post["content"], plan, time.strftime("%B %d, %Y"))
        meta = trim_meta(str(plan.get("meta_description") or ""))
        return {"post": {k: post[k] for k in ("id", "title", "url", "date")}, "summary": plan.get("summary") or [],
                "changes": done, "new_html": new_html, "old_html": post["content"], "meta_description": meta,
                "notes": notes, "sources": [[t, u] for t, u in sources][:8]}
    return run


def job_update_apply(body):
    def run(log):
        w = wp()
        fields = {"content": body.get("content") or ""}
        if not fields["content"].strip():
            raise UserError("Nothing to save.")
        if body.get("meta_description") and w.bridge_installed():
            fields["meta"] = {"_yoast_wpseo_metadesc": body["meta_description"],
                              "rank_math_description": body["meta_description"]}
        w.update_post(int(body["post_id"]), fields)
        log("Post updated. WordPress keeps the old version under Revisions if you want to undo.")
        return {"ok": True}
    return run


def job_check_update(log):
    return system.check_update(cfg())


def job_detect_openai(log):
    need("openai_api_key")
    names = OpenAIWriter(cfg()["openai_api_key"], "x").list_models()
    best = pick_openai(names)
    api_save_config({"openai_model": best})
    log(f"OpenAI model: {best}")
    return {"model": best, "models": [n for n in names if n.startswith(("gpt-", "o"))]}


def job_detect_anthropic(log):
    need("anthropic_api_key")
    names = AnthropicWriter(cfg()["anthropic_api_key"], "x").list_models()
    best = pick_anthropic(names)
    api_save_config({"anthropic_model": best})
    log(f"Claude model: {best}")
    return {"model": best, "models": names}


def api_upload_image(body):
    data_url = body.get("data") or ""
    m = re.match(r"data:(image/[a-z+]+);base64,(.+)", data_url, re.S)
    if not m or m.group(1) not in IMAGE_TYPES:
        raise UserError("Use a JPG, PNG, WebP or GIF image.")
    raw = base64.b64decode(m.group(2))
    if len(raw) > 15 * 1024 * 1024:
        raise UserError("Image is larger than 15 MB.")
    config.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    name = secrets.token_hex(8) + IMAGE_TYPES[m.group(1)]
    (config.MEDIA_DIR / name).write_bytes(raw)
    return {"file": name}


def api_plan(body):
    prof = cfg()["profile"]
    act = body.get("action", "list")
    try:
        if act == "add":
            planner.add(prof, body.get("date", ""), body.get("topic", ""), body.get("angle", ""), body.get("note", ""))
        elif act == "update":
            planner.update(prof, body.get("id", ""), body.get("fields") or {})
        elif act == "delete":
            planner.delete(prof, body.get("id", ""))
    except (KeyError, ValueError) as e:
        raise UserError(str(e).strip("'") or "Plan item not found.")
    return {"items": planner.items(prof), "suggested_dates": planner.week_suggestion(cfg().get("posts_per_week", 3)),
            "posts_per_week": cfg().get("posts_per_week", 3)}


def api_report(_body):
    return {"text": system.problem_report(cfg(), JOBS)}


def api_seo(body):
    a = article_from(body.get("article"))
    return {"seo_report": seo_report(a, cfg().get("language") or "English")}


def job_preview(body):
    def run(log):
        a = article_from(body.get("article"))
        p = Pipeline(cfg(), log) if cfg().get("gemini_api_key") else None
        if p and a.experience_notes.strip() and not a.experience_html:
            p.polish_experience(a)
        content = p.final_html(a, [], False) if p else a.body_html
        e = html.escape
        page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{e(a.title)}</title>
<style>body{{font-family:Georgia,serif;max-width:760px;margin:24px auto;padding:0 16px;line-height:1.7;color:#1f2937}}
h1,h2,h3{{font-family:system-ui,Arial;line-height:1.25}} a{{color:#2563eb}}
.serp{{font-family:Arial;background:#f8fafc;border:1px solid #e2e8f0;padding:14px;border-radius:10px;font-size:14px}}
.serp .t{{color:#1a0dab;font-size:18px}} .serp .u{{color:#006621}} .note{{font-family:Arial;color:#64748b;font-size:13px}}
table{{border-collapse:collapse}} td,th{{border:1px solid #e2e8f0;padding:6px 10px}}</style></head><body>
<div class="serp"><div class="t">{e(a.seo_title or a.title)}</div><div class="u">{e(site_domain())} › {e(a.slug)}</div>
<div>{e(a.meta_description)}</div></div><h1>{e(a.title)}</h1>
<p class="note">Preview. Images are added when you save the draft to WordPress.</p>{content}</body></html>"""
        a.save()
        return {"html": page, "article": asdict(a)}
    return run


def job_publish(body):
    def run(log):
        need("wp_url", "wp_user", "wp_app_password", "gemini_api_key")
        a = article_from(body.get("article"))
        if not a.title or not a.body_html:
            raise UserError("Write the article first.")
        if topic_check(a.topic, a.angle)["blocked"]:
            raise UserError("This topic breaks AdSense rules, so the app won't save it.")
        p = Pipeline(cfg(), log)
        w = wp()
        limit = int(cfg().get("posts_per_week", 3) or 3)
        if not body.get("force"):
            n = _week_count(w)
            if n >= limit:
                raise UserError(f"WEEKLY_LIMIT: Your site already has {n} new posts in the last 7 days "
                                f"(your limit is {limit}). Too many posts at once can look like spam to Google.")
        if a.experience_notes.strip() and not a.experience_html:
            p.polish_experience(a)
        a.profile = a.profile or cfg()["profile"]
        res = p.publish_draft(a, w)
        link = w.edit_link(res["id"])
        _mark_plan(body.get("plan_id"), "draft", a.file)
        STATE.pop("posts_cache", None)
        log(f"Draft saved in WordPress (ID {res['id']}). Open it, read it once and click Publish yourself.")
        return {"id": res["id"], "edit_link": link, "article": asdict(a), "link": res.get("link", "")}
    return run


def job_site_stats(log):
    w = wp()
    posts = w.recent_posts()
    now = time.time()

    def age_days(p):
        try:
            return (now - time.mktime(time.strptime(p["date"][:19], "%Y-%m-%dT%H:%M:%S"))) / 86400
        except ValueError:
            return 999
    pub = [p for p in posts if p["status"] == "publish"]
    return {"published_7d": sum(age_days(p) <= 7 for p in pub), "drafts": sum(p["status"] == "draft" for p in posts),
            "recent": posts[:8]}


def api_drafts(_body):
    out = []
    if config.DRAFTS_DIR.is_dir():
        for f in sorted(config.DRAFTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:200]:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if d.get("profile") and d.get("profile") != cfg()["profile"]:
                continue
            out.append({"name": f.name, "title": d.get("title") or d.get("topic"), "topic": d.get("topic"),
                        "created": d.get("created", ""), "wp_post_id": d.get("wp_post_id", 0),
                        "words": len(re.sub(r"<[^>]+>", " ", d.get("body_html", "")).split())})
    return {"drafts": out}


def api_draft(body):
    name = os.path.basename(body.get("name", ""))
    path = config.DRAFTS_DIR / name
    if not name.endswith(".json") or not path.is_file():
        raise UserError("Draft not found.")
    return {"article": asdict(Article.load(str(path)))}


def api_delete_draft(body):
    name = os.path.basename(body.get("name", ""))
    path = config.DRAFTS_DIR / name
    if name.endswith(".json") and path.is_file():
        path.unlink()
    return api_drafts(None)


def api_save_local(body):
    a = recheck(article_from(body.get("article")))
    return {"path": a.save(), "article": asdict(a)}


def api_recheck(body):
    return {"article": asdict(recheck(article_from(body.get("article"))))}


def api_job(body):
    j = JOBS.get(body.get("id", ""))
    if not j:
        raise UserError("Unknown job.")
    return {k: j[k] for k in ("id", "label", "status", "logs", "result", "error")}


def start(label, fn):
    return lambda body: {"job": run_job(label, fn(body) if fn.__code__.co_varnames[:1] == ("body",) else fn)}


ROUTES = {
    "state": api_state,
    "profile": api_profile,
    "upload_image": api_upload_image,
    "plan": api_plan,
    "report": api_report,
    "seo": api_seo,
    "factcheck": start("Fact-check", job_factcheck),
    "social": start("Social posts", job_social),
    "link_suggest": start("Links from older posts", job_link_suggest),
    "link_apply": start("Add link", job_link_apply),
    "posts": start("Your posts", job_posts),
    "update_suggest": start("Update an old post", job_update_suggest),
    "update_apply": start("Save post update", job_update_apply),
    "check_update": start("Check for updates", job_check_update),
    "detect_openai": start("Detect OpenAI models", job_detect_openai),
    "detect_anthropic": start("Detect Claude models", job_detect_anthropic),
    "config": api_save_config,
    "check_topic": lambda b: topic_check(b.get("topic", ""), b.get("angle", "")),
    "recheck": api_recheck,
    "save_local": api_save_local,
    "drafts": api_drafts,
    "draft": api_draft,
    "delete_draft": api_delete_draft,
    "job": api_job,
    "test_wordpress": start("Test WordPress", job_test_wordpress),
    "detect_models": start("Detect Gemini models", job_detect_models),
    "test_image": start("Test image", job_test_image),
    "test_pexels": start("Test Pexels", job_test_pexels),
    "site_stats": start("Site stats", job_site_stats),
    "trends": start("Trending searches", job_trends),
    "hot": start("Hot in my niche", job_hot),
    "ideas": start("Topic ideas", job_ideas),
    "suggest": start("Google suggestions", job_suggest),
    "write": start("Research + write", job_write),
    "preview": start("Preview", job_preview),
    "publish": start("Save draft to WordPress", job_publish),
}


# ----------------------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "BlogDraftStudio"

    def log_message(self, *_):
        pass

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode("utf-8"))

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, b"Forbidden", "text/plain")
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            page = (WEB / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
            self.send_response(200)
            body = page.encode("utf-8")
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
                             "script-src 'self'; frame-src 'self' blob:; connect-src 'self'")
            self.end_headers()
            return self.wfile.write(body)
        if path.startswith("/media/"):
            f = config.MEDIA_DIR / os.path.basename(path)
            if f.is_file() and f.suffix.lower() in IMAGE_TYPES.values():
                return self._send(200, f.read_bytes(), mimetypes.guess_type(str(f))[0] or "image/jpeg")
        if path.startswith("/static/"):
            f = (WEB / path[len("/static/"):]).resolve()
            if WEB.resolve() in f.parents and f.is_file():
                # fixed types: the Windows registry sometimes maps .js to text/plain, which browsers refuse
                ctype = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                         ".svg": "image/svg+xml", ".html": "text/html; charset=utf-8"}.get(
                    f.suffix.lower()) or mimetypes.guess_type(str(f))[0] or "application/octet-stream"
                return self._send(200, f.read_bytes(), ctype)
        self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-Token") != TOKEN:
            return self._json(403, {"error": "Forbidden"})
        path = urlparse(self.path).path
        if path == "/api/quit":
            self._json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        name = path[len("/api/"):] if path.startswith("/api/") else ""
        fn = ROUTES.get(name)
        if not fn:
            return self._json(404, {"error": "Unknown action"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            self._json(200, fn(body))
        except UserError as e:
            self._json(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            self._json(500, {"error": f"{type(e).__name__}: {e}"})


class LocalServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second program bind a port that is already in use, so two copies of the
    # app would silently share 8765. Never reuse there; elsewhere it only skips the TIME_WAIT delay.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True

    def server_bind(self):
        if os.name == "nt" and hasattr(__import__("socket"), "SO_EXCLUSIVEADDRUSE"):
            import socket
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(port=None) -> ThreadingHTTPServer:
    """port=None: the usual ports 8765-8767 (else any free one). port=0: any free port (tests)."""
    for p in ([port] if port is not None else [8765, 8766, 8767, 0]):
        try:
            return LocalServer(("127.0.0.1", p), Handler)
        except OSError:
            continue
    raise SystemExit("Could not start the local server.")


INSTANCE_FILE = config.CONFIG_DIR / "instance.json"


def _other_instance() -> dict:
    """The app that may already be running (its port, token and version), if it answers."""
    try:
        info = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
        req = urllib.request.Request(f"http://127.0.0.1:{int(info['port'])}/api/state", data=b"{}", method="POST",
                                     headers={"X-Token": info["token"], "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as r:
            st = json.loads(r.read())
        return {"port": int(info["port"]), "token": info["token"], "version": st.get("version")}
    except Exception:  # noqa: BLE001 - nothing running, or not ours
        return {}


def _stop_instance(other: dict) -> None:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{other['port']}/api/quit", data=b"{}", method="POST",
                                     headers={"X-Token": other["token"]})
        urllib.request.urlopen(req, timeout=3).read()
        time.sleep(1.0)
    except Exception:  # noqa: BLE001
        pass


def main():
    system.setup_logging()
    system.log.info("%s %s starting", config.APP_NAME, config.APP_VERSION)
    other = _other_instance()
    if other and other["version"] == config.APP_VERSION and "--new" not in sys.argv:
        # already running: just open it instead of starting a second copy
        webbrowser.open(f"http://127.0.0.1:{other['port']}/")
        return
    if other:
        system.log.info("Stopping older running version %s", other["version"])
        _stop_instance(other)
    srv = make_server()
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    try:
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        INSTANCE_FILE.write_text(json.dumps({"port": port, "token": TOKEN, "pid": os.getpid()}), encoding="utf-8")
        os.chmod(INSTANCE_FILE, 0o600)
    except OSError:
        pass
    print(f"{config.APP_NAME} is running at {url}  (close this window or click Quit in the app to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if json.loads(INSTANCE_FILE.read_text(encoding="utf-8")).get("token") == TOKEN:
                INSTANCE_FILE.unlink()
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    main()
