#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
whisper_gradio_tool.py

Gradio-based UI for:
1. Uploading a video (mp4, mkv, mov, etc.)
2. Transcribing with OpenAI Whisper
3. Translating subtitles with googletrans
4. Burning translated subtitles into the video with ffmpeg drawtext
5. Returning:
   - Subtitled MP4
   - Original transcript .txt
   - Translated transcript .txt
   - Log text output

Run (e.g. in Colab):
    !python whisper_gradio_tool.py
"""

import sys
import json
import subprocess
import shlex
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# ----------------------------
# 0. Dependencies & utilities
# ----------------------------
def run_cmd(cmd, check=True, capture_output=True, text=True):
    """Helper to run subprocess commands with basic error handling."""
    return subprocess.run(cmd, check=check, capture_output=capture_output, text=text)


def ensure_pip_package(pkg_spec: str):
    """
    Install a Python package with pip if it's not available.
    pkg_spec can be 'whisper' or 'git+https://github.com/openai/whisper.git', etc.
    """
    try:
        if "git+" not in pkg_spec and "==" in pkg_spec:
            mod_name = pkg_spec.split("==", 1)[0]
        elif "git+" not in pkg_spec and "[" not in pkg_spec and "<" not in pkg_spec and ">" not in pkg_spec:
            mod_name = pkg_spec
        else:
            mod_name = None

        if mod_name:
            __import__(mod_name)
            return
    except ImportError:
        pass

    print(f"Installing pip package: {pkg_spec} ...")
    cmd = [sys.executable, "-m", "pip", "install", "-q", pkg_spec]
    run_cmd(cmd, check=True, capture_output=False, text=False)
    print(f"Installed: {pkg_spec}")


def ensure_dependencies():
    """Install or import all necessary dependencies."""
    ensure_pip_package("git+https://github.com/openai/whisper.git")
    ensure_pip_package("googletrans==4.0.0-rc1")
    ensure_pip_package("gradio==4.44.0")  # version can be adjusted

    global torch, whisper, Translator, gr
    import torch  # type: ignore
    import whisper  # type: ignore
    from googletrans import Translator  # type: ignore
    import gradio as gr  # type: ignore


# ----------------------------
# 1. Prepare directories
# ----------------------------
BASE_DIR = Path(".").resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
OUT_DIR = BASE_DIR / "transcripts"
FONT_DIR = BASE_DIR / "fonts"

for d in (UPLOAD_DIR, OUT_DIR, FONT_DIR):
    d.mkdir(exist_ok=True)

print("工作目錄 / Working dir:", BASE_DIR)


# ----------------------------
# 2. Font download / setup
# ----------------------------
def ensure_font(font_dir: Path) -> Path:
    """
    Automatically download NotoSansCJK-Regular.ttc from the given ZIP URL
    and place it under fonts/ as NotoSansCJK-Regular.ttc.
    """
    font_path = font_dir / "NotoSansCJK-Regular.ttc"
    if font_path.exists():
        print("使用已存在字型 / Using existing font:", font_path)
        return font_path

    print("下載字型 Noto Sans CJK ... / Downloading Noto Sans CJK ...")

    import urllib.request
    import zipfile
    from io import BytesIO

    url = "https://noto-website-2.storage.googleapis.com/pkgs/NotoSansCJK-Regular.ttc.zip"

    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
    except Exception as e:
        raise SystemExit(
            f"字型下載失敗 / Font download failed: {e}\n"
            "請確認網路連線後再試。/ Please check your network and retry."
        )

    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            ttc_names = [n for n in zf.namelist() if n.lower().endswith(".ttc")]
            if not ttc_names:
                raise SystemExit("ZIP 中找不到 .ttc 字型檔 / No .ttc font in ZIP.")
            ttc_name = ttc_names[0]
            print("從 ZIP 取出字型 / Extracting font from ZIP:", ttc_name)
            zf.extract(ttc_name, path=font_dir)
            extracted_path = font_dir / ttc_name
            extracted_path.rename(font_path)
    except Exception as e:
        raise SystemExit(
            f"解壓字型失敗 / Failed to unzip font: {e}\n"
            "請檢查 ZIP 檔或重試。"
        )

    if not font_path.exists():
        raise SystemExit("字型安裝失敗 / Font installation failed.")

    print("使用字型 / Using font:", font_path)
    return font_path


FONT_PATH = ensure_font(FONT_DIR)


# ----------------------------
# 3. Core processing function
# ----------------------------
def process_video(
    video_file,
    model_name="small",
    target_lang="en",
):
    """
    Gradio callback:
    - video_file: temp file object from Gradio
    - model_name: Whisper model size
    - target_lang: translation target language (e.g. 'en', 'zh-TW', etc.)

    Returns:
        (subtitled_video, original_txt, translated_txt, log_text)
    """
    logs = []
    def log(*args):
        msg = " ".join(str(a) for a in args)
        print(msg)
        logs.append(msg)

    if video_file is None:
        return None, None, None, "請先上傳影片 / Please upload a video first."

    # Ensure dependencies imported (once)
    ensure_dependencies()
    global torch, whisper, Translator, gr  # imported above

    # Save uploaded file to UPLOAD_DIR with a sane name
    # video_file is a tempfile path-like object (Gradio)
    temp_src = Path(video_file.name)
    # Build a new unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = temp_src.suffix or ".mp4"
    base_name = f"upload_{timestamp}{ext}"
    dst = UPLOAD_DIR / base_name
    shutil.copy2(temp_src, dst)

    video_path = dst
    log("影片已儲存 / Video saved:", video_path)

    # 3.1 Load Whisper model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"載入 Whisper 模型 {model_name} 在 {device} / Loading model on {device} ...")
    try:
        model = whisper.load_model(model_name, device=device)
    except Exception as e:
        log("載入模型失敗 / Failed to load model:", e)
        return None, None, None, "\n".join(logs)

    # 3.2 Extract audio with ffmpeg
    audio_path = UPLOAD_DIR / f"{video_path.stem}.m4a"
    if not audio_path.exists():
        log("從影片抽取音訊 ... / Extracting audio from video ...")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "aac",
            "-b:a", "192k",
            str(audio_path),
        ]
        try:
            proc = run_cmd(cmd, check=True, capture_output=True, text=True)
            log(proc.stderr)
        except subprocess.CalledProcessError as e:
            log("ffmpeg error (audio extraction):")
            log(e.stderr)
            return None, None, None, "\n".join(logs)

    if not audio_path.exists():
        log("抽取音訊失敗 / Failed to extract audio.")
        return None, None, None, "\n".join(logs)

    log("音訊檔案 / Audio file:", audio_path)

    # 3.3 Transcribe with Whisper
    log("使用 Whisper 轉錄（自動偵測語言） / Transcribing with auto language detection ...")
    try:
        result = model.transcribe(str(audio_path), task="transcribe", verbose=False)
    except Exception as e:
        log("Whisper 轉錄失敗 / Transcription failed:", e)
        return None, None, None, "\n".join(logs)

    language = result.get("language", "unknown")
    segments = result.get("segments", [])
    full_text = result.get("text", "")

    log("偵測語言 / Detected language:", language)
    preview_src = full_text[:300] + ("..." if len(full_text) > 300 else "")
    log("原文前 300 字 / First 300 chars of source:")
    log(preview_src)

    if not segments:
        log("Whisper 沒有產生任何段落 / No segments from Whisper.")
        return None, None, None, "\n".join(logs)

    # 3.4 Translate segments
    target_lang = target_lang.strip() or "en"
    log("翻譯字幕語言 / Subtitle language:", target_lang)

    translator = Translator()
    translated_segments = []

    log("開始翻譯字幕 ... / Translating segments ...")
    for seg in segments:
        orig = seg.get("text", "").strip()
        if not orig:
            t_txt = ""
        else:
            try:
                t = translator.translate(orig, dest=target_lang)
                t_txt = t.text
            except Exception as e:
                log("翻譯失敗，改用原文 / Translation failed, using original:", e)
                t_txt = orig

        ns = dict(seg)
        ns["translated_text"] = t_txt
        translated_segments.append(ns)

    full_translated_text = "\n".join(s["translated_text"] for s in translated_segments)
    preview_tr = full_translated_text[:300] + ("..." if len(full_translated_text) > 300 else "")
    log("翻譯前 300 字 / First 300 chars of translation:")
    log(preview_tr)

    # 3.5 Save transcripts
    base = video_path.stem
    txt_orig = OUT_DIR / f"{base}_original.txt"
    txt_tr = OUT_DIR / f"{base}_translated_{target_lang}.txt"

    txt_orig.write_text(full_text, encoding="utf-8")
    txt_tr.write_text(full_translated_text, encoding="utf-8")

    log("文字稿已儲存 / Transcripts saved:")
    log("  ", txt_orig)
    log("  ", txt_tr)

    # 3.6 Build drawtext filter
    log("建立 drawtext 濾鏡字串 ... / Building drawtext filter string ...")

    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video_path),
    ]
    try:
        probe = run_cmd(probe_cmd, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log("ffprobe error:")
        log(e.stderr)
        return None, str(txt_orig), str(txt_tr), "\n".join(logs)

    info = json.loads(probe.stdout)
    vw = info["streams"][0]["width"]
    vh = info["streams"][0]["height"]
    font_size = max(24, int(vh * 0.05))  # Slightly larger for readability

    log(f"影片解析度 / Video resolution: {vw}x{vh}, 字體大小 / font size: {font_size}")

    fontfile_str = str(FONT_PATH)

    filter_parts = []
    input_label = "[0:v]"
    idx = 0

    for seg in translated_segments:
        txt = seg.get("translated_text", "").strip()
        if not txt:
            continue

        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 1.0))
        end = end + 0.05

        safe_text = (
            txt.replace("\\", "\\\\")
               .replace("'", "’")
               .replace(":", "\\:")
               .replace(",", "\\,")
               .replace("%", "%%")
        )

        output_label = f"[v{idx+1}]"

        draw = (
            f"{input_label}drawtext=fontfile='{fontfile_str}':"
            f"text='{safe_text}':"
            f"fontsize={font_size}:"
            f"fontcolor=white:bordercolor=black:borderw=2:"
            f"x=(w-text_w)/2:y=h-1.5*text_h:"
            f"enable='between(t,{start},{end})'{output_label}"
        )

        filter_parts.append(draw)
        input_label = output_label
        idx += 1

    if idx == 0:
        log("沒有任何字幕內容可以畫 / No subtitle lines to render.")
        return None, str(txt_orig), str(txt_tr), "\n".join(logs)

    vf_filter = "; ".join(filter_parts)
    output_label = input_label

    log("濾鏡字串前 600 字 / Filter string first 600 chars:")
    preview_filter = vf_filter[:600] + ("..." if len(vf_filter) > 600 else "")
    log(preview_filter)

    # 3.7 ffmpeg burn subtitles
    out_mp4 = OUT_DIR / f"{base}_sub_{target_lang}_drawtext.mp4"

    cmd_burn = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-filter_complex", vf_filter,
        "-map", output_label,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "copy",
        str(out_mp4),
    ]

    log("執行 ffmpeg 硬燒字幕 / Running ffmpeg to burn subtitles ...")
    log("Command (shell escaped):")
    log(" ".join(shlex.quote(c) for c in cmd_burn))
    log("=== ffmpeg output ===")

    proc = run_cmd(cmd_burn, check=False, capture_output=True, text=True)

    if proc.returncode == 0:
        log(proc.stderr)
        log("✅ 成功產生含字幕影片 / Subtitled video created:")
        log("  ", out_mp4)
        subtitled_video = str(out_mp4)
    else:
        log("=== ffmpeg stdout ===")
        log(proc.stdout)
        log("=== ffmpeg stderr ===")
        log(proc.stderr)
        log("ffmpeg return code:", proc.returncode)
        log("❌ 產生含字幕影片失敗 / Failed to create subtitled video.")
        subtitled_video = None

    # Gradio expects actual file paths or file-like objects
    return (
        subtitled_video,
        str(txt_orig),
        str(txt_tr),
        "\n".join(logs),
    )


# ----------------------------
# 4. Gradio interface
# ----------------------------
def launch_gradio():
    ensure_dependencies()
    global gr

    with gr.Blocks(title="Whisper Subtitle Tool (Gradio)") as demo:
        gr.Markdown(
            """
# Whisper Subtitle Tool (Gradio)

1. 上傳影片檔（mp4, mkv, mov 等）  
2. 選擇 Whisper 模型與翻譯語言  
3. 點擊「Start」開始轉錄 + 翻譯 + 硬燒字幕  

輸出：  
- 含字幕影片 (MP4)  
- 原文文字稿 (.txt)  
- 翻譯文字稿 (.txt)  
- 日誌訊息 (log)
"""
        )

        with gr.Row():
            video_input = gr.Video(
                label="影片上傳 / Video upload",
                sources=["upload"],
                format="mp4",
                interactive=True,
            )

        with gr.Row():
            model_dropdown = gr.Dropdown(
                label="Whisper 模型大小 / Model size",
                choices=["tiny", "base", "small", "medium", "large"],
                value="small",
            )
            target_lang_text = gr.Textbox(
                label="翻譯目標語言代碼 / Target language code (e.g. en, zh-TW, ja)",
                value="en",
            )

        start_button = gr.Button("Start", variant="primary")

        with gr.Row():
            video_output = gr.Video(
                label="含字幕影片 / Subtitled video",
            )

        with gr.Row():
            orig_txt_output = gr.File(label="原文文字稿 / Original transcript (.txt)")
            tr_txt_output = gr.File(label="翻譯文字稿 / Translated transcript (.txt)")

        log_output = gr.Textbox(
            label="日誌 / Logs",
            lines=20,
            interactive=False,
        )

        start_button.click(
            fn=process_video,
            inputs=[video_input, model_dropdown, target_lang_text],
            outputs=[video_output, orig_txt_output, tr_txt_output, log_output],
        )

    # In Colab: share=True to get a public link
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)


if __name__ == "__main__":
    launch_gradio()
