import base64
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("BLOGDRAFT_HOME", tempfile.mkdtemp())

from core import config, llm, planner, system, updater, writer  # noqa: E402
from core.writer import Article, Pipeline  # noqa: E402


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.patch = mock.patch.multiple(config, CONFIG_DIR=config.Path(self.dir),
                                         CONFIG_FILE=config.Path(self.dir) / "config.json")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_migrates_flat_config_and_switches(self):
        (config.CONFIG_FILE).write_text(json.dumps({"gemini_api_key": "G", "wp_url": "https://a.com",
                                                    "site_name": "TechKrak", "niches": ["tech"]}))
        c = config.load()
        self.assertEqual((c["profile"], c["gemini_api_key"], c["wp_url"]), ("TechKrak", "G", "https://a.com"))
        c = config.add_profile("Food Blog")
        self.assertEqual(c["profile"], "Food Blog")
        self.assertEqual(c["wp_url"], "")                 # connection is not copied
        self.assertEqual(c["gemini_api_key"], "G")        # keys are shared
        c["niches"] = ["food"]
        c["wp_url"] = "https://food.com"
        config.save(c)
        c = config.switch_profile("TechKrak")
        self.assertEqual((c["niches"], c["wp_url"]), (["tech"], "https://a.com"))
        c = config.rename_profile("TechKrak", "Tech Site")
        self.assertEqual(c["profiles"], ["Tech Site", "Food Blog"])
        c = config.delete_profile("Tech Site")
        self.assertEqual(c["profile"], "Food Blog")
        with self.assertRaises(ValueError):
            config.delete_profile("Food Blog")

    def test_masked_has_no_secrets(self):
        m = config.masked({"gemini_api_key": "SECRET123456", "wp_app_password": "", "site_name": "x"})
        self.assertEqual(m["gemini_api_key"], "set")
        self.assertEqual(m["wp_app_password"], "empty")


class PlannerAndSystemTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.patch = mock.patch.multiple(config, CONFIG_DIR=config.Path(self.dir),
                                         LOG_FILE=config.Path(self.dir) / "app.log")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_plan_crud(self):
        it = planner.add("A", "2026-11-10", "Topic one")
        planner.add("A", "bad-date", "Topic two")
        planner.add("B", "2026-11-11", "Other site")
        self.assertEqual(len(planner.items("A")), 2)
        planner.update("A", it["id"], {"status": "draft", "date": "2026-11-12"})
        self.assertEqual(planner.items("A")[-1]["status"], "draft")
        planner.delete("A", it["id"])
        self.assertEqual(len(planner.items("A")), 1)
        self.assertEqual(len(planner.week_suggestion(3)), 3)
        with self.assertRaises(ValueError):
            planner.add("A", "", "  ")

    def test_usage_and_report(self):
        system.record("gemini", "m", 1000, 500, 0)
        system.record("gemini", "img", 0, 0, 2)
        u = system.usage_summary({"price_in_per_m": 1.0, "price_out_per_m": 2.0, "price_image": 0.05})
        self.assertEqual((u["requests"], u["tokens_in"], u["images"]), (2, 1000, 2))
        self.assertAlmostEqual(u["cost"], 0.1, places=2)
        config.LOG_FILE.write_text("line with SECRETKEY999 inside\n")
        rep = system.problem_report({"gemini_api_key": "SECRETKEY999", "site_name": "x"}, {})
        self.assertNotIn("SECRETKEY999", rep)
        self.assertIn(config.APP_VERSION, rep)

    def test_update_check(self):
        with mock.patch.object(system.requests, "get") as g:
            g.return_value = mock.Mock(json=lambda: {"version": "99.0", "url": "https://x/y.zip", "notes": "n"},
                                       raise_for_status=lambda: None)
            u = system.check_update({"update_url": "https://x/latest.json"})
        self.assertTrue(u["available"])
        self.assertFalse(system.check_update({"update_url": ""})["configured"])


class UpdaterTests(unittest.TestCase):
    HTML = ("<p>The phone costs $799 and ships in March.</p><h2>Price</h2><p>It is the cheapest model.</p>"
            "<h2>Frequently asked questions</h2><h3>Q?</h3><p>A.</p>")

    def test_apply_update_only_exact_matches(self):
        plan = {"edits": [{"find": "The phone costs $799 and ships in March.", "replace": "The phone now costs $699."},
                          {"find": "Not in the article.", "replace": "x"}],
                "new_sections": [{"after_heading": "Price", "html": "<h2>New in 2026</h2><p>Update.</p><script>x</script>"}]}
        out, log = updater.apply_update(self.HTML, plan, "Nov 8, 2026")
        self.assertIn("$699", out)
        self.assertNotIn("<script>", out)
        self.assertLess(out.index("New in 2026"), out.index("Frequently asked"))
        self.assertTrue(out.startswith("<p><em>Updated on Nov 8, 2026.</em></p>"))
        self.assertTrue(any(x.startswith("Skipped") for x in log))

    def test_link_insert(self):
        content = "<p>" + "Battery life matters a lot when you travel with your phone every day. " * 2 + "</p><p>short</p>"

        class W:
            def generate_json(self, *a, **k):
                return {"p": 0, "anchor": "Battery life"}
        sug = updater.suggest_link(W(), {"id": 5, "title": "Old", "content": content}, "New", "summary")
        self.assertEqual(sug["anchor"], "Battery life")
        new = updater.insert_link(content, sug["index"], sug["anchor"], "https://b.com/new/")
        self.assertIn('<a href="https://b.com/new/">Battery life</a>', new)
        self.assertEqual(new.count("<a "), 1)

        class Bad:
            def generate_json(self, *a, **k):
                return {"p": 0, "anchor": "words that are not there"}
        self.assertEqual(updater.suggest_link(Bad(), {"id": 5, "title": "Old", "content": content}, "N", "s"), {})


class WriterV3Tests(unittest.TestCase):
    def test_seo_report_and_similar(self):
        a = Article(topic="x", focus_keyword="battery life", seo_title="Battery life tips", slug="battery-life-tips",
                    meta_description="m" * 140, body_html="<p>Battery life is key. Short sentence.</p><h2>A</h2><p>b</p>")
        rows = {r["label"]: r for r in writer.seo_report(a)}
        self.assertTrue(rows["Keyword in first paragraph"]["ok"])
        self.assertTrue(rows["Keyword in slug"]["ok"])
        self.assertFalse(rows["Length"]["ok"])
        sim = writer.similar_posts("iPhone 17 battery drain fix", [{"title": "How to fix iPhone 17 battery drain", "url": "u"},
                                                                   {"title": "Best pizza recipe", "url": "p"}])
        self.assertEqual([p["url"] for p in sim], ["u"])

    def test_outline_then_write_uses_outline(self):
        seen = {}

        class G:
            text_model = "m"
            image_model = ""

            def research(self, prompt, system=""):
                return "notes", []

            def generate_json(self, prompt, system="", temperature=0.7):
                if "Plan an article" in prompt:
                    return {"sections": [{"h2": "Why it matters", "points": ["a", "b"]}], "faq": ["Q1?"]}
                seen["prompt"] = prompt
                return {"title": "T", "seo_title": "T", "slug": "t", "focus_keyword": "t", "meta_description": "d",
                        "body_html": "<p>x</p>", "featured_image": {}, "inline_images": []}
        cfg = dict(config.DEFAULTS, gemini_api_key="k", text_model="m")
        with mock.patch.object(writer, "resolve_url", lambda u: u):
            p = Pipeline(cfg, log=lambda m: None, gemini=G())
            a = Article(topic="t")
            p.research(a)
            p.outline(a)
            self.assertIn("## Why it matters", a.outline)
            self.assertIn("## Frequently asked questions", a.outline)
            a.outline += "\n- my own point"
            p.write(a, [], [])
        self.assertIn("my own point", seen["prompt"])

    def test_article_file_name_is_stable(self):
        with mock.patch.object(config, "DRAFTS_DIR", config.Path(tempfile.mkdtemp())):
            a = Article(topic="Some topic")
            p1 = a.save()
            a.slug = "changed-slug"
            p2 = a.save()
        self.assertEqual(p1, p2)


class LLMTests(unittest.TestCase):
    def test_pickers(self):
        self.assertEqual(llm.pick_openai(["gpt-4o-mini", "gpt-5", "gpt-5-mini", "gpt-image-1", "gpt-4o-2024-08-06",
                                          "text-embedding-3", "gpt-4o-realtime"]), "gpt-5")
        self.assertEqual(llm.pick_anthropic(["claude-haiku-x", "claude-sonnet-y", "claude-opus-z"]), "claude-sonnet-y")

    def test_make_writer(self):
        g = object()
        self.assertIs(llm.make_writer({"writer_provider": "gemini"}, g), g)
        w = llm.make_writer({"writer_provider": "openai", "openai_api_key": "k", "openai_model": "gpt-5"}, g)
        self.assertIsInstance(w, llm.OpenAIWriter)
        with self.assertRaises(llm.LLMError):
            llm.make_writer({"writer_provider": "anthropic", "anthropic_api_key": "", "anthropic_model": ""}, g)

    def test_openai_json_and_usage(self):
        w = llm.OpenAIWriter("k", "gpt-5")
        resp = {"choices": [{"message": {"content": '{"a": 1}'}}], "usage": {"prompt_tokens": 3, "completion_tokens": 4}}
        with mock.patch.object(llm, "_retry_post", return_value=resp) as p, mock.patch.object(llm, "_record") as r:
            self.assertEqual(w.generate_json("hi"), {"a": 1})
        self.assertEqual(p.call_args[0][2]["response_format"], {"type": "json_object"})
        r.assert_called_with("openai", "gpt-5", 3, 4)


class ServerV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        import server
        cls.server = server
        cls.srv = server.make_server(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def api(self, name, body=None):
        import urllib.request
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/{name}", data=json.dumps(body or {}).encode(),
                                   method="POST", headers={"Content-Type": "application/json", "X-Token": self.server.TOKEN})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_upload_plan_profile_report(self):
        png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
        code, r = self.api("upload_image", {"data": png})
        self.assertEqual(code, 200)
        self.assertTrue(r["file"].endswith(".png"))
        code, _ = self.api("upload_image", {"data": "data:text/html;base64,PGI+"})
        self.assertEqual(code, 400)
        _, p = self.api("plan", {"action": "add", "date": "2026-11-20", "topic": "Plan me"})
        self.assertTrue(any(i["topic"] == "Plan me" for i in p["items"]))
        _, st = self.api("profile", {"action": "add", "name": "Second Site"})
        self.assertEqual(st["config"]["profile"], "Second Site")
        _, p2 = self.api("plan", {})
        self.assertFalse(any(i["topic"] == "Plan me" for i in p2["items"]))   # plans are per site
        self.api("config", {"gemini_api_key": "AIzaTOPSECRET42"})
        _, rep = self.api("report", {})
        self.assertNotIn("AIzaTOPSECRET42", rep["text"])
        _, seo = self.api("seo", {"article": {"topic": "t", "body_html": "<p>hello world</p>", "focus_keyword": "hello"}})
        self.assertTrue(any(r["label"] == "Keyword in first paragraph" for r in seo["seo_report"]))


if __name__ == "__main__":
    unittest.main()
