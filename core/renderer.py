"""renderer.py: FFmpeg rendering engine with dynamic ASS captions, audio normalization, and 9:16 compositing.
"""
import subprocess
from pathlib import Path
from .layout import build_filter_graph
from .ingester import duration

COLOR_YELLOW = "&H00D7FF&"  # ASS format is BGR
COLOR_CYAN = "&HFFFF00&"
COLOR_WHITE = "&H00FFFFFF&"

def _has_audio_stream(path: Path) -> bool:
    """Check whether a media file contains at least one audio stream."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True
        ).stdout.strip()
        return len(out) > 0
    except Exception:
        return True  # assume audio exists if probe fails

def ass_time(t: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cs"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def write_ass_subtitles(words, credit: str, total_duration: float, ass_path: Path, style: str = "hormozi"):
    """
    Generate an ASS subtitle script with active word-highlighting and top streamer credit.
    """
    highlight_color = COLOR_CYAN if style == "neon" else COLOR_YELLOW

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV\n"
        "Style: Cap,Arial Black,84,&H00FFFFFF,&H00000000,&H80000000,1,1,6,2,2,60,60,450\n"
        "Style: Credit,Arial,42,&H00FFFFFF,&H96000000,&H96000000,1,3,10,0,8,60,60,130\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Text\n"
    )

    lines = []
    if credit:
        lines.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total_duration)},Credit,clip credit: {credit}")

    chunk = []
    prev_end = 0.0

    # Group into punchy 2-3 word chunks
    for w in words + [None]:
        if w and (not chunk or (len(chunk) < 3 and w["s"] - chunk[-1]["e"] < 0.6)):
            chunk.append(w)
            continue

        for k, current_word in enumerate(chunk):
            end = chunk[k + 1]["s"] if k + 1 < len(chunk) else min(current_word["e"] + 0.15, w["s"] if w else 1e9)
            
            # Format chunk text with active word highlighted
            formatted_words = []
            for item in chunk:
                word_txt = item["w"].upper()
                if item is current_word:
                    formatted_words.append(f"{{\\c{highlight_color}}}{word_txt}{{\\c{COLOR_WHITE}}}")
                else:
                    formatted_words.append(word_txt)

            start = max(current_word["s"], prev_end)
            prev_end = max(end, start + 0.05)
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(prev_end)},Cap,{' '.join(formatted_words)}")

        chunk = [w] if w else []

    ass_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")

def render_vertical_reel(raw_path: Path, words, credit: str, out_path: Path,
                         layout: str = "fill", focus: float = 0.5, facecam_pos: str = "bottom-left",
                         caption_style: str = "hormozi"):
    """
    Produce a production-ready 1080x1920 vertical reel with normalized audio and burned captions.
    """
    raw_path, out_path = Path(raw_path), Path(out_path)
    dur = duration(raw_path)
    ass_path = out_path.with_suffix(".ass")

    # Generate captions if words exist
    if words:
        write_ass_subtitles(words, credit, dur, ass_path, style=caption_style)
        ass_name = ass_path.name
    else:
        ass_name = ""

    vf = build_filter_graph(layout, dur, ass_name, focus=focus, facecam_pos=facecam_pos)

    # Probe for audio stream to decide whether to include loudness normalization
    has_audio = _has_audio_stream(raw_path)

    if has_audio:
        # Merge audio loudness normalization into filter_complex so FFmpeg
        # doesn't reject the separate -af flag alongside -filter_complex.
        af = "loudnorm=I=-14:TP=-1.5:LRA=11"
        full_filter = vf + f";[0:a]anull,{af}[a]"
        map_args = ["-map", "[v]", "-map", "[a]"]
        audio_args = ["-c:a", "aac", "-b:a", "192k"]
    else:
        full_filter = vf
        map_args = ["-map", "[v]"]
        audio_args = []

    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-i", str(raw_path.resolve()),
        "-filter_complex", full_filter,
        *map_args,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        *audio_args,
        "-movflags", "+faststart",
        str(out_path.name)
    ]

    subprocess.run(cmd, check=True, cwd=out_path.parent)
