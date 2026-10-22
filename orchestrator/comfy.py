"""Generates illustrations with ComfyUI."""
import asyncio
import json
import random
import uuid
from pathlib import Path

import httpx

COMFY_URL = "http://127.0.0.1:8188"
PROJECT = Path(__file__).parent.parent
WORKFLOW_FILE = PROJECT / "workflows" / "pumpkin.json"   # change to switch workflows

# Added to every prompt so all the illustrations share one look
STYLE = (
    ". Moody cinematic lighting, eerie atmosphere, painterly storybook illustration, "
    "rich deep shadows, warm firelight against cold moonlight"
)


def _find_node(workflow: dict, class_type: str) -> dict:
    """Find a node by its type, so we never depend on node numbers."""
    for node in workflow.values():
        if node.get("class_type") == class_type:
            return node
    raise ValueError(f"No {class_type} node found in {WORKFLOW_FILE.name}")


def build_workflow(prompt: str, seed: int) -> dict:
    """Load the workflow and fill in this image's prompt and seed."""
    workflow = json.loads(WORKFLOW_FILE.read_text())
    _find_node(workflow, "CLIPTextEncode")["inputs"]["text"] = prompt + STYLE
    _find_node(workflow, "KSampler")["inputs"]["seed"] = seed
    return workflow


async def generate_image(prompt: str, save_path: Path, seed: int | None = None) -> Path:
    """Make one image and save it to save_path."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    workflow = build_workflow(prompt, seed)

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Hand the job to ComfyUI and get a ticket number
        response = await client.post(
            f"{COMFY_URL}/prompt",
            json={"prompt": workflow, "client_id": str(uuid.uuid4())},
        )
        response.raise_for_status()
        prompt_id = response.json()["prompt_id"]

        # 2. Check every half second until it's done (up to 5 minutes)
        for _ in range(600):
            await asyncio.sleep(0.5)
            history = (await client.get(f"{COMFY_URL}/history/{prompt_id}")).json()
            if prompt_id in history:
                break
        else:
            raise TimeoutError("ComfyUI took too long")

        job = history[prompt_id]
        if job.get("status", {}).get("status_str") == "error":
            raise RuntimeError("ComfyUI reported an error; check its terminal")

        # 3. Download the finished image and save it
        for output in job["outputs"].values():
            for image in output.get("images", []):
                response = await client.get(f"{COMFY_URL}/view", params=image)
                response.raise_for_status()
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(response.content)
                return save_path

    raise RuntimeError("ComfyUI finished but returned no image")