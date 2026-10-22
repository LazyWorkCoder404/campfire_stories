#!/usr/bin/env bash
cd "$(dirname "$0")/../services/ComfyUI"
source venv/bin/activate
python main.py
