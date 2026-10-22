# Campfire Stories: Setup and Running

Everything runs locally: **Ollama** writes the story, **ComfyUI** paints the illustrations, and **Kokoro** narrates. Nothing calls out to the cloud once it's installed.

## What you need

- **Linux with an NVIDIA GPU** and a working driver (`nvidia-smi` should list your card). Developed on Ubuntu 24.04 on an NVIDIA DGX Spark (GB10, 128 GB unified memory).
- **Memory:** the story model and image model are loaded at the same time. On a regular graphics card, plan on 16 GB of VRAM or more.
- **Disk:** about 40 GB free (image model ~20 GB, story model ~8 GB, plus two PyTorch installs).
- **Python 3.12**, Git, and a few system packages (below).

## 1. System packages

```bash
sudo apt update
sudo apt install git python3.12-venv python3-full python3.12-dev build-essential espeak-ng
```

- `python3.12-venv` / `python3-full`: needed to create virtual environments.
- `python3.12-dev` / `build-essential`: ComfyUI compiles a small piece of C code on first run and fails without these.
- `espeak-ng`: Kokoro uses it for pronunciation.

## 2. Ollama (the storyteller)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:12b
```

Ollama installs as a background service and starts on boot, so you never launch it yourself.

**Optional, bigger model:** `ollama pull gemma3:27b` (about 17 GB), then start the server with `CAMPFIRE_LLM=gemma3:27b` in front of the `uvicorn` command in step 7.

## 3. Get the project

```bash
cd ~/PycharmProjects            # or wherever you keep projects
git clone https://github.com/YOUR-USERNAME/campfire_stories.git
cd campfire_stories
```

## 4. Project environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p output
```

Your prompt should now start with `(.venv)`. The install takes a few minutes because Kokoro pulls in PyTorch. Kokoro also downloads its voice model the first time it speaks.

## 5. ComfyUI (the illustrator)

ComfyUI isn't stored in the repo. Install it into `services/` with its **own** environment, separate from the project's:

```bash
mkdir -p services
cd services
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install torch torchvision torchaudio
pip install -r requirements.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
deactivate
cd ../..
```

The last check must print a version number followed by **`True`**. If it says `False`, install the CUDA build of PyTorch using the command from pytorch.org (*Get Started* → Linux / Pip / Python / your CUDA version) inside that venv.

### Image model: Z-Image Turbo

The game uses **Z-Image Turbo**, which is three files (about 20 GB in total). Each goes in its own folder under `services/ComfyUI/models/`:

| File | Folder |
|---|---|
| `z_image_turbo_bf16.safetensors` | `diffusion_models/` |
| `qwen_3_4b.safetensors` | `text_encoders/` |
| `ae.safetensors` | `vae/` |

The easiest way to get them: start ComfyUI (step 7), open `http://127.0.0.1:8188`, go to **Workflow → Browse Templates**, search for **Z-Image Turbo**, and open it. ComfyUI offers to download any missing files. If your browser saves them to `~/Downloads`, move them into the folders above, then restart ComfyUI.

Click **Run** once in that template to confirm an image appears.

### The workflow file

The game sends its prompts through `workflows/pumpkin.json`, which is included in the repo. If it's missing, create it from the Z-Image Turbo template in ComfyUI with **Workflow → Export (API)** (not plain Export) and save it as `workflows/pumpkin.json`.

## 6. Quick checks (optional)

With `(.venv)` active, from the project root:

```bash
python test_tts.py     # writes output/test_0.wav; play it with: aplay output/test_0.wav
python test_gpu.py     # prints GPU stats the fire animation reads
```

## 7. Start the game

You need **two terminals**, both in the project folder.

**Terminal 1: ComfyUI**
```bash
chmod +x scripts/start_comfyui.sh    # first time only
./scripts/start_comfyui.sh
```
Leave it running. It's ready when it prints that it's serving on `127.0.0.1:8188`.

**Terminal 2: the game server**
```bash
source .venv/bin/activate
uvicorn orchestrator.main:app --port 8000
```
(Add `--reload` while you're editing code, so the server restarts whenever you save a file.)

**Then open** `http://localhost:8000` and tap the fire.

To confirm everything is connected, open `http://localhost:8000/health`. You should see:

```json
{"ollama": true, "comfyui": true}
```

### Faster first story (optional)

Ollama unloads the story model after 5 minutes of no use, making the next story slow to start. To keep it loaded for an hour without changing any system settings:

```bash
curl http://localhost:11434/api/generate -d '{"model": "gemma3:12b", "keep_alive": "1h"}'
```

## Stopping

Press **Ctrl+C** in both terminals. To free the story model's memory right away:

```bash
curl http://localhost:11434/api/generate -d '{"model": "gemma3:12b", "keep_alive": 0}'
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `externally-managed-environment` when running `pip` | The project environment isn't active. Run `source .venv/bin/activate` and check your prompt starts with `(.venv)`. |
| `No module named 'kokoro'` (or `fastapi`, etc.) | Wrong environment: probably ComfyUI's is active. Run `deactivate`, then `source .venv/bin/activate`. |
| `Command 'python' not found` | Same cause: no environment is active. |
| ComfyUI fails with a compile/Triton error | Install `python3.12-dev build-essential` (step 1) and restart ComfyUI. |
| Model boxes in ComfyUI show nothing to pick | A `.safetensors` file is in the wrong folder. Check the table in step 5. |
| `/health` shows `"comfyui": false` | ComfyUI isn't running. Start it in terminal 1. |
| `/health` shows `"ollama": false` | Run `systemctl status ollama`; if it's stopped, `sudo systemctl start ollama`. Confirm the model with `ollama list`. |
| `address already in use` on port 8000 | The server is already running in another terminal. Close it or use `--port 8001`. |

Every new terminal starts outside the environment, so run `source .venv/bin/activate` again each time. In PyCharm, set **Settings → Project → Python Interpreter** to `.venv/bin/python` and its terminal does it for you.
