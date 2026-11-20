"""transcriber.py: Faster-Whisper integration with word-level timestamps and Romanization.
"""
from pathlib import Path
from .romanizer import romanize_text

def transcribe_audio(video_path: Path, model_name: str = "small", compute_device: str = "cpu"):
    """
    Transcribe words from video audio with millisecond timestamps and Roman transliteration.
    Returns list of dicts: [{"w": "WORD", "s": 1.25, "e": 1.80}]
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("  [Notice] faster-whisper not installed: continuing without speech captions.")
        return []

    try:
        model = WhisperModel(model_name, device=compute_device, compute_type="int8")
        segments, _ = model.transcribe(str(video_path), word_timestamps=True)
        
        words = []
        for segment in segments:
            for word_info in segment.words:
                raw_w = word_info.word.strip()
                if not raw_w:
                    continue
                # Automatically romanize Hindi/Devanagari text to Latin characters
                clean_w = romanize_text(raw_w)
                words.append({
                    "w": clean_w,
                    "s": round(word_info.start, 2),
                    "e": round(word_info.end, 2)
                })
        return words
    except Exception as e:
        print(f"  [Warning] Transcription encountered an issue: {e}")
        return []
