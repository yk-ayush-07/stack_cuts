"""chat_monitor.py: Streaming chat parser, sliding-window aggregator, and hype-keyword sentiment scorer.
"""
import json
import re

HYPE_KEYWORDS = {
    "w", "lmao", "lol", "omg", "clip", "clip that", "hype", "no way", "wtf",
    "dead", "sheesh", "op", "gg", "clutch", "headshot", "insane", "bruh", "crazy",
    "pog", "poggers", "kekw", "bhai", "omggg", "ww", "www", "lmfao", "gotti"
}

HYPE_EMOJIS = {"💀", "🔥", "😭", "😂", "🤣", "😱", "🤯", "💥", "🐐", "👑", "⚡"}

def parse_chat_line(line: str):
    """Parse one yt-dlp live_chat JSON line -> list of (timestamp_sec, text, sentiment_score)."""
    try:
        d = json.loads(line)
    except (ValueError, TypeError):
        return []

    rep = d.get("replayChatItemAction", {})
    offset = rep.get("videoOffsetTimeMsec")
    out = []

    actions = rep.get("actions", []) or d.get("actions", [])
    for act in actions:
        item = act.get("addChatItemAction", {}).get("item", {})
        for r in item.values():
            if not isinstance(r, dict) or "timestampUsec" not in r:
                continue
            text = "".join(
                x.get("text", "") or x.get("emoji", {}).get("emojiId", "")[:2]
                for x in r.get("message", {}).get("runs", [])
            ).strip()
            
            if not text:
                continue

            live = d.get("isLive") or offset is None
            sec = int(r["timestampUsec"]) / 1e6 if live else int(offset) / 1000
            
            # Compute hype weight for this message
            weight = score_hype_text(text)
            out.append((sec, text, weight))

    return out

def score_hype_text(text: str) -> float:
    """Calculate hype weight for a single chat message (1.0 = normal, 2.0+ = high excitement)."""
    lower = text.lower().strip()
    score = 1.0

    # Keyword match
    for kw in HYPE_KEYWORDS:
        if kw in lower:
            score += 1.5
            break

    # Emoji match
    for emo in HYPE_EMOJIS:
        if emo in text:
            score += 1.0
            break

    # Shouting / All-caps
    if len(text) > 3 and text.isupper():
        score += 0.8

    # Repeated exclamation marks or question marks
    if "!" in text or "?" in text:
        score += 0.5

    return score

def bucket(events, window_sec=10):
    """Group events into discrete time windows: {bucket_index: [(text, hype_weight)]}."""
    buckets = {}
    for item in events:
        sec, text = item[0], item[1]
        weight = item[2] if len(item) > 2 else 1.0
        b_idx = int(sec // window_sec)
        buckets.setdefault(b_idx, []).append((text, weight))
    return buckets
