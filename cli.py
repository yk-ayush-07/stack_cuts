#!/usr/bin/env python3
"""cli.py: Stack Cuts - Intelligent Stream Highlight Clipper and Vertical Reel Studio.

Usage:
  python cli.py run <url> [options]       # Live stream or finished VOD replay
  python cli.py render <clip_dir>         # Re-render clips after editing captions
  python cli.py selftest                  # Run comprehensive automated unit tests
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure package root is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    stream_info, start_recorder, start_chat, cut_from_recording, cut_from_vod,
    kill_process_tree, duration, parse_chat_line, bucket, is_spike, top_spikes,
    transcribe_audio, romanize_text, render_vertical_reel, generate_clip_metadata
)

def read_new_lines(path: Path, pos: int):
    """Read newly appended lines from a growing file without reading from beginning."""
    if not path.exists():
        return [], pos
    with open(path, "rb") as f:
        f.seek(pos)
        data = f.read()
    cut = data.rfind(b"\n") + 1
    return data[:cut].decode("utf-8", "ignore").splitlines(), pos + cut

def process_and_save_clip(clip_num: int, raw_path: Path, meta: dict, args):
    """Transcribe, romanize, render, and log a finished clip."""
    words = []
    if not args.no_captions:
        print(f"  [Transcribing] Generating word timestamps for clip {clip_num:02d}...")
        words = transcribe_audio(raw_path, model_name=args.whisper_model)

    words_file = args.out / f"words_{clip_num:02d}.json"
    words_file.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_file = args.out / f"clip_{clip_num:02d}.mp4"
    print(f"  [Rendering] Creating 1080x1920 vertical reel ({args.layout} layout)...")
    render_vertical_reel(
        raw_path=raw_path,
        words=words,
        credit=args.credit,
        out_path=clip_file,
        layout=args.layout,
        focus=args.focus,
        facecam_pos=args.facecam_pos,
        caption_style=args.caption_style
    )

    transcript = " ".join(w["w"] for w in words)
    ai_meta = generate_clip_metadata(transcript, args.credit, meta.get("stream_title", ""))

    clip_entry = {
        **meta,
        "clip_number": clip_num,
        "file": clip_file.name,
        "raw_file": raw_path.name,
        "credit": args.credit,
        "transcript": transcript,
        **ai_meta
    }

    clips_json = args.out / "clips.json"
    existing = json.loads(clips_json.read_text(encoding="utf-8")) if clips_json.exists() else []
    clips_json.write_text(json.dumps(existing + [clip_entry], ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  ✓ Saved clip_{clip_num:02d}.mp4 in {args.out}")

def run_live(url: str, args):
    """Record live broadcast, monitor chat, and slice clips in real time."""
    rec_path = args.out / "rec.ts"
    chat_file = args.out / "chat.live_chat.json.part"

    print("  [Live Mode] Initializing stream recorder & live chat monitor...")
    recorder = start_recorder(url, rec_path, height=args.height, client=args.client)
    chat = start_chat(url, args.out)

    events = []
    pos = 0
    pending_clips = []
    last_clip_bucket = -10**9
    clips_made = 0
    rec_wall_start = None          # wall-clock time the recording began
    first_event_sec = None         # earliest stream-relative timestamp seen in chat
    stop_at = time.time() + (args.minutes * 60) if args.minutes > 0 else float("inf")

    print(f"  [Listening] Monitoring chat spikes. Output dir: {args.out}")
    try:
        while time.time() < stop_at and clips_made < args.max_clips and recorder.poll() is None:
            time.sleep(5)
            if rec_wall_start is None and rec_path.exists() and rec_path.stat().st_size > 0:
                rec_wall_start = time.time()

            new_lines, pos = read_new_lines(chat_file, pos)
            events.extend(e for ln in new_lines for e in parse_chat_line(ln))

            if not events or rec_wall_start is None:
                continue

            # Remember the first chat timestamp so we can convert stream-relative
            # bucket indices into wall-clock times.
            if first_event_sec is None:
                first_event_sec = min(e[0] for e in events)

            buckets = bucket(events, window_sec=args.window)
            if not buckets:
                continue

            last_complete_bucket = max(buckets.keys()) - 1
            spk_ok, baseline, score = is_spike(buckets, last_complete_bucket, factor=args.factor, min_msgs=args.min_msgs)

            spacing_needed = args.cooldown // args.window
            if spk_ok and (last_complete_bucket - last_clip_bucket >= spacing_needed):
                # Convert stream-relative bucket time to recording-relative seconds
                bucket_stream_sec = last_complete_bucket * args.window
                rec_elapsed = time.time() - rec_wall_start
                if rec_elapsed >= args.pre:
                    last_clip_bucket = last_complete_bucket
                    pending_clips.append({
                        "bucket": last_complete_bucket,
                        "wall_time": time.time(),
                        "score": round(score, 2),
                        "count": len(buckets[last_complete_bucket]),
                        "baseline": round(baseline, 1),
                        "chat_sample": [t for t, _ in buckets[last_complete_bucket][:6]]
                    })
                    print(f"  [Highlight Detected!] Bucket {last_complete_bucket} (Score: {score:.1f}, {len(buckets[last_complete_bucket])} msgs). Cutting in {args.post + 15}s...")

            # Ready to cut
            ready = [p for p in pending_clips if time.time() >= p["wall_time"] + args.post + 15]
            pending_clips = [p for p in pending_clips if p not in ready]

            for p in ready:
                dur_rec = duration(rec_path)
                # How many seconds ago (wall-clock) the spike happened
                secs_ago = time.time() - p["wall_time"]
                start_sec = max(0, dur_rec - secs_ago - args.pre + args.lag)
                raw_path = args.out / f"raw_{clips_made + 1:02d}.mp4"
                cut_from_recording(rec_path, start_sec, args.pre + args.post, raw_path)

                if duration(raw_path) < 3.0:
                    print("  [Notice] Segment skipped (insufficient duration in live buffer).")
                    continue

                clips_made += 1
                meta = {
                    **p,
                    "stream_title": getattr(args, "stream_title", ""),
                    "timestamp": time.strftime("%H:%M:%S", time.localtime(p["bucket"] * args.window))
                }
                process_and_save_clip(clips_made, raw_path, meta, args)

    except KeyboardInterrupt:
        print("\n  [Stopping] Execution interrupted by user.")
    finally:
        print("  [Cleanup] Terminating active streaming and recording processes...")
        kill_process_tree(recorder)
        kill_process_tree(chat)

    if not args.keep_recording and rec_path.exists():
        try:
            rec_path.unlink()
        except OSError:
            pass
    print(f"  [Done] {clips_made} clip(s) generated in {args.out}")

def run_replay(url: str, args):
    """Download chat replay from a finished VOD, calculate top spikes, and cut best moments."""
    print("  [VOD Replay Mode] Downloading chat replay...")
    from core.ingester import run as irun, YTDLP
    try:
        irun([YTDLP, "--no-update", "-q", "--skip-download", "--write-subs", "--sub-langs", "live_chat", "-o", str(args.out / "chat"), url])
    except subprocess.CalledProcessError:
        sys.exit("Error: Failed to download chat replay. The video may be private, deleted, or have no live chat.")
    
    chat_file = args.out / "chat.live_chat.json"
    if not chat_file.exists():
        sys.exit("Error: No chat replay found for this video. Cannot perform spike detection.")

    print("  [Analyzing] Parsing chat replay messages and detecting moments...")
    events = [e for ln in chat_file.read_text(encoding="utf-8", errors="ignore").splitlines() for e in parse_chat_line(ln)]
    buckets = bucket([e for e in events if e[0] >= 0], window_sec=args.window)

    spacing_buckets = max(1, args.cooldown // args.window)
    picks = top_spikes(buckets, max_clips=args.max_clips, factor=args.factor, min_msgs=args.min_msgs, spacing_buckets=spacing_buckets)
    print(f"  ✓ Processed {len(events)} chat messages. Found {len(picks)} highlight moments.")

    for n, pick in enumerate(picks, 1):
        i = pick["bucket"]
        start_sec = max(0, i * args.window - args.pre + args.lag)
        raw_path = args.out / f"raw_{n:02d}.mp4"
        print(f"\n[Clip {n}/{len(picks)}] Downloading highlight at {time.strftime('%H:%M:%S', time.gmtime(start_sec))}...")
        cut_from_vod(url, start_sec, args.pre + args.post, raw_path, height=args.height)

        meta = {
            **pick,
            "stream_title": getattr(args, "stream_title", ""),
            "timestamp": time.strftime("%H:%M:%S", time.gmtime(start_sec))
        }
        process_and_save_clip(n, raw_path, meta, args)

    print(f"\n  [Done] Finished generating {len(picks)} clips in {args.out}")

def run_rerender(args):
    """Re-render existing clips after manual words_NN.json subtitle or layout edits."""
    clips_file = args.out / "clips.json"
    if not clips_file.exists():
        sys.exit(f"Error: {clips_file} not found.")

    clips = json.loads(clips_file.read_text(encoding="utf-8"))
    for item in clips:
        n = item["clip_number"]
        words_path = args.out / f"words_{n:02d}.json"
        raw_path = args.out / item["raw_file"]
        clip_path = args.out / item["file"]
        words = json.loads(words_path.read_text(encoding="utf-8")) if words_path.exists() else []

        print(f"Re-rendering {clip_path.name}...")
        render_vertical_reel(
            raw_path=raw_path,
            words=words,
            credit=args.credit or item.get("credit", ""),
            out_path=clip_path,
            layout=args.layout,
            focus=args.focus,
            facecam_pos=args.facecam_pos,
            caption_style=args.caption_style
        )
    print("  ✓ All clips re-rendered.")

def selftest():
    """Verify spike detector, transliterator, and ASS formatting."""
    print("Running Stack Cuts selftest suite...")

    # 1. Test Romanizer
    assert romanize_text("भाई क्या मारा") == "bhai kya mara"
    assert romanize_text("Hello World") == "Hello World"
    print("  ✓ Romanizer: PASSED")

    # 2. Test Chat Parsing
    dummy_chat = json.dumps({
        "replayChatItemAction": {
            "videoOffsetTimeMsec": "15000",
            "actions": [{
                "addChatItemAction": {
                    "item": {
                        "liveChatTextMessageRenderer": {
                            "timestampUsec": "1700000000000000",
                            "message": {"runs": [{"text": "CLIP THAT BRO! 🔥"}]}
                        }
                    }
                }
            }]
        }
    })
    parsed = parse_chat_line(dummy_chat)
    assert len(parsed) == 1 and parsed[0][0] == 15.0 and "CLIP" in parsed[0][1]
    print("  ✓ Chat Parser: PASSED")

    # 3. Test Spike Detector
    calm = [(t + 0.1 * k, "hi", 1.0) for t in range(0, 300, 10) for k in range(5)]
    spike = [(200 + 0.05 * k, "WTF NO WAY", 3.0) for k in range(35)]
    b = bucket(calm + spike, window_sec=10)
    is_spk, base, score = is_spike(b, 20, factor=2.5, min_msgs=8)
    assert is_spk and score > 5.0
    print("  ✓ Spike Detector: PASSED")

    # 4. Test Layout Filter Generation
    from core.layout import build_filter_graph
    vf = build_filter_graph("stacked", 30.0, "sub.ass", facecam_pos="bottom-left")
    assert "vstack=inputs=2" in vf and "crop=" in vf
    print("  ✓ Layout Compositor: PASSED")

    print("\nALL 4 TEST MODULES PASSED SUCCESSFULLY! ✓")

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["run", "render", "selftest"])
    parser.add_argument("target", nargs="?", help="YouTube URL (run) or clip directory (render)")
    parser.add_argument("--out", type=Path, default=None, help="Output directory for generated clips")
    parser.add_argument("--minutes", type=float, default=0, help="Live mode: record for N minutes (0 = continuous)")
    parser.add_argument("--max-clips", type=int, default=10, help="Maximum number of clips to produce")
    parser.add_argument("--window", type=int, default=10, help="Chat aggregation window in seconds")
    parser.add_argument("--factor", type=float, default=2.5, help="Highlight spike threshold factor")
    parser.add_argument("--min-msgs", type=int, default=8, help="Minimum chat messages in a window")
    parser.add_argument("--cooldown", type=int, default=60, help="Minimum seconds between distinct clips")
    parser.add_argument("--pre", type=float, default=22, help="Seconds preserved before the moment")
    parser.add_argument("--post", type=float, default=12, help="Seconds preserved after the moment")
    parser.add_argument("--lag", type=float, default=0, help="Fine-tune time offset (+/- seconds)")
    parser.add_argument("--height", type=int, default=720, help="Max video resolution height")
    parser.add_argument("--client", default="android", help="yt-dlp client emulation")
    parser.add_argument("--layout", choices=["stacked", "fill", "fit"], default="stacked", help="Vertical layout mode")
    parser.add_argument("--facecam-pos", choices=["top-left", "top-right", "bottom-left", "bottom-right"], default="bottom-left")
    parser.add_argument("--focus", type=float, default=0.5, help="Focus center for fill layout (0.0 to 1.0)")
    parser.add_argument("--credit", default=None, help="Streamer credit text")
    parser.add_argument("--caption-style", choices=["hormozi", "neon"], default="hormozi", help="Animated subtitle style")
    parser.add_argument("--whisper-model", default="small", help="Faster-Whisper model")
    parser.add_argument("--no-captions", action="store_true", help="Omit subtitle generation")
    parser.add_argument("--keep-recording", action="store_true", help="Retain full .ts stream file")

    args = parser.parse_args()

    if args.mode == "selftest":
        selftest()
        return

    if not args.target:
        parser.error("Please supply a YouTube URL for 'run' or directory path for 'render'.")

    if args.mode == "render":
        args.out = Path(args.target)
        run_rerender(args)
        return

    # Mode == run
    info = stream_info(args.target)
    args.credit = args.credit or info["channel"]
    args.stream_title = info["title"]
    args.out = args.out or (Path("clips") / info["id"])
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f" Stack Cuts: {info['channel']}")
    print(f" Stream: {info['title']}")
    print(f" Status: {'LIVE NOW' if info['live'] else 'FINISHED VOD'}")
    print(f" Layout: {args.layout.upper()} (Facecam: {args.facecam_pos})")
    print(f"=======================================================\n")

    if info["live"]:
        run_live(args.target, args)
    else:
        run_replay(args.target, args)

if __name__ == "__main__":
    main()
