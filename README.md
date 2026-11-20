# 🎬 Stack Cuts

> **Intelligent Stream-to-Reels Highlight Clipper & Vertical Studio**  
> Turn long YouTube Live streams and finished VODs into viral 9:16 vertical shorts (Reels, TikTok, Shorts) automatically when the chat goes wild!

---

## ✨ Features

- 🎮 **Stacked Gaming Layout**: Automatically places the streamer's facecam on the top 35% and gameplay on the bottom 65% — the industry standard for viral gaming shorts.
- ⚡ **Multi-Modal Highlight Detection**: Filters out giveaway spam, AFK screens, and chat sampling anomalies by scoring message velocity alongside hype keywords ("W", "LMAO", "CLIP THAT", "💀", "🔥").
- 🗣️ **Word-by-Word Animated Captions**: Alex Hormozi & Neon glow subtitle styles with dynamic active word highlights and streamer credit badges.
- 🌐 **Automatic Romanization**: Transliterates spoken Hindi/Urdu Devanagari audio into clean Latin/Roman script (`"BHAI KYA MARA"`), maximizing retention on Indian & global feeds.
- 🎚️ **Loudness Normalization**: Mastered to `-14 LUFS` EBU R128 standard so reels never play quiet or distorted on mobile speakers.
- 🛡️ **Cross-Platform Resilience**: Clean process lifecycle management on Windows and Linux with zero orphan background processes or memory leaks.
- ⏱️ **VOD Selective Cutting**: Extracts only the best moments from finished streams without downloading multi-gigabyte 5-hour video files.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) (with libass enabled)

### 2. Install
```bash
git clone https://github.com/yk-ayush-07/stack_cuts.git
cd stack_cuts
pip install -r requirements.txt
```

Verify your setup:
```bash
python cli.py selftest
```

### 3. Run
#### On a Live Stream:
```bash
python cli.py run "https://www.youtube.com/live/<ID>" --layout stacked --max-clips 10
```

#### On a Finished Stream (VOD):
```bash
python cli.py run "https://www.youtube.com/watch?v=<ID>" --layout stacked --max-clips 25 --pre 25 --post 15
```

Clips land in `clips/<video_id>/` as `clip_01.mp4`, `clip_02.mp4` along with `clips.json` metadata!

---

## 🎛️ Layout Modes

| Layout | Flag | Description |
|---|---|---|
| **Stacked (Gaming)** | `--layout stacked` | Facecam on top (35%) + gameplay on bottom (65%). Configurable with `--facecam-pos [bottom-left \| top-left \| top-right \| bottom-right]`. |
| **Fill & Zoom** | `--layout fill` | 9:16 vertical crop with slow push-in zoom and configurable horizontal focus (`--focus 0.5`). |
| **Fit & Blur** | `--layout fit` | Preserves original 16:9 aspect ratio centered over a blurred, dimmed background canvas. |

---

## ⚙️ Options & Tuning

| Flag | Default | Description |
|---|---|---|
| `--max-clips` | `10` | Maximum number of clips to cut. |
| `--pre` | `22` | Seconds preserved before the chat spike. |
| `--post` | `12` | Seconds preserved after the chat spike. |
| `--cooldown` | `60` | Minimum spacing (seconds) between distinct clips. |
| `--factor` | `2.5` | Spike threshold (multiplier over baseline chat rate). |
| `--min-msgs` | `8` | Minimum messages in a window required to trigger a spike. |
| `--caption-style`| `hormozi` | Subtitle style: `hormozi` (yellow highlight) or `neon` (cyan glow). |
| `--whisper-model`| `small` | Faster-Whisper model (`small`, `base`, `large-v3-turbo`). |

---

## 🤖 AI Agent Skill

Stack Cuts is also a native AI agent skill compatible with **Antigravity**, **Claude Code**, and **Codex**. Simply ask your agent:
> *"Find the best moments and cut 10 vertical reels from `<YouTube link>` using stacked layout"*

---

## 📜 License
MIT License.
