# Microsoft Teams Recording Downloader & Whisper Transcriber

A CLI that **downloads Microsoft Teams / SharePoint meeting recordings** (from the `videomanifest` URL) and **optionally transcribes** them with **OpenAI Whisper**.

- **New:** At startup you choose: **Download Only** _or_ **Download + Transcribe**.  
- **Smart URL cleanup:** trims everything **from the first `altManifest*` onward** (case-insensitive) to avoid segment issues.  
- **Auto language:** set language to `auto` to let Whisper detect it.  
- **Model auto-switch:** if your default model ends with `.en` and you pick a non-English language or `auto`, it switches to the multilingual variant.  
- **CUDA→CPU fallback:** if CUDA isn’t available, it automatically uses CPU and tells you.  
- **Robust TXT pick:** after transcribing, it looks for `video.txt`, otherwise picks the newest `.txt` in the output folder.

> ⚠️ Use **only** with content you’re authorized to access. This tool does **not** 😉 bypass DRM.

---

## Requirements

- **Python 3.9+**
- **ffmpeg** available in your `PATH`
- **OpenAI Whisper (CLI)**  
  ```bash
  pip install -U openai-whisper
  ```

> On Windows, use `py` instead of `python3` in the examples.

---

## Getting the Teams/SharePoint `videomanifest` URL (Browser)

You need the **`videomanifest`** request URL from your browser’s Developer Tools.

1. **Open the video** in your browser (Teams/SharePoint player).  
2. Press **F12** (or menu → **Web Developer** → **Toggle Tools**).  
3. Go to the **Network** tab.  
4. Start/seek the video so network requests appear.  
5. In the filter box, type **`videomanifest`** (or sort by **Type** and look for **DASH/MPD** requests).  
6. Click the request named `videomanifest?...`.  
7. Right-click it → **Copy** → **Copy URL** (or **Copy → Copy cURL** if you also need headers later).  
8. Paste that URL into the script when asked.

> Tip: These URLs often contain **short-lived tokens** (e.g., `tempauth=...`). Copy a **fresh** URL and run the script soon after.

---

## Usage

Run from a terminal so you can see logs and errors.

**macOS / Linux**
```bash
python3 auto_teams_whisper.py
```

**Windows (PowerShell)**
```powershell
py .uto_teams_whisper.py
```

You’ll be prompted:

0. **Action**  
   - `[1] Download Only` → saves the video and **exits**  
   - `[2] Download + Transcribe` (default) → saves the video and **runs Whisper**
1. **Output folder** (default: `transcripts/`)
2. **Video link**  
   - paste the **`videomanifest`** URL you captured
   - the script will **truncate everything from the first `altManifest*` onward**
3. **Transcription language**  
   - press Enter for `en` or type `auto` (auto-detect)
4. **Device**  
   - Enter for `cuda`; type `cpu` if you don’t have CUDA

**What happens next**

- The cleaned URL is passed to **ffmpeg**, which downloads `video.mp4` into your chosen folder.  
- If you chose **Download + Transcribe**, Whisper runs and outputs a `.txt` transcript in the same folder.


```
## Acknowledgements

- https://ffmpeg.org/
- https://github.com/openai/whisper

---

