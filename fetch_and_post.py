import os
import re
import json
import requests
import feedparser
from deep_translator import GoogleTranslator

RSS_URL = "https://www.ennaharonline.com/feed/"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
EMOJI_KEYWORDS_URL = "https://raw.githubusercontent.com/muan/emojilib/main/dist/emoji-en-US.json"
EMOJI_GROUPS_URL = "https://raw.githubusercontent.com/muan/unicode-emoji-json/main/data-by-emoji.json"

MAX_ARTICLES_PER_RUN = 5
MAX_TITLE_LENGTH = 256
MAX_SUMMARY_LENGTH = 500
SEEN_FILE = "seen_articles.json"

NETWORK_NAME = "Ennahar News"      # <-- edit this to whatever you want shown
SERVER_INVITE = ""                 # <-- optional: paste your server's invite link here
DISCLAIMER = f"This content is for informational purposes only; {NETWORK_NAME} does not endorse any views expressed."

DEFAULT_FLAG = "🇩🇿"
MAX_FLAGS = 3
MAX_TOPICS = 2

# Emoji categories to never use as topic emoji — faces, expressions, people, body parts, gestures
EXCLUDED_GROUPS = {"Smileys & Emotion", "People & Body"}

COUNTRY_FLAGS = {
    "algeria": "🇩🇿", "morocco": "🇲🇦", "tunisia": "🇹🇳", "libya": "🇱🇾", "egypt": "🇪🇬",
    "mauritania": "🇲🇷", "mali": "🇲🇱", "niger": "🇳🇪", "sudan": "🇸🇩",
    "saudi arabia": "🇸🇦", "palestine": "🇵🇸", "gaza": "🇵🇸", "israel": "🇮🇱",
    "lebanon": "🇱🇧", "syria": "🇸🇾", "iraq": "🇮🇶", "iran": "🇮🇷", "jordan": "🇯🇴",
    "yemen": "🇾🇪", "qatar": "🇶🇦", "uae": "🇦🇪", "united arab emirates": "🇦🇪",
    "kuwait": "🇰🇼", "bahrain": "🇧🇭", "oman": "🇴🇲", "turkey": "🇹🇷", "france": "🇫🇷",
    "united states": "🇺🇸", "usa": "🇺🇸", "russia": "🇷🇺", "ukraine": "🇺🇦", "china": "🇨🇳",
    "spain": "🇪🇸", "italy": "🇮🇹", "germany": "🇩🇪", "united kingdom": "🇬🇧", "britain": "🇬🇧",
}

_emoji_keyword_map = None


def load_emoji_keyword_map() -> dict:
    global _emoji_keyword_map
    if _emoji_keyword_map is not None:
        return _emoji_keyword_map

    reverse_map = {}
    try:
        keywords_resp = requests.get(EMOJI_KEYWORDS_URL, timeout=15)
        keywords_resp.raise_for_status()
        keywords_data = keywords_resp.json()

        groups_resp = requests.get(EMOJI_GROUPS_URL, timeout=15)
        groups_resp.raise_for_status()
        groups_data = groups_resp.json()

        for emoji_char, keywords in keywords_data.items():
            group_info = groups_data.get(emoji_char)
            if group_info and group_info.get("group") in EXCLUDED_GROUPS:
                continue  # skip faces, expressions, people, body parts, gestures

            for keyword in keywords:
                keyword = keyword.lower()
                if len(keyword) < 4:
                    continue
                if keyword not in reverse_map:
                    reverse_map[keyword] = emoji_char
    except Exception as e:
        print(f"[emoji-lookup] failed to load, skipping auto emojis this run: {e}")

    _emoji_keyword_map = reverse_map
    return reverse_map


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


def detect_topics(text: str) -> str:
    keyword_map = load_emoji_keyword_map()
    if not keyword_map:
        return ""

    words = re.findall(r"[a-zA-Z']+", text.lower())
    matched = []
    for word in words:
        emoji_char = keyword_map.get(word)
        if emoji_char and emoji_char not in matched:
            matched.append(emoji_char)
        if len(matched) >= MAX_TOPICS:
            break
    return " ".join(matched)


def extract_image_url(entry) -> str:
    media_content = entry.get("media_content")
    if media_content:
        for media in media_content:
            if media.get("url"):
                return media["url"]

    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail:
        for thumb in media_thumbnail:
            if thumb.get("url"):
                return thumb["url"]

    enclosures = entry.get("enclosures")
    if enclosures:
        for enc in enclosures:
            if str(enc.get("type", "")).startswith("image") and enc.get("href"):
                return enc["href"]

    raw_summary = entry.get("summary", "")
    match = re.search(r'<img[^>]+src="([^"]+)"', raw_summary)
    if match:
        return match.group(1)

    return ""


def build_embed(entry) -> dict:
    title_en = translate_to_english(entry.get("title", "")) or "Ennahar News"
    summary_en = translate_to_english(clean_html(entry.get("summary", "")))

    combined_text = f"{title_en} {summary_en}"
    flags = detect_flags(combined_text)
    topics = detect_topics(combined_text)
    prefix = " ".join(p for p in [flags, topics] if p)

    title = f"{prefix} | {title_en}"[:MAX_TITLE_LENGTH]

    embed = {
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

    image_url = extract_image_url(entry)
    if image_url:
        embed["image"] = {"url": image_url}

    return embed


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

    embeds = [build_embed(entry) for entry in reversed(new_entries)]

    response = requests.post(WEBHOOK_URL, json={"embeds": embeds}, timeout=30)
    response.raise_for_status()

    for entry in new_entries:
        seen.add(entry.link)
    save_seen(seen)

    print(f"Posted {len(embeds)} new article(s).")


if __name__ == "__main__":
    main()
