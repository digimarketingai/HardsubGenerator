# whisper_sub_burner_colab.py
# 專為 Google Colab 設計的版本：使用者可透過上傳按鈕選擇影片檔，
# 然後自動執行：抽取音訊 -> Whisper 轉錄 -> Google 翻譯 -> FFmpeg drawtext 硬燒字幕。

import os
import json
import subprocess
from pathlib import Path

import torch
import whisper
from googletrans import Translator

try:
    from google.colab import files
    from IPython.display import Audio, display
except ImportError:
    raise SystemExit(
        "這個腳本只適用於 Google Colab 環境。\n"
        "This script is intended to run in Google Colab only."
    )

# ==========================================
# 1. 準備目錄 / Prepare directories
# ==========================================
CWD = Path(".").resolve()
UPLOAD_DIR = CWD / "uploads"
OUT_DIR = CWD / "transcripts"
FONT_DIR = CWD / "fonts"

for d in (UPLOAD_DIR, OUT_DIR, FONT_DIR):
    d.mkdir(exist_ok=True)

print("工作目錄 / Working dir:", CWD)

# ==========================================
# 2. 下載字型 Noto Sans / Download font
# ==========================================
FONT_PATH = FONT_DIR / "NotoSans-Regular.ttf"

if not FONT_PATH.exists():
    print("下載字型 Noto Sans ... / Downloading Noto Sans ...")
    font_url = (
        "https://github.com/google/fonts/raw/main/ofl/notosans/"
        "NotoSans-Regular.ttf"
    )
    cmd_font = [
        "wget",
        "-q",
        "-O",
        str(FONT_PATH),
        font_url,
    ]
    proc_font = subprocess.run(cmd_font)
    if proc_font.returncode != 0 or not FONT_PATH.exists():
        raise SystemExit(
            "字型下載失敗，請重新執行本腳本。\n"
            "Font download failed; please rerun this script."
        )

print("使用字型 / Using font:", FONT_PATH)

# ==========================================
# 3. 上傳影片檔（Colab 按鈕） / Upload video via Colab
# ==========================================
print("\n請上傳要處理的影片檔（mp4, mkv, mov 等）")
uploaded = files.upload()
if not uploaded:
    raise SystemExit("未上傳任何檔案 / No file uploaded.")

# 只處理第一個檔案 / Only process the first uploaded file
up_name = list(uploaded.keys())[0]
tmp_path = Path(up_name)
video_path = UPLOAD_DIR / up_name
if tmp_path.exists():
    tmp_path.rename(video_path)

if not video_path.exists():
    raise SystemExit("影片檔不存在，請重試上傳。/ Video file does not exist; please re-upload.")

print("影片路徑 / Video path:", video_path)

# ==========================================
# 4. 載入 Whisper 模型 / Load Whisper model
# ==========================================
print("\n選擇 Whisper 模型大小 (tiny / base / small / medium / large)")
model_name = input("模型大小 [預設 small]: ").strip() or "small"

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"載入 Whisper 模型 {model_name} 在 {device} / Loading model {model_name} on {device} ...")
model = whisper.load_model(model_name, device=device)
print("模型已載入 / Model loaded.\n")

# ==========================================
# 5. 抽取音訊 / Extract audio from video
# ==========================================
audio_path = UPLOAD_DIR / f"{video_path.stem}.m4a"
if not audio_path.exists():
    print("從影片抽取音訊 ... / Extracting audio from video ...")
    cmd_audio = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "aac",
        "-b:a",
        "192k",
        str(audio_path),
    ]
    proc_audio = subprocess.run(cmd_audio, text=True, capture_output=True)
    if proc_audio.returncode != 0:
        print("=== ffmpeg stdout ===")
        print(proc_audio.stdout)
        print("\n=== ffmpeg stderr ===")
        print(proc_audio.stderr)
        raise SystemExit("抽取音訊失敗 / Failed to extract audio.")

if not audio_path.exists():
    raise SystemExit("抽取音訊失敗（無音訊檔）/ Failed to extract audio (file missing).")

print("音訊檔案 / Audio file:", audio_path)
try:
    display(Audio(filename=str(audio_path)))
except Exception as e:
    print("Colab 無法直接播放音訊，略過播放。/ Cannot auto-play audio, skipping.", e)

# ==========================================
# 6. Whisper 轉錄 / Transcribe with Whisper
# ==========================================
print("\n使用 Whisper 轉錄（自動偵測語言） / Transcribing with auto language detection ...")
result = model.transcribe(str(audio_path), task="transcribe", verbose=False)

language = result.get("language", "unknown")
segments = result.get("segments", [])
full_text = result.get("text", "")

print("偵測語言 / Detected language:", language)
print("\n原文前 300 字 / First 300 chars of source:")
print(full_text[:300] + ("..." if len(full_text) > 300 else ""))

if not segments:
    raise SystemExit("Whisper 沒有產生任何段落 / No segments from Whisper.")

# ==========================================
# 7. 選擇翻譯語言 / Choose target language
# ==========================================
print("\n選擇翻譯語言代碼（en, zh-TW, zh-CN, ja, fr, es, de ...）")
target_lang = input("翻譯目標語言 [預設 en]: ").strip() or "en"
print("翻譯字幕語言 / Subtitle language:", target_lang)

# ==========================================
# 8. 翻譯字幕段落 / Translate segments
# ==========================================
print("\n開始翻譯字幕 ... / Translating segments ...")

translator = Translator()
translated_segments = []

for i, seg in enumerate(segments, start=1):
    orig = seg.get("text", "").strip()
    if not orig:
        t_txt = ""
    else:
        try:
            t = translator.translate(orig, dest=target_lang)
            t_txt = t.text
        except Exception as e:
            print(f"[段落 {i}] 翻譯失敗，改用原文 / Translation failed, using original:", e)
            t_txt = orig

    ns = seg.copy()
    ns["translated_text"] = t_txt
    translated_segments.append(ns)

full_translated_text = "\n".join(s["translated_text"] for s in translated_segments)

print("\n翻譯前 300 字 / First 300 chars of translation:")
print(full_translated_text[:300] + ("..." if len(full_translated_text) > 300 else ""))

# ==========================================
# 9. 儲存逐字稿 / Save transcripts
# ==========================================
base = video_path.stem
txt_orig = OUT_DIR / f"{base}_original.txt"
txt_tr = OUT_DIR / f"{base}_translated_{target_lang}.txt"

txt_orig.write_text(full_text, encoding="utf-8")
txt_tr.write_text(full_translated_text, encoding="utf-8")

print("\n文字稿已儲存 / Transcripts saved:")
print("  ", txt_orig)
print("  ", txt_tr)

# ==========================================
# 10. 建立 filter_complex 字串 / Build filter_complex
# ==========================================
print("\n建立 drawtext 濾鏡字串 ... / Building drawtext filter string ...")

# 取得影片解析度 / Get video resolution
probe_cmd = [
    "ffprobe",
    "-v",
    "error",
    "-select_streams",
    "v:0",
    "-show_entries",
    "stream=width,height",
    "-of",
    "json",
    str(video_path),
]
probe = subprocess.run(probe_cmd, capture_output=True, text=True)
if probe.returncode != 0:
    print("=== ffprobe stderr ===")
    print(probe.stderr)
    raise SystemExit("無法取得影片解析度 / Failed to get video resolution.")

info = json.loads(probe.stdout)
vw = info["streams"][0]["width"]
vh = info["streams"][0]["height"]
font_size = max(24, int(vh * 0.05))  # 5% of height

print(f"影片解析度 / Video resolution: {vw}x{vh}, 字體大小 / font size: {font_size}")

fontfile_str = str(FONT_PATH)

# 建立 drawtext 濾鏡鏈 / Build drawtext chain
filter_parts = []
input_label = "[0:v]"
idx = 0

for seg in translated_segments:
    txt = seg.get("translated_text", "").strip()
    if not txt:
        continue

    start = float(seg.get("start", 0.0))
    end = float(seg.get("end", start + 1.0))

    # 稍微延長結束時間，減少閃爍 / Extend end time slightly
    end = end + 0.05

    # 文字跳脫 / Escape for ffmpeg drawtext
    safe_text = (
        txt.replace("\\", "\\\\")
        .replace("'", "’")        # avoid single quote issues
        .replace(":", "\\:")      # ffmpeg syntax
        .replace(",", "\\,")
        .replace("%", "%%")
    )

    output_label = f"[v{idx + 1}]"

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

output_label = input_label
vf_filter = "; ".join(filter_parts)

print("\n濾鏡字串前 1000 字 / Filter string first 1000 chars:")
print(vf_filter[:1000] + ("..." if len(vf_filter) > 1000 else ""))

# ==========================================
# 11. ffmpeg 硬燒字幕 / Burn subtitles with ffmpeg
# ==========================================
out_mp4 = OUT_DIR / f"{base}_sub_{target_lang}_drawtext.mp4"

cmd_burn = [
    "ffmpeg",
    "-y",
    "-i",
    str(video_path),
    "-filter_complex",
    vf_filter,
    "-map",
    output_label,
    "-map",
    "0:a?",
    "-c:v",
    "libx264",
    "-preset",
    "fast",
    "-crf",
    "22",
    "-c:a",
    "copy",
    str(out_mp4),
]

print("\n執行 ffmpeg 硬燒字幕 / Running ffmpeg to burn subtitles ...")
print("Command:")
print(" ", " ".join(cmd_burn))
print("\n=== ffmpeg output ===\n")

proc_burn = subprocess.run(cmd_burn, capture_output=True, text=True)

if proc_burn.returncode == 0:
    # ffmpeg 主要把進度印在 stderr
    print(proc_burn.stderr)
    print("\n✅ 成功產生含字幕影片 / Subtitled video created:")
    print("  ", out_mp4)
    print("\n請在左側 Files 面板展開 transcripts/，右鍵下載該 mp4。")
else:
    print("=== ffmpeg stdout ===")
    print(proc_burn.stdout)
    print("\n=== ffmpeg stderr ===")
    print(proc_burn.stderr)
    print("ffmpeg return code:", proc_burn.returncode)
    print("\n❌ 產生含字幕影片失敗 / Failed to create subtitled video.")
    print("請把上面 ffmpeg 輸出全部貼給我，我幫你看錯誤原因。")
