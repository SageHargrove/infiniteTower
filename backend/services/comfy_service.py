import json
import time
import random
import requests
import os

COMFY_URL = "http://127.0.0.1:8188"
CHECKPOINT = os.getenv("COMFY_CHECKPOINT", "noobaiXLNAIXL_vPred10Version.safetensors")
LORA_NAME = os.getenv("COMFY_LORA", None)
LORA_STRENGTH = float(os.getenv("COMFY_LORA_STRENGTH", "0.8"))


def _build_workflow(prompt: str, negative: str = "", seed: int = None, init_image_name: str = None, denoise: float = 0.45, width: int = 832, height: int = 1216, hires: bool = False, hires_denoise: float = 0.55) -> dict:
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    full_prompt = (
        "masterpiece, best quality, amazing quality, very aesthetic, "
        "dark fantasy, anime style, " + prompt
    )

    neg = negative or (
        "blurry, low quality, watermark, text, signature, bad anatomy, "
        "deformed, ugly, disfigured, worst quality, jpeg artifacts"
    )

    # model source: checkpoint by default, lora loader if lora configured
    model_source = ["4", 0]
    clip_source = ["4", 1]

    # hires=True runs a second, lower-denoise KSampler pass over a latent
    # upscale of the first pass's output — single-pass generation at a
    # busy, multi-subject composition (vs. a tight single-character
    # portrait) tends to come out simpler/blurrier than this game's other
    # scene-style art, since the base checkpoint resolution is fighting the
    # composition's complexity. The upscale-and-refine pass gives the model
    # a second look at the full composition instead of trying to render all
    # that detail in one pass.
    final_samples_source = ["3", 0]
    if hires and not init_image_name:
        final_samples_source = ["14", 0]

    workflow = {
        "4": {
            "inputs": {"ckpt_name": CHECKPOINT},
            "class_type": "CheckpointLoaderSimple"
        },
        "8": {
            "inputs": {"samples": final_samples_source, "vae": ["4", 2]},
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {"filename_prefix": "infinite_gacha", "images": ["8", 0]},
            "class_type": "SaveImage"
        }
    }

    # Add LoRA node if configured, rewire model/clip sources
    if LORA_NAME:
        workflow["10"] = {
            "inputs": {
                "lora_name": LORA_NAME,
                "strength_model": LORA_STRENGTH,
                "strength_clip": LORA_STRENGTH,
                "model": ["4", 0],
                "clip": ["4", 1]
            },
            "class_type": "LoraLoader"
        }
        model_source = ["10", 0]
        clip_source = ["10", 1]

    workflow["6"] = {
        "inputs": {"text": full_prompt, "clip": clip_source},
        "class_type": "CLIPTextEncode"
    }
    workflow["7"] = {
        "inputs": {"text": neg, "clip": clip_source},
        "class_type": "CLIPTextEncode"
    }
    if init_image_name:
        workflow["11"] = {
            "inputs": {"image": init_image_name, "upload": "image"},
            "class_type": "LoadImage"
        }
        workflow["12"] = {
            "inputs": {"pixels": ["11", 0], "vae": ["4", 2]},
            "class_type": "VAEEncode"
        }
        latent_image_source = ["12", 0]
        denoise_val = denoise
        base_width, base_height = width, height
    elif hires:
        # First pass renders smaller (at the checkpoint's natural strong
        # resolution for complex scenes), second pass upscales to the real
        # target size and refines.
        base_width = (int(width * 0.65) // 8) * 8
        base_height = (int(height * 0.65) // 8) * 8
        workflow["5"] = {
            "inputs": {"width": base_width, "height": base_height, "batch_size": 1},
            "class_type": "EmptyLatentImage"
        }
        latent_image_source = ["5", 0]
        denoise_val = 1.0
    else:
        workflow["5"] = {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage"
        }
        latent_image_source = ["5", 0]
        denoise_val = 1.0

    workflow["3"] = {
        "inputs": {
            "seed": seed,
            "steps": 28,
            "cfg": 7.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": denoise_val,
            "model": model_source,
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": latent_image_source
        },
        "class_type": "KSampler"
    }

    if hires and not init_image_name:
        workflow["13"] = {
            "inputs": {
                "samples": ["3", 0],
                "upscale_method": "bislerp",
                "width": width,
                "height": height,
                "crop": "disabled"
            },
            "class_type": "LatentUpscale"
        }
        workflow["14"] = {
            "inputs": {
                "seed": seed + 1,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": hires_denoise,
                "model": model_source,
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["13", 0]
            },
            "class_type": "KSampler"
        }

    return workflow


def _queue_prompt(workflow: dict) -> str | None:
    try:
        response = requests.post(
            f"{COMFY_URL}/prompt",
            json={"prompt": workflow},
            timeout=10.0
        )
        if response.status_code != 200:
            print(f"[ComfyUI] 400 detail: {response.text}")
            return None
        return response.json()["prompt_id"]
    except Exception as e:
        print(f"[ComfyUI] Failed to queue prompt: {e}")
        return None


def _wait_for_result(prompt_id: str, timeout: int = 180) -> str | None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=5.0)
            history = resp.json()
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        return node_output["images"][0]["filename"]
        except Exception:
            pass
        time.sleep(2.0)
    return None


def _download_image(filename: str, save_path: str) -> bool:
    try:
        resp = requests.get(
            f"{COMFY_URL}/view",
            params={"filename": filename, "type": "output"},
            timeout=30.0
        )
        resp.raise_for_status()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"[ComfyUI] Failed to download image: {e}")
        return False


def is_comfy_running() -> bool:
    try:
        requests.get(f"{COMFY_URL}/system_stats", timeout=3.0)
        return True
    except Exception:
        return False


def _upload_image(file_path: str) -> str | None:
    try:
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"image": (filename, f, "image/png")}
            resp = requests.post(f"{COMFY_URL}/upload/image", files=files, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data.get("name")
    except Exception as e:
        print(f"[ComfyUI] Failed to upload image {file_path}: {e}")
        return None


def generate_portrait_comfy(prompt: str, save_path: str, init_image_path: str = None, denoise: float = 0.45, negative: str = "", width: int = 832, height: int = 1216, hires: bool = False, hires_denoise: float = 0.55) -> bool:
    if not is_comfy_running():
        print("[ComfyUI] Server not running — skipping.")
        return False

    init_image_name = None
    if init_image_path and os.path.exists(init_image_path):
        init_image_name = _upload_image(init_image_path)

    workflow = _build_workflow(prompt, negative=negative, init_image_name=init_image_name, denoise=denoise, width=width, height=height, hires=hires, hires_denoise=hires_denoise)
    prompt_id = _queue_prompt(workflow)
    if not prompt_id:
        return False

    filename = _wait_for_result(prompt_id)
    if not filename:
        print("[ComfyUI] Timed out waiting for result.")
        return False

    return _download_image(filename, save_path)