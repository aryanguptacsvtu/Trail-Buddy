import os, subprocess, tempfile, wave
import numpy as np
import sounddevice as sd


SR = 16000
_stt = None


def listen():
    input("  [Enter] to talk... ")
    frames = []
    
    with sd.InputStream(samplerate=SR, channels=1, dtype="int16",
                        callback=lambda d, *_: frames.append(d.copy())):
        input("  listening, [Enter] to stop... ")
    
    if not frames:
        return ""
    
    audio = np.concatenate(frames).flatten().astype(np.float32) / 32768
    global _stt
    
    if _stt is None:
        from faster_whisper import WhisperModel
        _stt = WhisperModel(os.getenv("TB_STT", "base.en"), device="cpu", compute_type="int8")
    segs, _ = _stt.transcribe(audio, language="en")
    
    return " ".join(s.text for s in segs).strip()


def speak(text):
    
    print(f"TrailBuddy: {text}")
    voice = os.getenv("TB_VOICE", "models/en_US-lessac-medium.onnx")
    
    if not os.path.exists(voice):
        return  # text-only fallback
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    subprocess.run(["python", "-m", "piper", "--model", voice, "--output_file", out],
                   input=text.encode(), check=True, capture_output=True)
    
    with wave.open(out) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        sd.play(data, w.getframerate()); sd.wait()
    
    os.unlink(out)
