#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
whisper_subtitle_tool.py

Transcribe a video with OpenAI Whisper, translate subtitles with googletrans,
and burn translated subtitles into the video using ffmpeg drawtext.

Usage (in Google Colab):
    !python whisper_subtitle_tool.py

Usage (local shell):
    python whisper_subtitle_tool.py
"""

import os
import sys
import json
import subprocess
import shlex
from pathlib import Path

# ------------------------------------------
# 0. Utility: environment & dependencies
# ------------------------------------------
def in_colab() -> bool:
    """Detect if running inside Google Colab."""
    try:
        import google.colab  # type: ignore
        return True
    except Exception:
        return False


def run_cmd(cmd, check=True, capture_output=True, text=True):
    """Helper to run subprocess commands with basic error handling."""
    return subprocess.run(cmd, check=check, capture_output=capture_output, text=text)


def ensure_pip_package(pkg_spec: str):
    """
    Install a Python package with pip if it's not available.
    pkg_spec can be 'whisper' or 'git+https://github.com/openai/whisper.git', etc.
    """
    try:
        # Try importing by module name, if it looks like that
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
    # Whisper from GitHub (same as your cell)
    ensure_pip_package("git+https://github.com/openai/whisper.git")
    # googletrans
    ensure_pip_package("googletrans==4.0.0-rc1")

    # Now import them
    global torch, whisper, Translator
    import torch  # type: ignore
    import whisper  # type: ignore
    from googletrans import Translator  # type: ignore


# ------------------------------------------
# 1. Prepare directories
# ------------------------------------------
def prepare_directories():
    cwd = Path(".").resolve()
    upload_dir = cwd / "uploads"
    out_dir = cwd / "transcripts"
    font_dir = cwd / "fonts"
    for d in (upload_dir, out_dir, font_dir):
        d.mkdir(exist_ok=True)
    print("工作目錄 / Working dir:", cwd)
    return cwd, upload_dir, out_dir, font_dir


# ------------------------------------------
# 2. Download & install font (auto, from your URL)
# ------------------------------------------
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
        # Download zip into memory
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
    except Exception as e:
        raise SystemExit(
            f"字型下載失敗 / Font download failed: {e}\n"
            "請確認網路連線後再試。/ Please check your network and retry."
        )

    # Unzip and extract .ttc
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            # Find first .ttc inside zip
            ttc_names = [n for n in zf.namelist() if n.lower().endswith(".ttc")]
            if not ttc_names:
                raise SystemExit("ZIP 中找不到 .ttc 字型檔 / No .ttc font in ZIP.")
            # Use the first .ttc
            ttc_name = ttc_names[0]
            print("從 ZIP 取出字型 / Extracting font from ZIP:", ttc_name)
            zf.extract(ttc_name, path=font_dir)
            extracted_path = font_dir / ttc_name
            # Move / rename to NotoSansCJK-Regular.ttc at root of fonts/
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


# ------------------------------------------
# 3. Get video file (Colab upload or local path)
# ------------------------------------------
def get_video_file(upload_dir: Path) -> Path:
    if in_colab():
        # Colab: use upload widget
        from google.colab import files  # type: ignore

        print("\n請上傳要處理的影片檔（mp4, mkv, mov 等） / "
              "Please upload the video file (mp4, mkv, mov, etc.)")
        uploaded = files.upload()
        if not uploaded:
            raise SystemExit("未上傳任何檔案 / No file uploaded.")

        up_name = list(uploaded.keys())[0]
        tmp_path = Path(up_name)
        video_path = upload_dir / up_name
        if tmp_path.exists():
            tmp_path.rename(video_path)
    else:
        # Non-Colab: ask user for a path
        print("\n請輸入要處理的影片檔路徑（mp4, mkv, mov 等） / "
              "Please enter the video file path (mp4, mkv, mov, etc.)")
        path_str = input("影片檔路徑 / Video path: ").strip()
        if not path_str:
            raise SystemExit("未提供路徑 / No path provided.")
        src = Path(path_str).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"找不到影片檔 / Video not found: {src}")
        # Copy or use directly
        video_path = upload_dir / src.name
        if src != video_path:
            import shutil
            shutil.copy2(src, video_path)

    if not video_path.exists():
        raise SystemExit(
            "影片檔不存在，請重試上傳或檢查路徑。/ "
            "Video file does not exist; please re-upload or check path."
        )

    print("影片路徑 / Video path:", video_path)
    return video_path


# ------------------------------------------
# 4. Load Whisper model
# ------------------------------------------
def load_whisper_model():
    print("\n選擇 Whisper 模型大小 (tiny / base / small / medium / large)")
    model_name = input("模型大小 [預設 small]: ").strip() or "small"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"載入 Whisper 模型 {model_name} 在 {device} / "
          f"Loading model {model_name} on {device} ...")
    model = whisper.load_model(model_name, device=device)
    print("模型已載入 / Model loaded.\n")
    return model


# ------------------------------------------
# 5. Extract audio with ffmpeg
# ------------------------------------------
def extract_audio(video_path: Path, upload_dir: Path) -> Path:
    audio_path = upload_dir / f"{video_path.stem}.m4a"
    if not audio_path.exists():
        print("從影片抽取音訊 ... / Extracting audio from video ...")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "aac",
            "-b:a", "192k",
            str(audio_path),
        ]
        try:
            run_cmd(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print("ffmpeg error (audio extraction):")
            print(e.stderr)
            raise SystemExit("抽取音訊失敗 / Failed to extract audio.")

    if not audio_path.exists():
        raise SystemExit("抽取音訊失敗 / Failed to extract audio.")

    print("音訊檔案 / Audio file:", audio_path)

    # In Colab you can optionally play it, but script will continue either way
    if in_colab():
        try:
            from IPython.display import Audio, display  # type: ignore
            display(Audio(filename=str(audio_path)))
        except Exception:
            pass

    return audio_path


# ------------------------------------------
# 6. Whisper transcription
# ------------------------------------------
def transcribe_audio(model, audio_path: Path):
    print("\n使用 Whisper 轉錄（自動偵測語言） / "
          "Transcribing with auto language detection ...")
    result = model.transcribe(str(audio_path), task="transcribe", verbose=False)

    language = result.get("language", "unknown")
    segments = result.get("segments", [])
    full_text = result.get("text", "")

    print("偵測語言 / Detected language:", language)
    print("\n原文前 300 字 / First 300 chars of source:")
    preview = full_text[:300] + ("..." if len(full_text) > 300 else "")
    print(preview)

    if not segments:
        raise SystemExit("Whisper 沒有產生任何段落 / No segments from Whisper.")

    return language, segments, full_text


# ------------------------------------------
# 7 & 8. Choose target language & translate segments
# ------------------------------------------
def translate_segments(segments, default_lang="en"):
    print("\n選擇翻譯語言代碼（en, zh-TW, zh-CN, ja, fr, es, de ...）")
    target_lang = input(f"翻譯目標語言 [預設 {default_lang}]: ").strip() or default_lang
    print("翻譯字幕語言 / Subtitle language:", target_lang)

    print("\n開始翻譯字幕 ... / Translating segments ...")

    translator = Translator()
    translated_segments = []

    for seg in segments:
        orig = seg.get("text", "").strip()
        if not orig:
            t_txt = ""
        else:
            try:
                t = translator.translate(orig, dest=target_lang)
                t_txt = t.text
            except Exception as e:
                print("翻譯失敗，改用原文 / Translation failed, using original:", e)
                t_txt = orig

        ns = dict(seg)
        ns["translated_text"] = t_txt
        translated_segments.append(ns)

    full_translated_text = "\n".join(s["translated_text"] for s in translated_segments)

    print("\n翻譯前 300 字 / First 300 chars of translation:")
    preview = full_translated_text[:300] + ("..." if len(full_translated_text) > 300 else "")
    print(preview)

    return target_lang, translated_segments, full_translated_text


# ------------------------------------------
# 9. Save transcripts
# ------------------------------------------
def save_transcripts(
    video_path: Path,
    out_dir: Path,
    full_text: str,
    full_translated_text: str,
    target_lang: str,
):
    base = video_path.stem
    txt_orig = out_dir / f"{base}_original.txt"
    txt_tr = out_dir / f"{base}_translated_{target_lang}.txt"

    txt_orig.write_text(full_text, encoding="utf-8")
    txt_tr.write_text(full_translated_text, encoding="utf-8")

    print("\n文字稿已儲存 / Transcripts saved:")
    print("  ", txt_orig)
    print("  ", txt_tr)

    return txt_orig, txt_tr


# ------------------------------------------
# 10. Build ffmpeg drawtext filter_complex
# ------------------------------------------
def build_drawtext_filter(
    video_path: Path,
    translated_segments,
    font_path: Path,
):
    print("\n建立 drawtext 濾鏡字串 ... / Building drawtext filter string ...")

    # Probe video resolution
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
        print("ffprobe error:")
        print(e.stderr)
        raise SystemExit("無法讀取影片解析度 / Failed to get video resolution.")

    info = json.loads(probe.stdout)
    vw = info["streams"][0]["width"]
    vh = info["streams"][0]["height"]
    font_size = max(24, int(vh * 0.05))  # Slightly larger for readability

    print(f"影片解析度 / Video resolution: {vw}x{vh}, 字體大小 / font size: {font_size}")

    fontfile_str = str(font_path)

    filter_parts = []
    input_label = "[0:v]"
    idx = 0

    for seg in translated_segments:
        txt = seg.get("translated_text", "").strip()
        if not txt:
            continue

        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 1.0))
        end = end + 0.05  # small buffer

        # Escape text for ffmpeg drawtext
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
        raise SystemExit("沒有任何字幕內容可以畫 / No subtitle lines to render.")

    vf_filter = "; ".join(filter_parts)
    output_label = input_label

    print("\n濾鏡字串前 1000 字 / Filter string first 1000 chars:")
    preview = vf_filter[:1000] + ("..." if len(vf_filter) > 1000 else "")
    print(preview)

    return vf_filter, output_label


# ------------------------------------------
# 11. Run ffmpeg to burn subtitles
# ------------------------------------------
def burn_subtitles(
    video_path: Path,
    out_dir: Path,
    vf_filter: str,
    output_label: str,
    target_lang: str,
):
    base = video_path.stem
    out_mp4 = out_dir / f"{base}_sub_{target_lang}_drawtext.mp4"

    cmd_burn = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-filter_complex", vf_filter,
        "-map", output_label,     # last video label
        "-map", "0:a?",           # original audio if exists
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "copy",
        str(out_mp4),
    ]

    print("\n執行 ffmpeg 硬燒字幕 / Running ffmpeg to burn subtitles ...")
    print("Command (shell escaped):")
    print(" ", " ".join(shlex.quote(c) for c in cmd_burn))
    print("\n=== ffmpeg output ===\n")

    proc = run_cmd(cmd_burn, check=False, capture_output=True, text=True)

    if proc.returncode == 0:
        print(proc.stderr)
        print("\n✅ 成功產生含字幕影片 / Subtitled video created:")
        print("  ", out_mp4)
        if in_colab():
            print("\n請在左側 Files 面板展開 transcripts/，下載該 mp4。")
    else:
        print("=== ffmpeg stdout ===")
        print(proc.stdout)
        print("\n=== ffmpeg stderr ===")
        print(proc.stderr)
        print("ffmpeg return code:", proc.returncode)
        print("\n❌ 產生含字幕影片失敗 / Failed to create subtitled video.")
        print("請把上面 ffmpeg 輸出全部貼給我，我幫你看錯誤原因。")

    return out_mp4 if proc.returncode == 0 else None


# ------------------------------------------
# Main
# ------------------------------------------
def main():
    ensure_dependencies()

    global torch, whisper, Translator  # imported in ensure_dependencies

    cwd, upload_dir, out_dir, font_dir = prepare_directories()
    font_path = ensure_font(font_dir)  # <-- auto download + install from your URL

    video_path = get_video_file(upload_dir)

    model = load_whisper_model()

    audio_path = extract_audio(video_path, upload_dir)

    language, segments, full_text = transcribe_audio(model, audio_path)

    target_lang, translated_segments, full_translated_text = translate_segments(
        segments
    )

    save_transcripts(
        video_path,
        out_dir,
        full_text,
        full_translated_text,
        target_lang,
    )

    vf_filter, output_label = build_drawtext_filter(
        video_path, translated_segments, font_path
    )

    burn_subtitles(
        video_path,
        out_dir,
        vf_filter,
        output_label,
        target_lang,
    )


if __name__ == "__main__":
    main()
