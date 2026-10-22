#!/usr/bin/env bash
# Campfire Stories: start everything with one command.
# Starts ComfyUI and the game server, waits until both are ready, then opens the browser.
# Press Ctrl+C to stop everything.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"

LLM_MODEL="${CAMPFIRE_LLM:-gemma3:12b}"
PORT="${CAMPFIRE_PORT:-8000}"
COMFY_DIR="$ROOT/services/ComfyUI"
GAME_URL="http://localhost:$PORT"

ok()   { printf '\033[1;32m%s\033[0m\n' "$1"; }
info() { printf '\033[1;33m%s\033[0m\n' "$1"; }
die()  { printf '\033[1;31m%s\033[0m\n' "$1"; exit 1; }

[[ -x .venv/bin/uvicorn && -x "$COMFY_DIR/venv/bin/python" ]] || die "Setup hasn't been run yet. Run ./setup.sh first."
mkdir -p logs output

PIDS=()
cleanup() {
    echo
    info "Shutting down..."
    for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null; done
    wait 2>/dev/null
    # Free the story model's memory for other users of this machine
    curl -fs http://localhost:11434/api/generate \
        -d "{\"model\": \"$LLM_MODEL\", \"keep_alive\": 0}" >/dev/null 2>&1
    ok "Stopped."
}
trap cleanup EXIT
trap 'exit 0' INT TERM

wait_for() {  # wait_for <url> <seconds> <name> <log file>
    for ((i = 0; i < $2; i++)); do
        curl -fs "$1" >/dev/null 2>&1 && return 0
        sleep 1
    done
    die "$3 didn't start within $2 seconds. See $4 for details."
}

# 1. Ollama runs as a system service; make sure it's up
curl -fs http://localhost:11434/api/tags >/dev/null || die "Ollama isn't running. Try: sudo systemctl start ollama"

# 2. ComfyUI (reuse it if it's already running)
if curl -fs http://127.0.0.1:8188 >/dev/null 2>&1; then
    ok "ComfyUI already running"
else
    info "Starting ComfyUI..."
    (cd "$COMFY_DIR" && exec venv/bin/python main.py) > logs/comfyui.log 2>&1 &
    PIDS+=($!)
    wait_for http://127.0.0.1:8188 180 "ComfyUI" logs/comfyui.log
    ok "ComfyUI ready"
fi

# 3. Load the story model now and keep it loaded for an hour, so the first story is fast
info "Warming up the storyteller ($LLM_MODEL)..."
curl -fs http://localhost:11434/api/generate \
    -d "{\"model\": \"$LLM_MODEL\", \"keep_alive\": \"1h\"}" >/dev/null \
    || die "Couldn't load $LLM_MODEL. Run: ollama pull $LLM_MODEL"

# 4. The game server
curl -fs "$GAME_URL" >/dev/null 2>&1 && die "Something is already using port $PORT. Close it, or run: CAMPFIRE_PORT=8001 ./start.sh"
info "Starting the game server..."
CAMPFIRE_LLM="$LLM_MODEL" .venv/bin/uvicorn orchestrator.main:app --port "$PORT" > logs/server.log 2>&1 &
PIDS+=($!)
wait_for "$GAME_URL/health" 60 "The game server" logs/server.log

HEALTH="$(curl -fs "$GAME_URL/health")"
if [[ "$HEALTH" =~ \"ollama\":\ *true && "$HEALTH" =~ \"comfyui\":\ *true ]]; then
    ok "All systems ready: $HEALTH"
else
    info "Warning, health check reports: $HEALTH"
fi

# 5. Open the game
echo
ok "Campfire Stories is running at $GAME_URL"
echo "Logs are in the logs/ folder. Press Ctrl+C to stop."
command -v xdg-open >/dev/null && xdg-open "$GAME_URL" >/dev/null 2>&1 &

# Stay running until Ctrl+C, or until either service stops on its own
wait -n "${PIDS[@]}"
die "A service stopped unexpectedly. Check logs/comfyui.log and logs/server.log."
