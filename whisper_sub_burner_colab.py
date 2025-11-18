# ==========================================
# 0. 安裝必要套件 / Install dependencies
# ==========================================
import os
import json
from pathlib import Path
import subprocess
import shlex

import torch
import whisper
from googletrans import Translator
from google.colab import files
from IPython.display import Audio, display

# ==========================================
# 1. 準備目錄 / Prepare directories
# ==========================================
CWD = Path(".").resolve()
UPLOAD_DIR = CWD / "uploads"
OUT_DIR    = CWD / "transcripts"
FONT_DIR   = CWD / "fonts"

for d in (UPLOAD_DIR, OUT_DIR, FONT_DIR):
    d.mkdir(exist_ok=True)

print("工作目錄 / Working dir:", CWD)

# ==========================================
# 2. 下載字型（Noto Sans CJK） / Download font
# ==========================================
FONT_PATH = FONT_DIR / "NotoSansCJK-Regular.ttc"
if not FONT_PATH.exists():
    print("下載字型 Noto Sans CJK ... / Downloading Noto Sans CJK ...")
    # Using a more reliable font source from Noto CJK repo
    !wget -q -O "fonts/NotoSansCJK-Regular.ttc" \
      "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.otf"

if not FONT_PATH.exists():
    raise SystemExit("字型下載失敗，請重跑 cell 再試。/ Font download failed, rerun the cell.")

print("使用字型 / Using font:", FONT_PATH)

# ==========================================
# 3. 上傳影片檔 / Upload video
# ==========================================
print("\n請上傳要處理的影片檔（mp4, mkv, mov 等）")
uploaded = files.upload()
if not uploaded:
    raise SystemExit("未上傳任何檔案 / No file uploaded.")

up_name = list(uploaded.keys())[0]
tmp_path = Path(up_name)
video_path = UPLOAD_DIR / up_name
if tmp_path.exists():
    tmp_path.rename(video_path)

if not video_path.exists():
    raise SystemExit("影片檔不存在，請重試上傳。/ Video file does not exist; please re-upload.")

print("影片路徑 / Video path:", video_path)

# ==========================================
# 4. Whisper 模型 / Model
# ==========================================
print("\n選擇 Whisper 模型大小 (tiny / base / small / medium / large)")
model_name = input("模型大小 [預設 small]: ").strip() or "small"

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"載入 Whisper 模型 {model_name} 在 {device} / Loading model {model_name} on {device} ...")
model = whisper.load_model(model_name, device=device)
print("模型已載入 / Model loaded.\n")

# ==========================================
# 5. 抽取音訊 / Extract audio
# ==========================================
audio_path = UPLOAD_DIR / f"{video_path.stem}.m4a"
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
    # capture_output=True 方便 debug
    subprocess.run(cmd, check=True, capture_output=True)

if not audio_path.exists():
    raise SystemExit("抽取音訊失敗 / Failed to extract audio.")

print("音訊檔案 / Audio file:", audio_path)
display(Audio(filename=str(audio_path)))

# ==========================================
# 6. Whisper 轉錄 / Transcribe
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
txt_tr   = OUT_DIR / f"{base}_translated_{target_lang}.txt"

txt_orig.write_text(full_text, encoding="utf-8")
txt_tr.write_text(full_translated_text, encoding="utf-8")

print("\n文字稿已儲存 / Transcripts saved:")
print("  ", txt_orig)
print("  ", txt_tr)

# ==========================================
# 10. 建立 filter_complex 字串（用 label 串接多個 drawtext）
# ==========================================
print("\n建立 drawtext 濾鏡字串 ... / Building drawtext filter string ...")

# 取解析度，算字體大小
probe_cmd = [
    "ffprobe", "-v", "error",
    "-select_streams", "v:0",
    "-show_entries", "stream=width,height",
    "-of", "json",
    str(video_path),
]
probe = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
info = json.loads(probe.stdout)
vw = info["streams"][0]["width"]
vh = info["streams"][0]["height"]
font_size = max(24, int(vh * 0.05))  # Slightly larger for readability

print(f"影片解析度 / Video resolution: {vw}x{vh}, 字體大小 / font size: {font_size}")

# ffmpeg 在 Linux 路徑不用特別 escape ':'，這行對 Colab 其實可省
fontfile_str = str(FONT_PATH)

# ffmpeg filter chain: [0:v] drawtext=... [v1]; [v1] drawtext=... [v2]; ... [last] = output
filter_parts = []
input_label = "[0:v]"  # start from input video
idx = 0

for seg in translated_segments:
    txt = seg.get("translated_text", "").strip()
    if not txt:
        continue

    start = seg.get("start", 0.0)
    end   = seg.get("end", start + 1.0)

    # 為了避免邊界問題，尾端加一點點 buffer
    end = end + 0.05

    # ===== 正確 escape 給 ffmpeg drawtext =====
    # - \  -> \\
    # - '  -> 變成全形 ’，避免破壞單引號包住的字串
    # - :  -> \:
    # - ,  -> \,
    # - %  -> %%
    # ==========================================
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

# 最終輸出 label
output_label = input_label
vf_filter = "; ".join(filter_parts)

print("\n濾鏡字串前 1000 字 / Filter string first 1000 chars:")
print(vf_filter[:1000] + ("..." if len(vf_filter) > 1000 else ""))

# ==========================================
# 11. ffmpeg -filter_complex 硬燒字幕 / Burn subtitles
# ==========================================
out_mp4 = OUT_DIR / f"{base}_sub_{target_lang}_drawtext.mp4"

cmd_burn = [
    "ffmpeg", "-y",
    "-i", str(video_path),
    "-filter_complex", vf_filter,
    "-map", output_label,     # 使用最後的視訊 label
    "-map", "0:a?",           # 原始音訊（如果有）
    "-c:v", "libx264",        # Explicitly set video codec
    "-preset", "fast",        # Faster encoding
    "-crf", "22",             # Good quality/size balance
    "-c:a", "copy",
    str(out_mp4),
]

print("\n執行 ffmpeg 硬燒字幕 / Running ffmpeg to burn subtitles ...")
print("Command (shell escaped):")
print(" ", " ".join(shlex.quote(c) for c in cmd_burn))
print("\n=== ffmpeg output ===\n")

proc = subprocess.run(cmd_burn, capture_output=True, text=True)

if proc.returncode == 0:
    # ffmpeg 進度都在 stderr
    print(proc.stderr)
    print("\n✅ 成功產生含字幕影片 / Subtitled video created:")
    print("  ", out_mp4)
    print("\n請在左側 Files 面板展開 transcripts/，下載該 mp4。")
else:
    print("=== ffmpeg stdout ===")
    print(proc.stdout)
    print("\n=== ffmpeg stderr ===")
    print(proc.stderr)
    print("ffmpeg return code:", proc.returncode)
    print("\n❌ 產生含字幕影片失敗 / Failed to create subtitled video.")
    print("請把上面 ffmpeg 輸出全部貼給我，我幫你看錯誤原因。")
