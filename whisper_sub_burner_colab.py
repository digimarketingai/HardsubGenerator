# ==============================================================================
#      Whisper Auto-Caption and Translation Script for Google Colab
#
# This single script performs the following actions:
# 1. Installs necessary libraries (Whisper, Googletrans).
# 2. Sets up directories and downloads a font for subtitles.
# 3. Prompts the user for the Whisper model size and target translation language.
# 4. Prompts the user to upload a video file.
# 5. Extracts audio from the video using ffmpeg.
# 6. Transcribes the audio to text using OpenAI's Whisper.
# 7. Translates the transcribed text to the specified target language.
# 8. Saves the original and translated transcripts as .txt files.
# 9. Burns the translated subtitles permanently onto the video using ffmpeg.
# 10. Automatically downloads the final subtitled video.
#
# Instructions: Paste this entire script into a single Google Colab cell and run it.
# ==============================================================================

def main():
    # ==========================================
    # 0. 安裝必要套件 / Install dependencies
    # ==========================================
    print("⏳ [Step 0/11] Installing dependencies...")
    # Use -qq for quieter installation
    get_ipython().system('pip install -qq "git+https://github.com/openai/whisper.git" googletrans==4.0.0-rc1')
    print("✅ [Step 0/11] Dependencies installed.")

    # ==========================================
    # 1. 匯入函式庫與準備目錄 / Import libraries and Prepare directories
    # ==========================================
    import os
    import json
    from pathlib import Path
    import subprocess
    import shlex
    import sys

    import torch
    import whisper
    from googletrans import Translator
    from google.colab import files
    from IPython.display import Audio, display

    print("\n⏳ [Step 1/11] Preparing directories...")
    CWD = Path(".").resolve()
    UPLOAD_DIR = CWD / "uploads"
    OUT_DIR    = CWD / "transcripts"
    FONT_DIR   = CWD / "fonts"

    for d in (UPLOAD_DIR, OUT_DIR, FONT_DIR):
        d.mkdir(exist_ok=True)
    
    # Clean up previous runs to avoid confusion
    !rm -rf {UPLOAD_DIR}/*
    !rm -rf {OUT_DIR}/*

    print("✅ [Step 1/11] Directories prepared.")
    print("   - Working dir:", CWD)

    # ==========================================
    # 2. 下載字型（Noto Sans CJK） / Download font
    # ==========================================
    print("\n⏳ [Step 2/11] Downloading font for subtitles...")
    FONT_PATH = FONT_DIR / "NotoSansSC-Regular.otf"
    if not FONT_PATH.exists():
        # Using a reliable font source from Google Fonts repo
        get_ipython().system('wget -q -O "{FONT_PATH}" "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.otf"')

    if not FONT_PATH.exists():
        print("❌ 字型下載失敗，請重跑 cell 再試。/ Font download failed, rerun the cell.")
        return # Exit the function

    print("✅ [Step 2/11] Font ready:", FONT_PATH)

    # ==========================================
    # 3. 選擇 Whisper 模型 / Choose Whisper Model
    # ==========================================
    print("\n➡️ [Step 3/11] Choose a Whisper model size (tiny, base, small, medium, large)")
    print("   - `small` is a good balance of speed and accuracy.")
    model_name = input("Enter model size [default: small]: ").strip() or "small"

    # ==========================================
    # 4. 選擇翻譯語言 / Choose target language
    # ==========================================
    print("\n➡️ [Step 4/11] Choose a target language for translation.")
    print("   - Examples: en (English), zh-TW (Traditional Chinese), ja (Japanese), es (Spanish)")
    target_lang = input("Enter target language code [default: en]: ").strip() or "en"
    print(f"   - Subtitle language set to: {target_lang}")

    # ==========================================
    # 5. 上傳影片檔 / Upload video
    # ==========================================
    print("\n➡️ [Step 5/11] Please upload the video file to process (mp4, mkv, mov, etc.)")
    uploaded = files.upload()
    if not uploaded:
        print("❌ 未上傳任何檔案 / No file uploaded. Aborting.")
        return

    up_name = list(uploaded.keys())[0]
    video_path = UPLOAD_DIR / up_name
    # Move the uploaded file from the root to the designated uploads directory
    Path(up_name).rename(video_path)

    if not video_path.exists():
        print("❌ 影片檔不存在，請重試上傳。/ Video file does not exist; please re-upload.")
        return

    print(f"✅ [Step 5/11] Video uploaded successfully: {video_path}")

    # ==========================================
    # 6. Whisper 模型載入與音訊抽取 / Load Model & Extract Audio
    # ==========================================
    print("\n⏳ [Step 6/11] Loading Whisper model and extracting audio...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   - Loading model '{model_name}' on '{device}'...")
    model = whisper.load_model(model_name, device=device)
    print("   - Model loaded.")

    audio_path = UPLOAD_DIR / f"{video_path.stem}.m4a"
    print("   - Extracting audio from video...")
    cmd_audio = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "aac", "-b:a", "192k", str(audio_path),
    ]
    subprocess.run(cmd_audio, check=True, capture_output=True)

    if not audio_path.exists():
        print("❌ 抽取音訊失敗 / Failed to extract audio.")
        return

    print("✅ [Step 6/11] Audio extracted successfully.")
    display(Audio(filename=str(audio_path)))

    # ==========================================
    # 7. Whisper 轉錄 / Transcribe with Whisper
    # ==========================================
    print("\n⏳ [Step 7/11] Transcribing audio with Whisper (this may take a while)...")
    result = model.transcribe(str(audio_path), task="transcribe", verbose=False)

    language = result.get("language", "unknown")
    segments = result.get("segments", [])
    full_text = result.get("text", "")

    if not segments:
        print("❌ Whisper did not produce any segments. Cannot continue.")
        return

    print(f"✅ [Step 7/11] Transcription complete. Detected language: {language}")
    print("\n📜 First 300 characters of original transcript:")
    print(full_text[:300] + ("..." if len(full_text) > 300 else ""))

    # ==========================================
    # 8. 翻譯字幕段落 / Translate segments
    # ==========================================
    print(f"\n⏳ [Step 8/11] Translating segments to '{target_lang}'...")
    translator = Translator()
    translated_segments = []

    for i, seg in enumerate(segments):
        orig = seg.get("text", "").strip()
        if not orig:
            t_txt = ""
        else:
            try:
                t = translator.translate(orig, dest=target_lang)
                t_txt = t.text
            except Exception as e:
                print(f"   - Warning: Translation failed for a segment, using original text. Error: {e}")
                t_txt = orig

        ns = seg.copy()
        ns["translated_text"] = t_txt
        translated_segments.append(ns)
        print(f"\r   - Translated segment {i+1}/{len(segments)}", end="", flush=True)

    print("\n✅ [Step 8/11] Translation complete.")
    full_translated_text = "\n".join(s["translated_text"] for s in translated_segments)

    print("\n📜 First 300 characters of translated text:")
    print(full_translated_text[:300] + ("..." if len(full_translated_text) > 300 else ""))

    # ==========================================
    # 9. 儲存逐字稿 / Save transcripts
    # ==========================================
    print("\n⏳ [Step 9/11] Saving text transcripts...")
    base = video_path.stem
    txt_orig = OUT_DIR / f"{base}_original.txt"
    txt_tr   = OUT_DIR / f"{base}_translated_{target_lang}.txt"

    txt_orig.write_text(full_text, encoding="utf-8")
    txt_tr.write_text(full_translated_text, encoding="utf-8")

    print("✅ [Step 9/11] Transcripts saved:")
    print("  ", txt_orig)
    print("  ", txt_tr)

    # ==========================================
    # 10. ffmpeg 硬燒字幕 / Burn subtitles with ffmpeg
    # ==========================================
    print("\n⏳ [Step 10/11] Preparing to burn subtitles onto video...")
    
    # Get video resolution to calculate font size
    probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(video_path)]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    vh = info["streams"][0]["height"]
    font_size = max(24, int(vh * 0.05))
    
    # Escape font path for ffmpeg filter
    fontfile_str = str(FONT_PATH).replace(":", "\\:")

    # Build the complex filter string for ffmpeg
    filter_parts = []
    input_label = "[0:v]"
    for idx, seg in enumerate(translated_segments):
        txt = seg.get("translated_text", "").strip()
        if not txt: continue
        
        start, end = seg.get("start", 0.0), seg.get("end", 0.0) + 0.05
        
        # Escape text for ffmpeg drawtext filter
        safe_text = txt.replace("\\", "\\\\").replace("'", "’").replace(":", "\\:").replace(",", "\\,").replace("%", "%%")
        
        output_label = f"[v{idx+1}]"
        draw = (
            f"{input_label}drawtext=fontfile='{fontfile_str}':"
            f"text='{safe_text}':fontsize={font_size}:fontcolor=white:bordercolor=black:borderw=2.5:"
            f"x=(w-text_w)/2:y=h-1.5*text_h:enable='between(t,{start},{end})'{output_label}"
        )
        filter_parts.append(draw)
        input_label = output_label

    if not filter_parts:
        print("❌ No subtitle content to render. Aborting.")
        return

    vf_filter = "; ".join(filter_parts)
    out_mp4 = OUT_DIR / f"{base}_subtitled_{target_lang}.mp4"

    # Construct the final ffmpeg command
    cmd_burn = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-filter_complex", vf_filter,
        "-map", input_label,
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "copy",
        str(out_mp4),
    ]

    print("   - Running ffmpeg to burn subtitles. This is the final and longest step. Please be patient.")
    
    proc = subprocess.run(cmd_burn, capture_output=True, text=True)

    if proc.returncode == 0:
        print(f"\n✅ [Step 10/11] Subtitled video created successfully!")
        print(f"   - File path: {out_mp4}")
        
        # ==========================================
        # 11. 下載檔案 / Download the final video
        # ==========================================
        print("\n⏳ [Step 11/11] Preparing to download the final video...")
        files.download(str(out_mp4))
        print("✅ [Step 11/11] Download should start automatically in your browser.")
    else:
        print("\n❌ [Step 10/11] Failed to create subtitled video.")
        print("   - Please copy the full ffmpeg output below for debugging.")
        print("\n" + "="*20 + " FFMPEG STDOUT " + "="*20)
        print(proc.stdout)
        print("\n" + "="*20 + " FFMPEG STDERR " + "="*20)
        print(proc.stderr)
        print("="*55)

# Run the main function
main()
