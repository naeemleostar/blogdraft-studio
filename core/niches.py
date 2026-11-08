"""Blog niches: keyword signals used to filter Google trends and search ideas to the user's niche.

Matching is whole-word on lower-cased text. A trend belongs to a niche when its title, or at least
two of its news headlines, contain one of the niche's words. The optional AI filter (Gemini) is
more accurate; these lists are the fast, free first pass.
"""
import re

NICHES = {
    "tech": {
        "label": "Technology", "icon": "cpu",
        "hint": "smartphones, apps, gadgets, software, internet and everyday tech",
        "words": ["google", "apple", "iphone", "ipad", "macbook", "macos", "android", "samsung", "galaxy", "pixel",
                  "microsoft", "windows", "meta", "facebook", "instagram", "whatsapp", "tiktok", "youtube", "twitter",
                  "x app", "tesla", "spacex", "starlink", "nvidia", "amd", "intel", "qualcomm", "chip", "chips",
                  "semiconductor", "ios", "software", "app", "apps", "update", "laptop", "smartphone", "phone",
                  "smartwatch", "airpods", "wearable", "netflix", "spotify", "alexa", "smart home", "5g", "wi-fi",
                  "wifi", "browser", "chrome", "vpn", "gadget", "gadgets", "tech", "technology", "outage",
                  "app store", "play store", "firmware", "processor", "gpu", "router", "bluetooth", "smart tv",
                  "internet", "satellite", "cyber", "cybersecurity", "hack", "hacked", "malware", "ransomware",
                  "phishing", "data breach", "password", "robot", "robotics", "drone", "quantum"],
    },
    "ai": {
        "label": "AI & Tools", "icon": "sparkles",
        "hint": "AI tools, chatbots, AI news and how to use AI for work and study",
        "words": ["ai", "a.i.", "artificial intelligence", "chatgpt", "openai", "gemini", "claude", "copilot",
                  "llm", "chatbot", "midjourney", "deepseek", "grok", "perplexity", "machine learning",
                  "ai model", "ai tool", "ai tools", "generative", "sora", "agentic", "automation", "prompt"],
    },
    "gaming": {
        "label": "Gaming", "icon": "gamepad",
        "hint": "video games, consoles, PC gaming, game updates and guides",
        "words": ["xbox", "playstation", "ps5", "ps6", "nintendo", "switch 2", "steam", "fortnite", "minecraft",
                  "roblox", "gta", "call of duty", "valorant", "pokemon", "esports", "video game", "video games",
                  "gaming", "gamer", "console", "dlc", "patch notes", "battle pass", "twitch", "epic games"],
    },
    "sports": {
        "label": "Sports", "icon": "trophy",
        "hint": "match previews, results, players and sports news",
        "words": ["vs", "vs.", "nba", "nfl", "mlb", "nhl", "wnba", "ncaa", "mls", "ufc", "wwe", "pga", "nascar",
                  "formula 1", "f1", "super bowl", "world series", "world cup", "playoff", "playoffs",
                  "season opener", "injury report", "lineup", "lineups", "game preview", "touchdown",
                  "quarterback", "football", "basketball", "baseball", "soccer", "hockey", "tennis", "golf",
                  "boxing", "cricket", "premier league", "champions league", "olympics", "match", "score",
                  "standings", "coach", "stadium", "transfer", "grand prix"],
    },
    "health": {
        "label": "Health & Fitness", "icon": "heart",
        "hint": "fitness, nutrition, wellbeing and general health information",
        "words": ["health", "healthy", "fitness", "workout", "exercise", "diet", "nutrition", "protein", "vitamin",
                  "weight loss", "sleep", "yoga", "gym", "calories", "cholesterol", "blood pressure", "diabetes",
                  "heart", "mental health", "anxiety", "stress", "flu", "covid", "vaccine", "virus", "outbreak",
                  "cdc", "fda", "doctor", "hospital", "symptoms", "disease", "cancer", "recall", "supplement"],
        "ymyl": True,
    },
    "finance": {
        "label": "Money & Finance", "icon": "wallet",
        "hint": "personal finance, saving, banking, taxes, stocks and the economy",
        "words": ["stock", "stocks", "stock market", "dow", "s&p 500", "nasdaq", "earnings", "ipo", "interest rate",
                  "interest rates", "fed", "federal reserve", "inflation", "recession", "mortgage", "loan", "loans",
                  "credit card", "credit score", "bank", "banking", "tax", "taxes", "irs", "refund", "social security",
                  "401k", "ira", "retirement", "savings", "budget", "salary", "paycheck", "stimulus", "economy",
                  "gas prices", "price", "prices", "tariff", "tariffs", "insurance", "investing", "dividend"],
        "ymyl": True,
    },
    "crypto": {
        "label": "Crypto", "icon": "coins",
        "hint": "bitcoin, ethereum, exchanges, wallets and crypto news",
        "words": ["crypto", "cryptocurrency", "bitcoin", "btc", "ethereum", "eth", "solana", "xrp", "dogecoin",
                  "binance", "coinbase", "blockchain", "stablecoin", "nft", "altcoin", "memecoin", "web3", "defi",
                  "crypto etf", "halving"],
        "ymyl": True,
    },
    "business": {
        "label": "Business & Marketing", "icon": "briefcase",
        "hint": "startups, small business, marketing, jobs and companies",
        "words": ["business", "startup", "startups", "company", "ceo", "layoffs", "layoff", "hiring", "jobs",
                  "job", "remote work", "marketing", "seo", "ecommerce", "e-commerce", "amazon", "shopify",
                  "small business", "entrepreneur", "freelance", "freelancing", "side hustle", "brand", "merger",
                  "acquisition", "lawsuit", "black friday", "cyber monday", "sale", "deals"],
    },
    "education": {
        "label": "Education & Careers", "icon": "book",
        "hint": "students, exams, scholarships, online courses and careers",
        "words": ["student", "students", "school", "schools", "college", "university", "exam", "exams", "sat",
                  "scholarship", "scholarships", "student loan", "student loans", "fafsa", "course", "courses",
                  "online course", "degree", "admission", "admissions", "teacher", "study", "career", "resume",
                  "interview", "internship", "certification"],
    },
    "travel": {
        "label": "Travel", "icon": "plane",
        "hint": "destinations, flights, visas, hotels and travel tips",
        "words": ["travel", "flight", "flights", "airline", "airlines", "airport", "tsa", "faa", "passport",
                  "visa", "hotel", "hotels", "vacation", "cruise", "trip", "tourism", "tourist", "destination",
                  "national park", "road trip", "booking", "airbnb", "delta", "united airlines", "american airlines"],
    },
    "food": {
        "label": "Food & Recipes", "icon": "utensils",
        "hint": "recipes, cooking, restaurants and food news",
        "words": ["recipe", "recipes", "cooking", "cook", "bake", "baking", "food", "foods", "restaurant",
                  "restaurants", "menu", "mcdonald's", "starbucks", "chipotle", "taco bell", "chick-fil-a",
                  "pizza", "burger", "coffee", "dessert", "thanksgiving dinner", "turkey", "snack", "drink",
                  "food recall", "grocery", "costco", "trader joe's"],
    },
    "entertainment": {
        "label": "Movies, TV & Music", "icon": "film",
        "hint": "movies, shows, streaming releases, music and celebrities",
        "words": ["movie", "movies", "film", "trailer", "box office", "season", "episode", "series", "netflix",
                  "hulu", "disney+", "disney plus", "hbo", "max", "prime video", "apple tv", "album", "song",
                  "tour", "concert", "grammy", "grammys", "oscars", "emmys", "singer", "rapper", "actor",
                  "actress", "celebrity", "taylor swift", "marvel", "anime", "premiere", "cast", "reality show"],
    },
    "lifestyle": {
        "label": "Fashion & Beauty", "icon": "shirt",
        "hint": "fashion, beauty, skincare and style",
        "words": ["fashion", "style", "outfit", "outfits", "dress", "beauty", "makeup", "skincare", "skin care",
                  "hair", "hairstyle", "sneakers", "nike", "adidas", "zara", "shein", "sephora", "ulta",
                  "perfume", "fragrance", "nails", "met gala"],
    },
    "home": {
        "label": "Home & DIY", "icon": "home",
        "hint": "home improvement, gardening, cleaning and DIY",
        "words": ["home", "house", "diy", "garden", "gardening", "plants", "cleaning", "kitchen", "furniture",
                  "ikea", "home depot", "lowe's", "decor", "renovation", "repair", "appliance", "appliances",
                  "air fryer", "vacuum", "mattress", "paint", "lawn", "heating", "air conditioner"],
    },
    "auto": {
        "label": "Cars & EVs", "icon": "car",
        "hint": "cars, electric vehicles, reviews and auto news",
        "words": ["car", "cars", "ev", "electric vehicle", "electric car", "tesla", "ford", "toyota", "honda",
                  "chevrolet", "gm", "bmw", "mercedes", "hyundai", "kia", "rivian", "lucid", "byd", "suv", "truck",
                  "pickup", "recall", "charging", "gas mileage", "mpg", "auto show", "car insurance", "dealership"],
    },
    "parenting": {
        "label": "Family & Parenting", "icon": "baby",
        "hint": "parenting, kids, babies and family life",
        "words": ["parenting", "parent", "parents", "baby", "babies", "toddler", "kids", "children", "child",
                  "pregnancy", "family", "mom", "dad", "teen", "teens", "daycare", "child care", "toy", "toys"],
    },
    "pets": {
        "label": "Pets", "icon": "paw",
        "hint": "dogs, cats, pet care and pet products",
        "words": ["dog", "dogs", "cat", "cats", "puppy", "kitten", "pet", "pets", "vet", "veterinarian",
                  "pet food", "dog food", "cat food", "breed", "adoption", "shelter"],
    },
    "science": {
        "label": "Science & Space", "icon": "atom",
        "hint": "space, astronomy, climate and science discoveries",
        "words": ["nasa", "space", "astronaut", "rocket", "launch", "moon", "mars", "planet", "asteroid", "comet",
                  "meteor", "eclipse", "aurora", "northern lights", "telescope", "galaxy", "black hole",
                  "scientists", "study finds", "discovery", "dinosaur", "fossil", "climate", "earthquake",
                  "volcano", "solar storm"],
    },
}

# Recommended article settings per niche (applied from Settings with one click).
PRESETS = {'tech': {'target_words': 1400, 'inline_images': 2, 'tone': 'friendly', 'faq': True, 'image_source': 'pexels_then_gemini'}, 'ai': {'target_words': 1500, 'inline_images': 2, 'tone': 'friendly', 'faq': True, 'image_source': 'gemini'}, 'gaming': {'target_words': 1100, 'inline_images': 2, 'tone': 'friendly', 'faq': True, 'image_source': 'gemini'}, 'sports': {'target_words': 900, 'inline_images': 1, 'tone': 'friendly', 'faq': False, 'image_source': 'pexels'}, 'health': {'target_words': 1600, 'inline_images': 2, 'tone': 'professional', 'faq': True, 'image_source': 'pexels'}, 'finance': {'target_words': 1600, 'inline_images': 1, 'tone': 'professional', 'faq': True, 'image_source': 'pexels_then_gemini'}, 'crypto': {'target_words': 1300, 'inline_images': 1, 'tone': 'professional', 'faq': True, 'image_source': 'gemini'}, 'business': {'target_words': 1400, 'inline_images': 1, 'tone': 'professional', 'faq': True, 'image_source': 'pexels'}, 'education': {'target_words': 1400, 'inline_images': 1, 'tone': 'simple', 'faq': True, 'image_source': 'pexels'}, 'travel': {'target_words': 1600, 'inline_images': 4, 'tone': 'friendly', 'faq': True, 'image_source': 'pexels'}, 'food': {'target_words': 1200, 'inline_images': 4, 'tone': 'friendly', 'faq': True, 'image_source': 'pexels'}, 'entertainment': {'target_words': 900, 'inline_images': 1, 'tone': 'friendly', 'faq': False, 'image_source': 'pexels'}, 'lifestyle': {'target_words': 1100, 'inline_images': 3, 'tone': 'friendly', 'faq': True, 'image_source': 'pexels'}, 'home': {'target_words': 1400, 'inline_images': 3, 'tone': 'simple', 'faq': True, 'image_source': 'pexels'}, 'auto': {'target_words': 1300, 'inline_images': 2, 'tone': 'friendly', 'faq': True, 'image_source': 'pexels'}, 'parenting': {'target_words': 1300, 'inline_images': 2, 'tone': 'friendly', 'faq': True, 'image_source': 'pexels'}, 'pets': {'target_words': 1200, 'inline_images': 3, 'tone': 'friendly', 'faq': True, 'image_source': 'pexels'}, 'science': {'target_words': 1300, 'inline_images': 2, 'tone': 'simple', 'faq': True, 'image_source': 'pexels_then_gemini'}}

# Topics that hurt AdSense approval whatever the niche: gambling, adult, violence, tragedy.
ALWAYS_BLOCK = [
    "odds", "betting", "bet", "bets", "sportsbook", "parlay", "casino", "lottery", "powerball", "mega millions",
    "jackpot", "porn", "onlyfans", "nude", "leaked video", "shooting", "shot dead", "killed", "murder",
    "stabbing", "massacre", "suicide", "obituary", "dies", "dead at", "funeral", "arrested", "mugshot",
    "free stream", "live stream free", "watch free", "crack", "torrent", "apk mod",
]

# Hidden unless the user selects a niche that matches them (e.g. Sports, Entertainment).
NEWS_ONLY = ["election", "senate", "governor", "congress", "president", "trump", "biden", "democrat", "republican",
             "weather", "hurricane", "storm", "tornado", "snow", "forecast"]


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9.&+'\- ]+", " ", (text or "").lower().replace("’", "'")) + " "


def _has(words, padded: str) -> bool:
    return any(f" {w} " in padded for w in words)


def matches(text: str, niche: str) -> bool:
    n = NICHES.get(niche)
    return bool(n) and _has(n["words"], _norm(text))


def niches_of(text: str) -> list:
    padded = _norm(text)
    return [k for k, n in NICHES.items() if _has(n["words"], padded)]


def is_blocked(text: str) -> bool:
    return _has(ALWAYS_BLOCK, _norm(text))


def is_politics_or_weather(text: str) -> bool:
    return _has(NEWS_ONLY, _norm(text))


def niche_text(selected: list, custom: str = "") -> str:
    """Human description of the blog's niche for the writing prompts."""
    parts = [f"{NICHES[k]['label']} ({NICHES[k]['hint']})" for k in selected if k in NICHES]
    if custom.strip():
        parts.append(custom.strip())
    return "; ".join(parts) or "general interest"


def is_ymyl(selected: list) -> bool:
    return any(NICHES.get(k, {}).get("ymyl") for k in selected)


def public_list() -> list:
    return [{"id": k, "label": v["label"], "icon": v["icon"], "hint": v["hint"], "ymyl": bool(v.get("ymyl")),
             "preset": PRESETS.get(k, {})} for k, v in NICHES.items()]
