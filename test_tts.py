from pathlib import Path
from kokoro import KPipeline
import soundfile as sf

out_dir = Path(__file__).parent / "output"
out_dir.mkdir(exist_ok=True)

pipeline = KPipeline(lang_code="a")  # "a" = American English
text = "The fire crackled low. Somewhere past the tree line, something answered."

for i, (_, _, audio) in enumerate(pipeline(text, voice="am_michael")):
    path = out_dir / f"test_{i}.wav"
    sf.write(path, audio, 24000)
    print("Saved:", path)