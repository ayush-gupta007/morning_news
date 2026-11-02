import os, re, time, calendar, datetime, requests, feedparser
from urllib.parse import quote
from google import genai

def gnews(q):
    """Google News RSS search. Reliable fallback and good for niche topics."""
    return ("https://news.google.com/rss/search?q=" + quote(q + " when:1d")
            + "&hl=en-IN&gl=IN&ceid=IN:en")

FEEDS = {
    "India Politics": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://indianexpress.com/section/political-pulse/feed/",
        "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "https://feeds.feedburner.com/ndtvnews-india-news",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://theprint.in/feed/",
        "https://www.livemint.com/rss/politics",
    ],
    "United States": [
        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://www.theguardian.com/us-news/us-politics/rss",
        "https://feeds.npr.org/1014/rss.xml",
        "https://rss.politico.com/politics-news.xml",
        "https://thehill.com/feed/",
    ],
    "Europe": [
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "https://www.theguardian.com/world/europe-news/rss",
        "https://rss.dw.com/xml/rss-en-eu",
        "https://www.euronews.com/rss?format=mrss&level=theme&name=news",
        "https://www.politico.eu/feed/",
        "https://www.france24.com/en/europe/rss",
    ],
    "Russia": [
        "https://www.themoscowtimes.com/rss/news",
        "https://meduza.io/rss/en/all",
        "https://tass.com/rss/v2.xml",  # state media
        "https://www.theguardian.com/world/russia/rss",
        gnews("Russia Kremlin Putin"),
    ],
    "China": [
        "https://www.chinadaily.com.cn/rss/china_rss.xml",  # state media
        "https://thediplomat.com/feed/",
        "https://www.theguardian.com/world/china/rss",
        gnews("site:scmp.com China"),
        gnews("China Beijing Xi Jinping policy"),
    ],
    "Pakistan": [
        "https://www.dawn.com/feeds/home",
        "https://tribune.com.pk/feed/home",
        "https://www.geo.tv/rss/1/1",
        "https://www.thenews.com.pk/rss/1/1",
        gnews("Pakistan government Islamabad"),
    ],
    "Major World Updates": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.theguardian.com/world/rss",
        "https://rss.dw.com/xml/rss-en-world",
        "https://feeds.npr.org/1004/rss.xml",
        "https://www.thehindu.com/news/international/feeder/default.rss",
    ],
    "Finance": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.livemint.com/rss/markets",
        "https://www.business-standard.com/rss/markets-106.rss",
        "https://www.thehindubusinessline.com/markets/feeder/default.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    ],
    "AI & Tech": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://www.technologyreview.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://openai.com/news/rss.xml",
        "https://blog.google/technology/ai/rss/",
    ],
    "Billionaires": [
        gnews("Elon Musk OR Jeff Bezos OR Mark Zuckerberg OR Bill Gates OR Larry Ellison OR Jensen Huang"),
        gnews("Warren Buffett OR Bernard Arnault OR Carlos Slim OR Michael Dell OR Ken Griffin OR Larry Page OR Sergey Brin"),
        gnews("Mukesh Ambani OR Gautam Adani OR Shiv Nadar OR Azim Premji OR Sunil Mittal OR Kumar Mangalam Birla"),
        gnews("billionaire net worth Forbes OR Bloomberg Billionaires Index"),
        gnews("billionaire investment OR acquisition OR stake OR deal"),
        gnews("billionaire philanthropy OR donation OR pledge"),
        gnews("site:forbes.com billionaire"),
    ],
}

LIMITS = {"Billionaires": 8}   # stories kept per source (default is 6)
UA = {"User-Agent": "Mozilla/5.0 (compatible; MorningNewsBot/1.0)"}

# ---- time window: morning run covers the night, others cover ~7 hours ----
now = datetime.datetime.now(datetime.timezone.utc)
ist = now + datetime.timedelta(hours=5, minutes=30)
HOURS = 14 if now.hour < 4 else 8
cutoff = time.time() - HOURS * 3600
label = "Morning" if ist.hour < 11 else "Afternoon" if ist.hour < 16 else "Evening"

def fetch(url, limit):
    try:
        r = requests.get(url, headers=UA, timeout=20)
        feed = feedparser.parse(r.content)
    except Exception as e:
        print(f"FAILED {url[:80]}: {e}")
        return []
    is_gn = "news.google.com" in url
    src = "" if is_gn else (feed.feed.get("title") or "")[:30]
    out = []
    for e in feed.entries:
        t = e.get("published_parsed") or e.get("updated_parsed")
        if t and calendar.timegm(t) < cutoff:
            continue
        summary = "" if is_gn else re.sub(r"<[^>]+>", "", e.get("summary") or "").strip()[:150]
        out.append((e.title.strip(), summary, e.link, src))
        if len(out) >= limit:
            break
    print(f"{len(feed.entries):>3} entries, {len(out):>2} kept <- {url[:80]}")
    return out

seen_links, seen_titles, links, sections = set(), set(), [], []
for topic, urls in FEEDS.items():
    lines = []
    for url in urls:
        for title, summary, link, src in fetch(url, LIMITS.get(topic, 6)):
            key = title.lower()
            if link in seen_links or key in seen_titles:
                continue
            seen_links.add(link)
            seen_titles.add(key)
            links.append(link)
            tag = f" ({src})" if src else ""
            lines.append(f"[{len(links)}] {title}{tag}" + (f" - {summary}" if summary else ""))
    if lines:
        sections.append(f"## {topic.upper()}\n" + "\n".join(lines))

if not sections:
    raise SystemExit("No stories fetched. Check the feed logs above.")

prompt = (
    f"You are my personal news editor. Write my {label} news brief using ONLY the "
    "numbered stories below.\n"
    "Rules:\n"
    "- Begin with 'TOP OF THE DAY': the 4 most important developments, one line each.\n"
    "- Then one section per topic, in the order given, using the topic name in CAPS "
    "as the heading. Skip a topic if it has no stories. No markdown symbols.\n"
    "- Pick the 5-6 most important stories per topic and merge duplicates. For "
    "BILLIONAIRES give 8-10 stories, each with concrete details: who, what, amounts, "
    "stakes, companies, and dates where the text gives them. Say 'unconfirmed' when "
    "a story is a rumour or speculation.\n"
    "- When a story comes from state-run media (TASS, China Daily), add '(state media)'.\n"
    "- Each story: one or two short lines, ending with its story number in square "
    "brackets like [12]. Use only numbers from the list. Never write URLs.\n"
    "- Do not invent facts.\n\n" + "\n\n".join(sections)
)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]

def generate(prompt, tries_per_model=3):
    for model in MODELS:
        for attempt in range(tries_per_model):
            try:
                return client.models.generate_content(model=model, contents=prompt).text
            except Exception as e:
                print(f"{model} attempt {attempt + 1} failed: {e}")
                time.sleep(10 * (attempt + 1))
    raise RuntimeError("All Gemini models failed")

text = generate(prompt)

def attach_link(m):
    n = int(m.group(1))
    return f"\n🔗 {links[n - 1]}" if 1 <= n <= len(links) else ""

text = re.sub(r"\s*\[(\d+)\]", attach_link, text)
text = f"📰 {label} brief · {ist:%d %b %Y, %I:%M %p} IST\n\n" + text

def chunks(text, limit=3800):
    buf = ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > limit:
            yield buf
            buf = ""
        buf += line + "\n"
    if buf.strip():
        yield buf

token, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
for part in chunks(text):
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": part, "disable_web_page_preview": True},
    )
    time.sleep(1)
