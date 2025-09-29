
#!/usr/bin/env python3
# End-to-end automation: download a video (ffmpeg) and (optionally) transcribe it (whisper),
# with prompts at the start.
#
# New feature:
#   - At startup, asks whether to **Download Only** or **Download + Transcribe**.
#     If **Download Only** is chosen, the script stops right after the download step.
#
# Requirements:
#   - ffmpeg available in PATH
#   - openai-whisper installed (CLI command "whisper") → pip install -U openai-whisper
#
# Customization notes:
#   - DEFAULT LANGUAGE = "en" (English). If you want another language (e.g., "it"), enter it at the prompt.
#     If you choose a language different from "en" OR you choose 'auto', the script switches from "medium.en" (English-only) to "medium" (multilingual).
#   - DEFAULT DEVICE = "cuda". If you do NOT have CUDA/NVIDIA GPU, type "cpu" at the prompt.
#   - DEFAULT MODEL = "medium.en" (use "small.en" for more speed, or "large-v2" if you have more VRAM/time).
#
# Usage:
#   python3 auto_teams_whisper.py
#   0) choose action: Download Only OR Download + Transcribe
#   1) choose the output folder
#   2) paste the video link
#   3) choose language (Enter = en) and device (Enter = cuda)
#   → then the script runs until completion (or stops after download if chosen)

import os
import sys
import shutil
import subprocess
from urllib.parse import urlsplit, urlunsplit

def trim_after_altmanifest(url: str) -> str:
    parts = urlsplit(url)
    q = parts.query
    if not q:
        print("[i] No 'altManifest*' parameter found: using URL as is.")
        return url

    q_lower = q.lower()
    pos = q_lower.find("altmanifest")
    if pos == -1:
        print("[i] No 'altManifest*' parameter found: using URL as is.")
        return url

    amp = q.rfind("&", 0, pos)
    if amp == -1:
        new_query = ""
        kept = "(empty)"
    else:
        new_query = q[:amp]
        new_query = new_query.rstrip("&")
        kept = new_query if new_query else "(empty)"

    print(f"[i] Truncating URL at 'altManifest*'. Remaining query: {kept}")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

def prompt_mode() -> str:
    print("\n== Action ==")
    print("[1] Download Only (stop after saving the video)")
    print("[2] Download + Transcribe with Whisper (default)")
    try:
        choice = input("Choose 1 or 2 [default: 2]: ").strip()
    except EOFError:
        choice = ""
    if choice == "1":
        print("[i] Selected: Download Only.")
        return "download"
    else:
        print("[i] Selected: Download + Transcribe.")
        return "transcribe"

def prompt_all_inputs():
    default_dir = "transcripts"
    try:
        outdir_in = input(f"Where do you want to save the files? (Enter = {default_dir}): ").strip()
    except EOFError:
        outdir_in = ""
    outdir = os.path.abspath(os.path.expanduser(outdir_in or default_dir))

    try:
        url = input("Paste the video link (Teams/Stream) and press Enter: ").strip()
    except EOFError:
        url = ""
    if not url:
        print("[x] No URL provided. Exiting.")
        sys.exit(1)

    default_language = "en"
    default_device   = "cuda"
    default_model    = "medium.en"

    try:
        lang_in = input(f"Transcription language? (Enter = {default_language}; use 'auto' for automatic detection): ").strip()
    except EOFError:
        lang_in = ""
    language = (lang_in or default_language).lower()

    try:
        dev_in = input(f"Device? (Enter = {default_device}; type 'cpu' if you don't have CUDA): ").strip()
    except EOFError:
        dev_in = ""
    device = (dev_in or default_device).lower()
    if device not in {"cuda","cpu"}:
        print(f"[!] Unrecognized device: '{device}'. Using default: {default_device}.")
        device = default_device

    model = default_model
    if (language != "en" or language == "auto") and default_model.endswith(".en"):
        model = default_model.replace(".en", "")
        print(f"[i] Requested language = '{language}'. Switching model from '{default_model}' → '{model}' (multilingual).")

    return outdir, url, language, device, model

def ensure_cmd_on_path(cmd: str, help_hint: str):
    if shutil.which(cmd) is None:
        print(f"[x] Command '{cmd}' not found in PATH. {help_hint}")
        sys.exit(1)

def resolve_device(device: str) -> str:
    if device == "cuda":
        try:
            import torch  # type: ignore
            if not torch.cuda.is_available():
                print("[!] CUDA not available according to PyTorch. Falling back to 'cpu'.")
                return "cpu"
            else:
                print("[i] CUDA available: using 'cuda'.")
                return "cuda"
        except Exception:
            if shutil.which("nvidia-smi") is None:
                print("[!] Neither PyTorch CUDA nor 'nvidia-smi' detected. Falling back to 'cpu'.")
                return "cpu"
            print("[i] GPU detected via 'nvidia-smi': using 'cuda'.")
            return "cuda"
    return "cpu"

def make_paths(outdir: str, url: str):
    os.makedirs(outdir, exist_ok=True)
    url_trimmed = trim_after_altmanifest(url)
    basename = "video"
    mp4_path = os.path.join(outdir, f"{basename}.mp4")
    return url_trimmed, basename, mp4_path

def run_ffmpeg(url_trimmed: str, mp4_path: str):
    os.makedirs(os.path.dirname(mp4_path), exist_ok=True)
    print("[i] Downloading video with ffmpeg...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", url_trimmed,
        "-codec", "copy",
        mp4_path
    ], check=True)
    print(f"[✓] Video saved: {mp4_path}")

def run_whisper(mp4_path: str, outdir: str, model: str, language: str, device: str):
    print(f"[i] Starting Whisper transcription → model={model}, language={language}, device={device}")
    cmd = [
        "whisper",
        mp4_path,
        "--model", model,
        "--device", device,
        "--output_format", "txt",
        "--output_dir", outdir,
    ]
    if language != "auto":
        cmd += ["--language", language]

    cmd_verbose = cmd + ["--verbose", "False"]
    try:
        subprocess.run(cmd_verbose, check=True)
    except subprocess.CalledProcessError:
        print("[!] '--verbose False' not supported? Retrying without '--verbose'.")
        subprocess.run(cmd, check=True)

def pick_txt_output(outdir: str, basename: str):
    txt_path = os.path.join(outdir, f"{basename}.txt")
    if os.path.exists(txt_path):
        print(f"[✓] Transcript ready: {txt_path}")
        return txt_path

    candidates = []
    for f in os.listdir(outdir):
        if f.endswith(".txt") and f.startswith(basename):
            candidates.append(os.path.join(outdir, f))
    if not candidates:
        candidates = [os.path.join(outdir, f) for f in os.listdir(outdir) if f.endswith(".txt")]

    if candidates:
        latest = max(candidates, key=os.path.getmtime)
        print(f"[i] Found TXT output (newest): {latest}")
        return latest

    print("[x] Couldn't find the .txt output. Check whisper logs.")
    return None

def main():
    ensure_cmd_on_path("ffmpeg", "Install ffmpeg and ensure it's in PATH.")
    ensure_cmd_on_path("whisper", "Install openai-whisper with: pip install -U openai-whisper")

    mode = prompt_mode()  # 'download' or 'transcribe'

    outdir, url, language, device_req, model = prompt_all_inputs()
    url_trimmed, basename, mp4_path = make_paths(outdir, url)

    device = resolve_device(device_req)
    if device != device_req:
        print(f"[i] Device fallback: requested='{device_req}', effective='{device}'.")

    run_ffmpeg(url_trimmed, mp4_path)

    if mode == "download":
        print("[i] Download completed. Exiting as requested (Download Only).")
        sys.exit(0)

    try:
        run_whisper(mp4_path, outdir, model, language, device)
    except subprocess.CalledProcessError as e:
        print(f"[x] Error while running whisper: exit code {e.returncode}.")
        sys.exit(e.returncode)

    pick_txt_output(outdir, basename)

if __name__ == "__main__":
    main()
