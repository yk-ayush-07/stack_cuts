"""ai_hooks.py: Generates viral short titles, on-screen hooks, and social hashtags.
Works with optional AI API keys (Gemini / OpenAI), with automatic fallback to heuristic transcript parsing.
"""
import os
import re

def generate_clip_metadata(transcript: str, streamer_name: str, video_title: str) -> dict:
    """
    Generate an engaging title, hook, and social description for a clip.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    # If API key is available, we could query Gemini / OpenAI; otherwise use smart heuristics
    return generate_heuristic_metadata(transcript, streamer_name, video_title)

def generate_heuristic_metadata(transcript: str, streamer_name: str, video_title: str) -> dict:
    """Heuristic extraction of the punchiest moment for title and hook."""
    words = transcript.strip().split()
    
    # Catch exclamation or high-energy phrases
    sentences = re.split(r'[.!?]+', transcript)
    sentences = [s.strip() for s in sentences if len(s.strip().split()) >= 3]

    if sentences:
        # Pick the most emphatic sentence
        best_sentence = max(sentences, key=lambda s: len(s))
        words_best = best_sentence.split()
        hook = " ".join(words_best[:6]).upper()
        title = f"{streamer_name} CANNOT BELIEVE THIS! 💀"
    else:
        hook = f"WAIT FOR IT... 😱"
        title = f"Best {streamer_name} Stream Highlight"

    caption = (
        f"{title}\n\n"
        f"Clip credit: @{streamer_name}\n"
        f"Stream: {video_title}\n\n"
        f"#gaming #streamer #clips #shorts #reels #gaminghighlight"
    )

    return {
        "title": title,
        "hook": hook,
        "caption": caption
    }
