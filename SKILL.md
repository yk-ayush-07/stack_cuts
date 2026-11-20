---
name: stack_cuts
description: Advanced stream-to-reels clipping studio. Turns YouTube Live streams or finished VODs into ready-to-post 9:16 vertical shorts (Reels, TikTok, Shorts). Features Stacked Gaming Layout (Facecam top 35% + Gameplay bottom 65%), multi-modal chat & audio spike detection, word-highlighted animated captions with Roman Hindi/Hinglish transliteration, and audio loudness normalization. Use when clipping gaming streams, cutting highlights, or generating vertical reels from YouTube links.
---

# Stack Cuts

Intelligent stream clipping and vertical reel studio. Converts 16:9 gaming and IRL streams into 1080x1920 viral shorts with stacked facecam framing and synchronized captions.

## Quick Start

```bash
# Live stream (cuts while stream is active)
python cli.py run "<youtube_live_url>" --layout stacked --max-clips 10

# Finished stream VOD (reads chat replay and downloads only highlight seconds)
python cli.py run "<youtube_vod_url>" --layout stacked --max-clips 25
```

## Layout Modes
- `--layout stacked`: Streamer facecam on top (35%), gameplay on bottom (65%). Built for gaming streamers (GTA, BGMI, Valorant).
  - `--facecam-pos`: `bottom-left` (default), `top-left`, `top-right`, `bottom-right`.
- `--layout fill`: 9:16 vertical crop with slow push-in zoom.
- `--layout fit`: 16:9 full frame centered over blurred background.

## Captions & Languages
- Faster-Whisper word-by-word timestamps with Hormozi-style yellow highlighting.
- Automatic Romanization: Hindi and Urdu spoken phrases are automatically rendered in readable Latin/Roman English letters ("BHAI KYA MARA").
- Hindi/Hinglish streams: add `--whisper-model large-v3-turbo` or use default `small`.
