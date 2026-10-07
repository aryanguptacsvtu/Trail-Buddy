# TrailBuddy

TrailBuddy is an offline, voice-first hiking companion. It chooses from real GPX trails, suggests short observation missions, answers questions with a local Ollama model, and saves a short journal after the outing.

## What you need

- Python 3.10 or newer
- [Ollama](https://ollama.com) with a local model
- A microphone and speakers for voice mode
- Optional: a Piper voice model for spoken replies

TrailBuddy does not create or navigate routes. Add GPX files exported from an online route planner to `routes/` before heading offline.

## Setup

Complete these steps while online:

1. Install Ollama and download a model:

   ```text
   ollama pull gemma3:4b
   ```

   `qwen3:4b` also works when selected with `TB_MODEL`.
2. Create and activate a virtual environment, then install dependencies:

   **Windows PowerShell**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   **macOS/Linux**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Put a Piper voice pair (`.onnx` and `.onnx.json`) in `models/`. Without one, replies are printed as text.
4. Export one or more local trails as `.gpx` files into `routes/`.
5. Run TrailBuddy once online so faster-whisper can download its speech-to-text model.

## Run

Make sure Ollama is running, then:

```bash
python run.py "2 hours, moderate fitness, scenic" --max-min 120
```

For a microphone-free test:

```bash
python run.py "quick loop" --text
```

During an outing:

- Press **Enter** to talk in voice mode.
- Press **s** to toggle screen-time tracking.
- Press **q** to finish and save the journal.

Journals are written to `journals/` as Markdown files.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `TB_MODEL` | Ollama model name | `gemma3:4b` |
| `TB_STT` | faster-whisper model size | `base.en` |
| `TB_VOICE` | Path to the Piper `.onnx` voice | `models/en_US-lessac-medium.onnx` |
| `OLLAMA_HOST` | Ollama API URL | `http://localhost:11434` |

## Current limitations

- Routes must be supplied as GPX files; there is no GPS tracking or route generation yet.
- The screen-time meter is manual.
- The talk control is the keyboard Enter key.
