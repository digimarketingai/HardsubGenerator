# ==============================================================================
# Whisper Auto-Subtitler and Translator for Google Colab
#
# To run this script in Google Colab:
# 1. Open a new notebook at https://colab.research.google.com.
# 2. Ensure the runtime has a GPU (Runtime -> Change runtime type -> T4 GPU).
# 3. Copy the entire content of this file into a single cell in the notebook.
# 4. Run the cell.
# 5. Follow the prompts to upload your video and configure the settings.
#
# This script is designed to be run as a standalone .py file or pasted into
# a notebook. It uses pure Python functions instead of notebook "magic commands"
# like `!pip` or `!rm`.
# ==============================================================================

def main():
    """
    Main function to run the entire subtitling and translation pipeline.
    """
    # ==========================================
    # 0. 安裝必要套件 / Install dependencies
    # ==========================================
    print("⏳ Installing dependencies...")
    # Use subprocess to control output and ensure quiet installation
    import subprocess
    import sys
    
    # This is the Python equivalent of: !pip install -q ...
    install_process = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-q', 'git+https://github.com/openai/whisper.git', 'googletrans==4.0.0-rc1'],
        capture_output=True, text=True
    )
    if install_process.returncode != 0:
        print("❌ Failed to install dependencies.")
        print(install_process.stderr)
        return
    print("✅ Dependencies installed.")

    # ==========================================
    # 1. 匯入函式庫與準備目錄 / Import libraries and Prepare directories
    # ==========================================
    import os
    import json
    from pathlib import Path
    import shlex
    import torch
    import whisper
    from googletrans import Translator
    from google.colab import files
    from IPython.display import Audio, display

    CWD = Path(".").resolve()
    UPLOAD_DIR = CWD / "uploads"
    OUT_DIR    = CWD / "transcripts"
    FONT_DIR   = CWD / "fonts"

    for d in (UPLOAD_DIR, OUT_DIR, FONT_DIR):
        d.mkdir(exist_ok=True)

    print("\n工作目錄 / Working dir:", CWD)

    # ==========================================
    # 2. 下載字型（Noto Sans CJK） / Download font
    # ==========================================
    FONT_PATH = FONT_DIR / "NotoSansSC-Regular.otf"
    if not FONT_PATH.exists():
        print("\n⏳ 下載字型 Noto Sans CJK ... / Downloading Noto Sans CJK ...")
        font_url = "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.otf"
        # This is the Python equivalent of: !wget ...
        font_process = subprocess.run(['wget', '-q', '-O', str(FONT_PATH), font_url], capture_output=True)
        if font_process.returncode != 0 or not FONT_PATH.exists():
            print("❌ 字型下載失敗，請重跑 cell 再試。/ Font download failed, rerun the cell.")
            return
    print("✅ 使用字型 / Using font:", FONT_PATH)

    # ==========================================
    # 3. 上傳影片檔 / Upload video
    # ==========================================
    # This is the Python equivalent of: !rm -rf {UPLOAD_DIR}/*
    # It cleans up previous uploads to avoid confusion.
    for item in UPLOAD_DIR.glob('*'):
        if item.is_file():
            item.unlink()
        
    print("\n🎬 請上傳要處理的影片檔（mp4, mkv, mov 等）")
    print("Please upload the video file you want to process.")
    uploaded = files.upload()
    if not uploaded:
        print("❌ 未上傳任何檔案 / No file uploaded.")
        return

    up_name = list(uploaded.keys())[0]
    video_path = UPLOAD_DIR / up_name
    # Move the file from the root Colab directory to our upload directory
    Path(up_name).rename(video_path)

    if not video_path.exists():
        print("❌ 影片檔不存在，請重試上傳。/ Video file does not exist; please re-upload.")
        return
    print(f"\n✅ 影片上傳成功 / Video uploaded successfully: {video_path}")

    # ==========================================
    # 4. & 7. Whisper 模型與翻譯語言選擇 / Model and Language Selection
    # ==========================================
    print("\n⚙️ 選擇 Whisper 模型大小 (tiny / base / small / medium / large)")
    model_name = input("模型大小 [預設 small]: ").strip() or "small"

    print("\n🌐 選擇翻譯語言代碼（en, zh-TW, zh-CN, ja, fr, es, de ...）")
    target_lang = input("翻譯目標語言 [預設 en]: ").strip() or "en"
    print(f"翻譯字幕語言 / Subtitle language: {target_lang}")

    # ==========================================
    # 載入 Whisper 模型 / Load Model
    # ==========================================
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n⏳ 載入 Whisper 模型 {model_name} 在 {device} / Loading model {model_name} on {device} ...")
    model = whisper.load_model(model_name, device=device)
    print("✅ 模型已載入 / Model loaded.\n")

    # ==========================================
    # 5. 抽取音訊 / Extract audio
    # ==========================================
    audio_path = UPLOAD_DIR / f"{video_path.stem}.m4a"
    print("⏳ 從影片抽取音訊 ... / Extracting audio from video ...")
    cmd_audio = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "aac", "-b:a", "192k", str(audio_path)]
    audio_proc = subprocess.run(cmd_audio, check=True, capture_output=True, text=True)
    if audio_proc.returncode != 0:
        print("❌ 抽取音訊失敗 / Failed to extract audio.")
        print(audio_proc.stderr)
        return
    print("✅ 音訊檔案 / Audio file:", audio_path)
    display(Audio(filename=str(audio_path)))

    # ==========================================
    # 6. Whisper 轉錄 / Transcribe
    # ==========================================
    print("\n⏳ 使用 Whisper 轉錄（自動偵測語言） / Transcribing with auto language detection ...")
    result = model.transcribe(str(audio_path), task="transcribe", verbose=False)
    language = result.get("language", "unknown")
    segments = result.get("segments", [])
    full_text = result.get("text", "")
    print("✅ 偵測語言 / Detected language:", language)
    if not segments:
        print("❌ Whisper 沒有產生任何段落 / No segments from Whisper.")
        return

    # ==========================================
    # 8. 翻譯字幕段落 / Translate segments
    # ==========================================
    print("\n⏳ 開始翻譯字幕 ... / Translating segments ...")
    translator = Translator()
    translated_segments = []
    for i, seg in enumerate(segments):
        orig = seg.get("text", "").strip()
        t_txt = ""
        if orig:
            try:
                t = translator.translate(orig, dest=target_lang)
                t_txt = t.text
            except Exception as e:
                print(f"\n  - 翻譯失敗，改用原文 / Translation failed, using original: {e}")
                t_txt = orig
        ns = seg.copy()
        ns["translated_text"] = t_txt
        translated_segments.append(ns)
        print(f"\r  - Translated segment {i+1}/{len(segments)}", end="", flush=True)
    print("\n✅ 翻譯完成 / Translation complete.")

    # ==========================================
    # 9. 儲存逐字稿 / Save transcripts
    # ==========================================
    base = video_path.stem
    txt_orig = OUT_DIR / f"{base}_original.txt"
    txt_tr = OUT_DIR / f"{base}_translated_{target_lang}.txt"
    txt_orig.write_text(full_text, encoding="utf-8")
    txt_tr.write_text("\n".join(s["translated_text"] for s in translated_segments), encoding="utf-8")
    print("\n✅ 文字稿已儲存 / Transcripts saved.")

    # ==========================================
    # 10. 建立 filter_complex 字串 / Build filter_complex string
    # ==========================================
    print("\n⏳ 建立 drawtext 濾鏡字串 ... / Building drawtext filter string ...")
    probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(video_path)]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    vh = info["streams"][0]["height"]
    font_size = max(24, int(vh * 0.05))
    fontfile_str = str(FONT_PATH).replace(":", "\\:")

    filter_parts = []
    input_label = "[0:v]"
    for idx, seg in enumerate(translated_segments):
        txt = seg.get("translated_text", "").strip()
        if not txt: continue
        start, end = seg.get("start", 0.0), seg.get("end", 0.0) + 0.05
        safe_text = txt.replace("\\", "\\\\").replace("'", "’").replace(":", "\\:").replace(",", "\\,").replace("%", "%%")
        output_label = f"[v{idx+1}]"
        draw = (f"{input_label}drawtext=fontfile='{fontfile_str}':text='{safe_text}':fontsize={font_size}:"
                f"fontcolor=white:bordercolor=black:borderw=2.5:x=(w-text_w)/2:y=h-1.5*text_h:"
                f"enable='between(t,{start},{end})'{output_label}")
        filter_parts.append(draw)
        input_label = output_label

    if not filter_parts:
        print("❌ 沒有任何字幕內容可以畫 / No subtitle lines to render.")
        return
    vf_filter = "; ".join(filter_parts)

    # ==========================================
    # 11. ffmpeg -filter_complex 硬燒字幕 / Burn subtitles
    # ==========================================
    out_mp4 = OUT_DIR / f"{base}_sub_{target_lang}.mp4"
    cmd_burn = ["ffmpeg", "-y", "-i", str(video_path), "-filter_complex", vf_filter, "-map", input_label,
                "-map", "0:a?", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "copy", str(out_mp4)]

    print("\n🔥 執行 ffmpeg 硬燒字幕... / Running ffmpeg to burn subtitles...")
    print("   This may take a long time. Please be patient.")
    proc = subprocess.run(cmd_burn, capture_output=True, text=True)

    if proc.returncode == 0:
        print(f"\n\n✅ 成功產生含字幕影片 / Subtitled video created successfully!")
        print(f"   檔案路徑 / File path: {out_mp4}")
        print("\n💾 準備下載檔案... / Preparing to download file...")
        files.download(str(out_mp4))
    else:
        print("\n\n❌ 產生含字幕影片失敗 / Failed to create subtitled video.")
        print("   請把下面 ffmpeg 輸出全部貼給我，我幫你看錯誤原因。")
        print("   Please copy the entire ffmpeg output below and show me, I will help diagnose the error.")
        print("\n=== ffmpeg stdout ===")
        print(proc.stdout)
        print("\n=== ffmpeg stderr ===")
        print(proc.stderr)

# ==========================================
# 執行主程式 / Run main function
# ==========================================
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\n❌ An unexpected error occurred: {e}")
        traceback.print_exc()
