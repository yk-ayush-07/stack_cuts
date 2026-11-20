"""ingester.py: Media ingestion, recording, process supervision, and stream slicing.
Handles cross-platform process trees, YouTube live streams, and keyframe-accurate cuts.
"""
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
from pathlib import Path

# Resolve yt-dlp binary (local venv prioritized)
_venv_ytdlp = Path(sys.executable).parent / ("yt-dlp.exe" if sys.platform == "win32" else "yt-dlp")
YTDLP = os.environ.get("YTDLP") or (str(_venv_ytdlp) if _venv_ytdlp.exists() else None) or shutil.which("yt-dlp") or "yt-dlp"

def kill_process_tree(proc):
    """Safely terminate a process and all its child processes on Windows and POSIX."""
    if proc is None or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif hasattr(os, "killpg"):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
    except (OSError, ProcessLookupError):
        pass

def run(cmd, **kw):
    """Run a command synchronously and check for success."""
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)

def stream_info(url):
    """Extract YouTube / stream metadata."""
    out = run([YTDLP, "--no-update", "--no-playlist", "-J", url]).stdout
    d = json.loads(out)
    return {
        "id": d["id"],
        "channel": d.get("channel") or d.get("uploader") or "Unknown Streamer",
        "title": d.get("title", ""),
        "live": d.get("live_status") == "is_live",
        "duration": d.get("duration") or 0.0
    }

def start_recorder(url, rec_path, height=720, client="android"):
    """Spawn a resilient background recorder copying live HLS into a growing .ts buffer."""
    return subprocess.Popen(
        [
            YTDLP, "--no-update", "-q",
            "--extractor-args", f"youtube:player_client={client}",
            "-f", f"b[height<={height}]/bv[height<={height}]+ba/b",
            "--hls-use-mpegts", "--no-part",
            "-o", str(rec_path), url
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )

def start_chat(url, out_dir):
    """Spawn a background live chat downloader streaming JSON fragments."""
    return subprocess.Popen(
        [
            YTDLP, "--no-update", "-q", "--skip-download",
            "--write-subs", "--sub-langs", "live_chat",
            "-o", str(Path(out_dir) / "chat"), url
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )

def duration(path):
    """Get accurate media duration via ffprobe."""
    try:
        out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).stdout.strip()
        return float(out) if out and out != "N/A" else 0.0
    except Exception:
        return 0.0

def cut_from_recording(rec_path, start, dur, raw_out):
    """Accurately slice a clip from the active MPEG-TS recording with PTS synchronization."""
    run([
        "ffmpeg", "-v", "error", "-y",
        "-ss", f"{max(0, start):.2f}",
        "-i", str(rec_path),
        "-t", f"{dur:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-avoid_negative_ts", "make_zero",
        str(raw_out)
    ])

def cut_from_vod(url, start, dur, raw_out, height=720):
    """Download only the requested time section of a finished stream VOD."""
    run([
        YTDLP, "--no-update", "-q",
        "--download-sections", f"*{max(0, start):.0f}-{max(0, start + dur):.0f}",
        "--force-keyframes-at-cuts",
        "-f", f"bv[height<={height}]+ba/b[height<={height}]/b",
        "--merge-output-format", "mp4",
        "-o", str(raw_out), url
    ])
