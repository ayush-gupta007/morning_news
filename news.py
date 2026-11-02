import os, re, time, calendar, requests, feedparser
from google import genai

FEEDS = {
    "Geopolitics": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "Politics (India)": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
    ],
    "Finance": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "AI & Tech": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    ],
}

def fetch(urls, hours=26, per_feed=8):
    cutoff = time.time() - hours * 3600
    out = []
    for url in urls:
        count = 0
        for e in feedparser.parse(url).entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if t and calendar.timegm(t) < cutoff:
                continue
            summary = re.sub(r"<[^>]+>", "", e.get("summary") or "")[:200]
            out.append((e.title, summary, e.link))
            count += 1
            if count >= per_feed:
                break
    return out

links, sections = [], []
for topic, urls in FEEDS.items():
    lines = []
    for title, summary, link in fetch(urls):
        links.append(link)
        lines.append(f"[{len(links)}] {title} - {summary}")
    if lines:
        sections.append(f"## {topic}\n" + "\n".join(lines))

prompt = (
    "You are my morning news editor. Using ONLY the numbered stories below, "
    "write a concise daily brief in plain text.\n"
    "Rules:\n"
    "- Start with 'Top of the day' (3 short lines).\n"
    "- For each topic, show the 4-5 most important stories. Merge duplicates.\n"
    "- Use the topic name in CAPS as a heading. No markdown symbols.\n"
    "- Each story: one short line, ending with its story number in square "
    "brackets, like [12]. Use only numbers from the list. Never write URLs.\n"
    "- Do not invent facts.\n\n" + "\n\n".join(sections)
)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
text = client.models.generate_content(
    model="gemini-flash-latest", contents=prompt
).text

def attach_link(m):
    n = int(m.group(1))
    return f"\n🔗 {links[n - 1]}" if 1 <= n <= len(links) else ""

text = re.sub(r"\s*\[(\d+)\]", attach_link, text)

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
