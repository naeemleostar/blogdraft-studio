"""WordPress REST API client (Application Password auth)."""
import html
import mimetypes
import re

import requests


class WPError(RuntimeError):
    pass


class WordPress:
    def __init__(self, url: str, user: str, app_password: str, timeout: int = 60):
        if not (url and user and app_password):
            raise WPError("WordPress URL, username and Application Password are required (Settings tab).")
        self.base = url.rstrip("/") + "/wp-json/wp/v2"
        self.root = url.rstrip("/")
        self.s = requests.Session()
        self.s.auth = (user.strip(), app_password.replace(" ", "").strip())
        self.s.headers["User-Agent"] = "BlogDraftStudio/2.0"
        self.timeout = timeout

    def _req(self, method: str, path: str, **kw) -> requests.Response:
        url = path if path.startswith("http") else f"{self.base}/{path.lstrip('/')}"
        r = self.s.request(method, url, timeout=self.timeout, **kw)
        if not r.ok:
            msg = r.text[:400]
            if r.status_code == 401:
                msg += ("\n\nLogin failed. Check username + Application Password "
                        "(WordPress > Users > Profile > Application Passwords).")
            raise WPError(f"WordPress HTTP {r.status_code}: {msg}")
        return r

    # ---------- checks ----------
    def whoami(self) -> dict:
        return self._req("GET", "users/me", params={"context": "edit"}).json()

    def bridge_installed(self) -> bool:
        """True if the bridge plugin exposes Yoast fields over REST (new or old plugin)."""
        for ns in ("blogdraft-studio", "techkrak-writer"):
            try:
                if self.s.get(f"{self.root}/wp-json/{ns}/v1/ping", timeout=self.timeout).ok:
                    return True
            except requests.RequestException:
                pass
        return False

    def recent_posts(self, status: str = "publish,draft,future", limit: int = 30) -> list:
        r = self._req("GET", "posts", params={"per_page": limit, "status": status, "context": "edit",
                                              "_fields": "id,date,status,title,link"})
        return [{"id": p["id"], "date": p["date"], "status": p["status"],
                 "title": html.unescape(p["title"].get("raw") or p["title"].get("rendered", "")),
                 "url": p["link"]} for p in r.json()]

    # ---------- content lists ----------
    def categories(self) -> list:
        return self._req("GET", "categories", params={"per_page": 100, "_fields": "id,name,slug,count"}).json()

    def published_posts(self, limit: int = 100) -> list:
        out, page = [], 1
        while len(out) < limit:
            r = self.s.get(f"{self.base}/posts", params={"per_page": 100, "page": page, "status": "publish",
                                                         "_fields": "id,date,title,link,excerpt,categories"},
                           timeout=self.timeout)
            if not r.ok:
                break
            batch = r.json()
            for p in batch:
                out.append({"id": p["id"], "date": p.get("date", ""), "title": html.unescape(p["title"]["rendered"]), "url": p["link"],
                            "excerpt": re.sub(r"<[^>]+>", "", html.unescape(p["excerpt"]["rendered"]))[:160].strip()})
            if len(batch) < 100:
                break
            page += 1
        return out[:limit]

    def tag_ids(self, names: list) -> list:
        ids = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            found = self._req("GET", "tags", params={"search": name, "per_page": 20, "_fields": "id,name"}).json()
            match = next((t for t in found if html.unescape(t["name"]).lower() == name.lower()), None)
            if match:
                ids.append(match["id"])
                continue
            r = self.s.post(f"{self.base}/tags", json={"name": name}, timeout=self.timeout)
            if r.ok:
                ids.append(r.json()["id"])
            elif r.status_code == 400 and "term_exists" in r.text:
                ids.append(r.json().get("data", {}).get("term_id"))
        return [i for i in ids if i]

    def search_posts(self, query: str = "", limit: int = 30) -> list:
        params = {"per_page": limit, "status": "publish", "_fields": "id,date,modified,title,link"}
        if query:
            params["search"] = query
        r = self._req("GET", "posts", params=params)
        return [{"id": p["id"], "date": p["date"], "modified": p.get("modified", ""),
                 "title": html.unescape(p["title"]["rendered"]), "url": p["link"]} for p in r.json()]

    def get_post(self, post_id: int) -> dict:
        p = self._req("GET", f"posts/{int(post_id)}", params={"context": "edit"}).json()
        return {"id": p["id"], "date": p.get("date", ""), "status": p.get("status", ""), "url": p.get("link", ""),
                "title": html.unescape(p["title"].get("raw") or p["title"].get("rendered", "")),
                "content": p["content"].get("raw") or p["content"].get("rendered", ""),
                "excerpt": p.get("excerpt", {}).get("raw", "")}

    def update_post(self, post_id: int, fields: dict) -> dict:
        return self._req("POST", f"posts/{int(post_id)}", json=fields).json()

    # ---------- media ----------
    def upload_image(self, data: bytes, mime: str, filename: str, alt: str, caption: str, title: str) -> dict:
        ext = mimetypes.guess_extension(mime) or ".png"
        if ext == ".jpe":
            ext = ".jpg"
        fname = re.sub(r"[^a-z0-9-]+", "-", filename.lower()).strip("-")[:60] + ext
        r = self._req("POST", "media", data=data,
                      headers={"Content-Type": mime, "Content-Disposition": f'attachment; filename="{fname}"'})
        media = r.json()
        self._req("POST", f"media/{media['id']}", json={"alt_text": alt, "caption": caption, "title": title})
        return {"id": media["id"], "url": media.get("source_url", "")}

    # ---------- posts ----------
    def create_draft(self, post: dict) -> dict:
        body = {k: v for k, v in post.items() if v not in (None, "", [])}
        body["status"] = "draft"
        r = self._req("POST", "posts", json=body)
        return r.json()

    def edit_link(self, post_id: int) -> str:
        return f"{self.root}/wp-admin/post.php?post={post_id}&action=edit"
