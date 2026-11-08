import base64
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["BLOGDRAFT_HOME"] = tempfile.mkdtemp()

from core import trends, writer, gemini, niches, config  # noqa: E402
from core.writer import Article, Pipeline  # noqa: E402

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
<item><title>iphone 17 update</title><ht:approx_traffic>200K+</ht:approx_traffic>
<ht:news_item><ht:news_item_title>Apple releases iOS fix</ht:news_item_title><ht:news_item_url>https://example.com/a</ht:news_item_url><ht:news_item_source>The Verge</ht:news_item_source></ht:news_item></item>
<item><title>chiefs vs bills</title><ht:approx_traffic>1M+</ht:approx_traffic></item>
</channel></rss>"""


class TrendsTests(unittest.TestCase):
    def test_parse(self):
        items = trends.parse_trends_rss(RSS)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].traffic, "200K+")
        self.assertEqual(items[0].news[0][2], "The Verge")
        self.assertIn("tech", items[0].matched_niches)
        self.assertEqual(items[1].matched_niches, ["sports"])

    def test_sports_only_for_sports_niche(self):
        for title in ["Rockets vs Mavericks Injury Report and Game Preview",
                      "Magic vs. Hawks Season Opener: Preview, Lineups, and Stream"]:
            t = trends.Trend(title, news=[(title, "", "")])
            self.assertFalse(t.fits(["tech", "ai"]), title)
            self.assertTrue(t.fits(["sports"]), title)

    def test_always_blocked(self):
        for title in ["Oregon State vs. Washington State: Preview, Odds, and Stream", "Powerball jackpot tonight",
                      "Famous rapper dies at 45", "Mall shooting suspect arrested"]:
            self.assertTrue(niches.is_blocked(title), title)
            self.assertFalse(trends.Trend(title).fits(list(niches.NICHES)), title)

    def test_niche_matching(self):
        cases = {"Starlink Explained: Satellite Internet Plans": "tech", "ChatGPT down for users": "ai",
                 "Mortgage rates drop again": "finance", "Easy pumpkin pie recipe": "food",
                 "Bitcoin price hits record": "crypto", "Northern lights forecast tonight": "science",
                 "GTA 6 trailer": "gaming", "Best dog food for puppies": "pets"}
        for title, niche in cases.items():
            self.assertIn(niche, niches.niches_of(title), title)
        self.assertFalse(trends.Trend("Instagram Apple TV app").fits(["food"]))

    def test_news_alone_needs_two_headlines(self):
        t = trends.Trend("frank", news=[("Frank app hacked, data breach", "", ""), ("Cybersecurity firm warns", "", "")])
        self.assertIn("tech", t.matched_niches)
        self.assertNotIn("tech", trends.Trend("frank", news=[("Frank app", "", "")]).matched_niches)

    def test_ai_niches_override(self):
        t = trends.Trend("Hawks vs Magic", news=[("Watch on YouTube TV app", "", "")])
        t.ai_niches = ["sports"]
        self.assertFalse(t.fits(["tech"]))
        self.assertTrue(t.fits(["sports"]))


class GeminiTests(unittest.TestCase):
    def test_pick_models(self):
        names = ["gemini-2.5-flash", "gemini-3-flash", "gemini-3-pro", "gemini-3.1-flash-image",
                 "gemini-3.1-flash-lite-image", "gemini-3-pro-image", "text-embedding-004",
                 "gemini-3-flash-preview-tts"]
        t, i = gemini.Gemini.pick_models(names)
        self.assertEqual(t, "gemini-3-flash")
        self.assertEqual(i, "gemini-3.1-flash-image")

    def test_json_loose(self):
        self.assertEqual(gemini.parse_json_loose('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(gemini.parse_json_loose('noise {"a": 2} tail'), {"a": 2})


class WriterHelperTests(unittest.TestCase):
    def test_links_and_sanitize(self):
        body = ('<h1>Big</h1><p style="color:red">Hi <a href="https://good.com/x">ok</a> and '
                '<a href="https://made-up.com/y">fake</a></p><script>x</script><h2>Introduction</h2>')
        body = writer.sanitize_html(body)
        self.assertNotIn("<h1", body)
        self.assertNotIn("style=", body)
        self.assertNotIn("script", body)
        self.assertNotIn("Introduction", body)
        out, removed = writer.strip_disallowed_links(body, {"https://good.com/x/"})
        self.assertIn('href="https://good.com/x"', out)
        self.assertNotIn("made-up.com", out)
        self.assertIn("fake", out)
        self.assertEqual(removed, ["https://made-up.com/y"])

    def test_fabrication_and_banned(self):
        h = "<p>I tested the phone for two weeks. It is fast.</p><p>Let's dive in to the details.</p>"
        self.assertTrue(writer.find_fabrication(h))
        self.assertIn("let's dive in", writer.find_banned(h))
        self.assertFalse(writer.find_fabrication("<p>The phone ships in March.</p>"))

    def test_meta_trim(self):
        m = writer.trim_meta("word " * 60)
        self.assertLessEqual(len(m), 156)

    def test_build_final(self):
        a = Article(topic="t", body_html="<p>Intro</p><h2>A</h2><p>a1</p><!--MY_EXPERIENCE--><h2>B</h2><p>b1</p>",
                    experience_html="<h2>How I use it</h2><p>I use it daily.</p>",
                    sources=[["Src", "https://src.com/x"]])
        fig = writer.figure_html("https://img/1.png", "alt", "AI-generated image")
        out = a and writer.build_final_html(a, [(2, fig)], ai_note=True)
        self.assertIn("How I use it", out)
        self.assertNotIn("MY_EXPERIENCE", out)
        self.assertIn("<figcaption>AI-generated image</figcaption>", out)
        self.assertTrue(out.index("b1") < out.index("figure"))
        self.assertIn("<h2>Sources</h2>", out)
        self.assertIn("created with AI", out)

    def test_clean_sources(self):
        raw = [("a", "https://x.com/1"), ("b", "https://x.com/1/"), ("c", "bad"), ("d", "https://y.com/2")]
        out = writer.clean_sources(raw, resolve=lambda u: u)
        self.assertEqual([u for _, u in out], ["https://x.com/1", "https://y.com/2"])


class FakeGemini:
    def __init__(self, *a, **k):
        self.text_model = "gemini-3-flash"
        self.image_model = "gemini-3.1-flash-image"

    def research(self, prompt, system=""):
        assert "Topic:" in prompt
        return ("1. Apple released iOS 26.1 on Oct 1 2026 (Apple).", [("apple.com", "https://www.apple.com/newsroom/x")])

    def generate_json(self, prompt, system="", temperature=0.7):
        if "Author's notes" in prompt:
            return {"heading": "How I use it myself", "paragraphs": ["I use an iPhone 13 Pro."]}
        assert "INTERNAL ARTICLES" in prompt and "techkrak.com/old-post" in prompt
        return {
            "title": "iOS 26.1: What Changed", "seo_title": "iOS 26.1 update: what changed", "slug": "iOS 26.1 What Changed!",
            "focus_keyword": "iOS 26.1 update", "meta_description": "iOS 26.1 update explained " * 10,
            "excerpt": "Short.", "category": "Tech News", "tags": ["iOS", "Apple", " "],
            "body_html": ('<p>Apple released iOS 26.1.</p><h2>What changed</h2><p>Fixes. See '
                          '<a href="https://www.apple.com/newsroom/x">Apple</a> and '
                          '<a href="https://techkrak.com/old-post/">our guide</a> and '
                          '<a href="https://techkrak.com/other/">more</a> and <a href="https://invented.com">x</a>.</p>'
                          '<!--MY_EXPERIENCE--><h2>What this means for you</h2><p>Update now.</p>'),
            "featured_image": {"prompt": "phone on desk", "alt": "phone", "stock_query": "iphone"},
            "inline_images": [{"after_h2": 1, "prompt": "settings screen", "alt": "settings", "stock_query": "phone"}],
        }

    def generate_image(self, prompt, ar="16:9"):
        assert "No text" in prompt
        return b"\x89PNG fake", "image/png"


class FakeWP:
    def __init__(self):
        self.uploads, self.created = [], None

    def categories(self):
        return [{"id": 17, "name": "Tech News"}, {"id": 1, "name": "Uncategorized"}]

    def tag_ids(self, names):
        return list(range(100, 100 + len(names)))

    def upload_image(self, data, mime, filename, alt, caption, title):
        self.uploads.append((filename, caption))
        return {"id": 500 + len(self.uploads), "url": f"https://techkrak.com/wp-content/uploads/{filename}.png"}

    def bridge_installed(self):
        return True

    def create_draft(self, post):
        self.created = post
        return {"id": 999, **post}


class PipelineTests(unittest.TestCase):
    def test_end_to_end(self):
        cfg = dict(writer.config.DEFAULTS, gemini_api_key="k", text_model="m", image_model="im")
        with mock.patch.object(writer, "Gemini", FakeGemini), \
             mock.patch.object(writer, "resolve_url", lambda u: u):
            p = Pipeline(cfg, log=lambda m: None)
            a = Article(topic="iOS 26.1 update")
            p.research(a, [("Apple releases iOS fix", "https://example.com/a", "The Verge")])
            posts = [{"title": "Old iOS post", "url": "https://techkrak.com/old-post/", "excerpt": "ios"},
                     {"title": "Other", "url": "https://techkrak.com/other/", "excerpt": ""}]
            p.write(a, posts, [{"id": 17, "name": "Tech News"}])
            self.assertEqual(a.slug, "ios-26-1-what-changed")
            self.assertLessEqual(len(a.meta_description), 156)
            self.assertNotIn("invented.com", a.body_html)
            self.assertEqual(a.tags, ["iOS", "Apple"])
            self.assertTrue(any("Removed 1 link" in w for w in a.warnings))
            a.experience_notes = "iphone 13 pro use kerta hun"
            p.polish_experience(a)
            self.assertIn("iPhone 13 Pro", a.experience_html)
            wp = FakeWP()
            res = p.publish_draft(a, wp)
            post = wp.created
            self.assertEqual(res["id"], 999)
            self.assertEqual(post["status"], "draft")
            self.assertEqual(post["categories"], [17])
            self.assertEqual(post["featured_media"], 501)
            self.assertIn("<figcaption>AI-generated image</figcaption>", post["content"])
            self.assertIn("How I use it myself", post["content"])
            self.assertIn("<h2>Sources</h2>", post["content"])
            self.assertEqual(post["meta"]["_yoast_wpseo_focuskw"], "iOS 26.1 update")
            self.assertEqual(len(wp.uploads), 2)


class SystemCapture(FakeGemini):
    systems = []

    def generate_json(self, prompt, system="", temperature=0.7):
        SystemCapture.systems.append(system)
        return super().generate_json(prompt, system, temperature)


class GenericNicheTests(unittest.TestCase):
    def test_finance_no_images_no_faq(self):
        cfg = dict(config.DEFAULTS, gemini_api_key="k", text_model="m", image_model="im", niches=["finance"],
                   image_source="none", faq=False, language="Urdu", target_words=900, site_name="Paisa Blog")
        SystemCapture.systems = []
        with mock.patch.object(writer, "Gemini", SystemCapture), mock.patch.object(writer, "resolve_url", lambda u: u):
            p = Pipeline(cfg, log=lambda m: None)
            a = Article(topic="iOS 26.1 update")
            p.research(a)
            posts = [{"title": "Old iOS post", "url": "https://techkrak.com/old-post/", "excerpt": "ios"}]
            p.write(a, posts, [])
            sysmsg = SystemCapture.systems[0]
            self.assertIn("Money & Finance", sysmsg)
            self.assertIn("Write the whole article in Urdu", sysmsg)
            self.assertIn("Do not add an FAQ", sysmsg)
            self.assertIn("qualified professional", sysmsg)
            self.assertIn("about 900 words", sysmsg)
            self.assertEqual(a.inline_images, [])
            wp = FakeWP()
            p.publish_draft(a, wp)
            self.assertEqual(wp.uploads, [])
            self.assertIn("not professional medical, financial or legal advice", wp.created["content"])
            self.assertEqual(wp.created["meta"]["rank_math_focus_keyword"], "iOS 26.1 update")


class GeminiImageParse(unittest.TestCase):
    def test_image_response(self):
        g = gemini.Gemini("k", image_model="gemini-3.1-flash-image")
        resp = {"candidates": [{"content": {"parts": [{"text": "here"},
                {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(b"img").decode()}}]}}]}
        with mock.patch.object(g, "_post", return_value=resp):
            data, mime = g.generate_image("x")
        self.assertEqual((data, mime), (b"img", "image/png"))

    def test_research_sources(self):
        g = gemini.Gemini("k", text_model="gemini-3-flash")
        resp = {"candidates": [{"content": {"parts": [{"text": "notes"}]},
                "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://r/1", "title": "t1"}}]}}]}
        with mock.patch.object(g, "_post", return_value=resp) as m:
            text, src = g.research("q")
        self.assertEqual(text, "notes")
        self.assertEqual(src, [("t1", "https://r/1")])
        self.assertIn({"google_search": {}}, m.call_args[0][1]["tools"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


NEWS_RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>iOS 27 users report HDMI output issues - GSMArena.com</title><link>https://news.google.com/a1</link>
<pubDate>Sat, 07 Nov 2026 05:00:02 GMT</pubDate>
<description>&lt;ol&gt;&lt;li&gt;&lt;a href="https://news.google.com/a1" target="_blank"&gt;iOS 27 users report HDMI output issues&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;GSMArena.com&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/a2" target="_blank"&gt;iPhone users report HDMI issues after iOS 27&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Analytics Insight&lt;/font&gt;&lt;/li&gt;&lt;/ol&gt;</description>
<source url="https://www.gsmarena.com">GSMArena.com</source></item>
<item><title>Apple CEO presses software chief on AI strategy - Bloomberg.com</title><link>https://news.google.com/b1</link>
<pubDate>Sun, 08 Nov 2026 15:00:01 GMT</pubDate>
<description>&lt;ol&gt;&lt;li&gt;&lt;a href="https://news.google.com/b1"&gt;Apple CEO presses software chief&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Bloomberg.com&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/b2"&gt;Ternus urges Federighi&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;iClarified&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/b3"&gt;Apple AI plans&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;9to5Mac&lt;/font&gt;&lt;/li&gt;&lt;/ol&gt;</description></item>
<item><title>Casino giant opens betting app - Reuters</title><link>https://news.google.com/c1</link><pubDate>Sun, 08 Nov 2026 15:00:01 GMT</pubDate><description>x</description></item>
</channel></rss>"""


class NewsTests(unittest.TestCase):
    def test_parse_and_rank(self):
        from core import news
        items = news.parse_news_rss(NEWS_RSS, "tech")
        self.assertEqual(items[0].title, "iOS 27 users report HDMI output issues")
        self.assertEqual(items[0].news[1], ("iPhone users report HDMI issues after iOS 27", "https://news.google.com/a2", "Analytics Insight"))
        self.assertEqual(items[1].traffic, "3 outlets")
        self.assertTrue(all(t.fits(["tech"]) for t in items[:2]))
        with mock.patch.object(news.requests, "get") as g:
            g.return_value = mock.Mock(ok=True, text=NEWS_RSS, raise_for_status=lambda: None)
            hot = news.fetch_hot(["tech"], "PK")
        self.assertEqual([t.title for t in hot], ["Apple CEO presses software chief on AI strategy",
                                                  "iOS 27 users report HDMI output issues"])
        self.assertEqual(g.call_args[1]["params"]["ceid"], "PK:en")
        self.assertIn("category=18", news.trends_page_url("pk", ["tech"]))

    def test_trends_sorted_by_volume(self):
        rss = RSS.replace("200K+", "200+").replace("1M+", "1000+")
        items = trends.parse_trends_rss(rss)
        items.sort(key=lambda t: t.traffic_num, reverse=True)
        self.assertEqual(items[0].title, "chiefs vs bills")
        self.assertEqual(trends.Trend("x", "2M+").traffic_num, 2000000)

    def test_ai_classify_accepts_labels(self):
        from core import topics

        class G:
            def generate_json(self, *a, **k):
                return {"items": [{"i": 0, "niches": ["Sports"]}, {"i": 1, "niches": ["Technology", "AI & Tools"]}]}
        items = [trends.Trend("inter vs como"), trends.Trend("chatgpt down")]
        topics.ai_classify(G(), items)
        self.assertEqual(items[0].ai_niches, ["sports"])
        self.assertEqual(items[1].ai_niches, ["tech", "ai"])

        class Bad:
            def generate_json(self, *a, **k):
                return ["nonsense"]
        items = [trends.Trend("inter vs como")]
        topics.ai_classify(Bad(), items)
        self.assertIsNone(items[0].ai_niches)
        self.assertTrue(items[0].fits(["sports"]))
