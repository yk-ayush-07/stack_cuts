"""Stack Cuts Core Module
"""
from .ingester import stream_info, start_recorder, start_chat, cut_from_recording, cut_from_vod, kill_process_tree, duration
from .chat_monitor import parse_chat_line, bucket
from .highlight_detector import is_spike, top_spikes
from .transcriber import transcribe_audio
from .romanizer import romanize_text
from .renderer import render_vertical_reel
from .ai_hooks import generate_clip_metadata

__all__ = [
    "stream_info", "start_recorder", "start_chat", "cut_from_recording", "cut_from_vod",
    "kill_process_tree", "duration", "parse_chat_line", "bucket", "is_spike", "top_spikes",
    "transcribe_audio", "romanize_text", "render_vertical_reel", "generate_clip_metadata"
]
