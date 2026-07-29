import os
import re
import json
import requests
import feedparser
from deep_translator import GoogleTranslator

RSS_URL = "https://www.ennaharonline.com/feed/"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

MAX_ARTICLES_PER_RUN = 5
MAX_TITLE_LENGTH = 256
MAX_SUMMARY_LENGTH = 500
SEEN_FILE = "seen_articles.json"

NETWORK_NAME = "Ennahar News"      # <-- edit this to whatever you want shown
SERVER_INVITE = ""                 # <-- optional: paste your server's invite link here, e.g. "discord.gg/yourcode"
DISCLAIMER = f"This content is for informational purposes only; {NETWORK_NAME} does not endorse any views expressed."

DEFAULT_FLAG = "🇩🇿"  # shown when no other country is mentioned by name (Ennahar is Algerian)
MAX_FLAGS = 3

# Add more entries here any time — key is matched as a whole word, case-insensitive
COUNTRY_FLAGS = {
    "algeria": "🇩🇿",
    "morocco": "🇲🇦",
    "tunisia": "🇹🇳",
    "libya": "🇱🇾",
    "egypt": "🇪🇬",
    "mauritania": "🇲🇷",
    "mali": "🇲🇱",
    "niger": "🇳🇪",
    "sudan": "🇸🇩",
    "saudi arabia": "🇸🇦",
    "palestine": "🇵🇸",
    "gaza": "🇵🇸",
    "zionism": "🇮🇱",
    "lebanon": "🇱🇧",
    "syria": "🇸🇾",
    "iraq": "🇮🇶",
    "iran": "🇮🇷",
    "jordan": "🇯🇴",
    "yemen": "🇾🇪",
    "qatar": "🇶🇦",
    "uae": "🇦🇪",
    "united arab emirates": "🇦🇪",
    "kuwait": "🇰🇼",
    "bahrain": "🇧🇭",
    "oman": "🇴🇲",
    "turkey": "🇹🇷",
    "france": "🇫🇷",
    "united states": "🇺🇸",
    "usa": "🇺🇸",
    "russia": "🇷🇺",
    "ukraine": "🇺🇦",
    "china": "🇨🇳",
    "spain": "🇪🇸",
    "italy": "🇮🇹",
    "germany": "🇩🇪",
    "united kingdom": "🇬🇧",
    "britain": "🇬🇧",
}


def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set) -> None:
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False)


def translate_to_english(text: str) -> str:
    if not text:
        return ""
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        print(f"[translate] failed, using original text: {e}")
        return text


def clean_html(raw_html: str) -> str:
    return re.sub("<[^<]+?>", "", raw_html or "").strip()


def detect_flags(text: str) -> str:
    text_lower = text.lower()
    matched = []
    for keyword, flag in COUNTRY_FLAGS.items():
        if flag in matched:
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
            matched.append(flag)
        if len(matched) >= MAX_FLAGS:
            break
    return " ".join(matched) if matched else DEFAULT_FLAG


def build_embed(entry) -> dict:
    title_en = translate_to_english(entry.get("title", "")) or "Ennahar News"
    summary_en = translate_to_english(clean_html(entry.get("summary", "")))

    flags = detect_flags(f"{title_en} {summary_en}")
    title = f"{flags} | {title_en}"[:MAX_TITLE_LENGTH]

    return {
        "title": title,
        "description": summary_en[:MAX_SUMMARY_LENGTH],
        "url": entry.get("link"),
        "color": 0xC8102E,
        "fields": [
            {
                "name": f"🔶 {NETWORK_NAME} 🔶",
                "value": SERVER_INVITE if SERVER_INVITE else "\u200b",
                "inline": False,
            }
        ],
        "footer": {"text": DISCLAIMER},
    }


def main():
    feed = feedparser.parse(RSS_URL)
    if feed.bozo:
        print(f"[rss] feed parsed with warnings: {feed.bozo_exception}")

    seen = load_seen()
    entries = [e for e in feed.entries if e.get("link")][:MAX_ARTICLES_PER_RUN]
    new_entries = [e for e in entries if e.link not in seen]

    if not new_entries:
        print("No new articles this check.")
        return

    embeds = [build_embed(entry) for entry in reversed(new_entries)]  # oldest first

    response = requests.post(WEBHOOK_URL, json={"embeds": embeds}, timeout=30)
    response.raise_for_status()

    for entry in new_entries:
        seen.add(entry.link)
    save_seen(seen)

    print(f"Posted {len(embeds)} new article(s).")


if __name__ == "__main__":
    main()
