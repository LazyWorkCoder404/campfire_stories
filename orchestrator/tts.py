"""Narrates scene text with Kokoro."""
import asyncio
import threading
from pathlib import Path

import numpy as np
import soundfile as sf

VOICE = "am_michael"   # try "bm_george" for a British storyteller
SAMPLE_RATE = 24000    # Kokoro always produces audio at this rate

_pipeline = None
_lock = threading.Lock()


def _to_numpy(audio):
    """Kokoro may hand back a PyTorch tensor; soundfile wants a NumPy array."""
    if hasattr(audio, "cpu"):
        return audio.cpu().numpy()
    return np.asarray(audio)


def _narrate_sync(text: str, save_path: Path) -> Path:
    """The slow, blocking part: runs in a background thread."""
    global _pipeline
    with _lock:  # one narration at a time, so two scenes never collide
        if _pipeline is None:
            from kokoro import KPipeline  # loaded on first use, then kept
            _pipeline = KPipeline(lang_code="a")
        pieces = [_to_numpy(audio) for _, _, audio in _pipeline(text, voice=VOICE)]

    save_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(save_path, np.concatenate(pieces), SAMPLE_RATE)
    return save_path


async def narrate(text: str, save_path: Path) -> Path:
    """Narrate text into a .wav file without freezing the server."""
    return await asyncio.to_thread(_narrate_sync, text, save_path)