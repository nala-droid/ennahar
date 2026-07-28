import os
import re
import requests
import feedparser
from deep_translator import GoogleTranslator

RSS_URL = "https://www.ennaharonline.com/feed/"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
MAX_ARTICLES = 5
MAX_TITLE_LENGTH = 256
MAX_SUMMARY_LENGTH = 500


def translate_to_english(text: str) -> str:
    if not text:
        return ""
    try:
        # source="auto" handles the feed mixing Arabic with occasional French/English
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        print(f"[translate] failed, using original text: {e}")
        return text


def clean_html(raw_html: str) -> str:
    return re.sub("<[^<]+?>", "", raw_html or "").strip()


def main():
    feed = feedparser.parse(RSS_URL)
    if feed.bozo:
        print(f"[rss] feed parsed with warnings: {feed.bozo_exception}")

    entries = feed.entries[:MAX_ARTICLES]
    if not entries:
        print("No articles found in the feed — nothing to post.")
        return

    embeds = []
    for entry in entries:
        title_en = translate_to_english(entry.get("title", ""))[:MAX_TITLE_LENGTH] or "Ennahar News"
        summary_en = translate_to_english(clean_html(entry.get("summary", "")))[:MAX_SUMMARY_LENGTH]

        embeds.append({
            "title": title_en,
            "description": summary_en,
            "url": entry.get("link"),
            "color": 0xC8102E,
            "footer": {"text": "Ennahar TV (An-Nahar), Algeria — auto-translated from Arabic"},
        })

    # Discord webhooks accept up to 10 embeds in a single message
    response = requests.post(WEBHOOK_URL, json={"embeds": embeds}, timeout=30)
    response.raise_for_status()
    print(f"Posted {len(embeds)} articles.")


if __name__ == "__main__":
    main()
