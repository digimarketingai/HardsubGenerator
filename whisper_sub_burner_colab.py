# ==============================================================================
# Full Python Script to Download a Font and Burn Subtitles into a Video
#
# Dependencies:
#   - Python 3.6+
#   - 'requests' library (`pip install requests`)
#   - ffmpeg (must be installed and available in the system's PATH)
# ==============================================================================

import os
import subprocess
import requests
from pathlib import Path

# ==========================================
# 1. 設定目錄 / Setup Directories
# ==========================================
# Create directories for fonts, input, and output files for good organization.
FONT_DIR = Path("./fonts")
VIDEO_DIR = Path("./videos")
OUTPUT_DIR = Path("./output")

FONT_DIR.mkdir(exist_ok=True)
VIDEO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

print("✅ Directories ensured to exist: ./fonts, ./videos, ./output")

# ==========================================
# 2. 下載字型（Noto Sans CJK） / Download Font
# ==========================================
# This section has been refactored to encapsulate the download logic.
# It still uses a primary and a fallback URL for robustness.
FONT_NAME = "NotoSansSC-Regular.otf"
FONT_PATH = FONT_DIR / FONT_NAME

def download_font_with_fallback(font_filename, destination_path):
    """
    Downloads the specified font, trying a primary URL first and then a fallback.

    This function encapsulates the entire download process, including error handling
    and logging for each attempt.

    Args:
        font_filename (str): The name of the font file (e.g., "NotoSansSC-Regular.otf").
        destination_path (Path): The path object where the file will be saved.

    Returns:
        bool: True if download was successful, False otherwise.
    """
    # The font family is 'notosanssc' in the Google Fonts repository URL structure.
    font_family_url_part = "notosanssc"
    
    # URL 1: Primary source from the official Google Fonts GitHub repository.
    font_url_primary = f"https://github.com/google/fonts/raw/main/ofl/{font_family_url_part}/{font_filename}"

    # URL 2: Fallback source from the reliable jsDelivr CDN, which mirrors GitHub.
    font_url_fallback = f"https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/{font_family_url_part}/{font_filename}"

    def _download_attempt(url, destination):
        """Inner function to handle a single download attempt."""
        try:
            print(f"   Attempting to download from: {url}")
            # Use a timeout to prevent the script from hanging indefinitely.
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                with open(destination, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"   Successfully downloaded to {destination}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"   Download attempt failed: {e}")
            return False

    # --- Main Download Logic ---
    print(f"\n⏳ 下載字型 {font_filename} ... / Downloading font {font_filename} ...")
    if _download_attempt(font_url_primary, destination_path):
        print("✅ 字型已成功下載 / Font successfully downloaded.")
        return True
    else:
        print("\n   Primary download failed. Trying fallback URL...")
        if _download_attempt(font_url_fallback, destination_path):
            print("✅ 字型已透過備用連結成功下載 / Font successfully downloaded via fallback link.")
            return True
        else:
            # Both attempts failed
            return False

# --- Main Script Logic for Font ---
# Check if the font file already exists to avoid re-downloading.
if not FONT_PATH.exists():
    # If the font doesn't exist, call the download function.
    if not download_font_with_fallback(FONT_NAME, FONT_PATH):
        # If the download function returns False (meaning both URLs failed), exit the script.
        raise SystemExit(
            "\n❌ 字型下載失敗，主要來源與備用來源皆無法連線。\n"
            "❌ Font download failed from both primary and fallback sources.\n"
ax"   Please check your network connection or try running the script again later."
        )

if FONT_PATH.exists():
    print(f"\n✅ 使用字型 / Using font: {FONT_PATH}")
else:
    # This case should be unreachable if the download fails due to the SystemExit above,
    # but it serves as a final safeguard.
    raise SystemExit(f"❌ 字型檔案不存在 / Font file not found at: {FONT_PATH}")

# ==========================================
# 3. 建立範例字幕檔 / Create Sample Subtitle File
# ==========================================
SUBTITLE_PATH = VIDEO_DIR / "subtitles.srt"
srt_content = """1
00:00:01,000 --> 00:00:04,000
This is the first subtitle.
這是第一個字幕。

2
00:00:05,000 --> 00:00:08,000
This is the second subtitle,
using the Noto Sans font.
這是第二個字幕，
使用思源黑體。
"""

with open(SUBTITLE_PATH, "w", encoding="utf-8") as f:
    f.write(srt_content)

print(f"\n✅ 範例字幕檔已建立 / Sample subtitle file created at: {SUBTITLE_PATH}")

# ==========================================
# 4. 建立範例影片 / Create Sample Video
# ==========================================
INPUT_VIDEO_PATH = VIDEO_DIR / "input.mp4"
if not INPUT_VIDEO_PATH.exists():
    print(f"\n⏳ 正在建立 10 秒的黑色範例影片 / Creating a 10-second black sample video...")
    # This ffmpeg command creates a 10-second, 640x360, black video with silent audio.
    ffmpeg_create_video_cmd = [
        'ffmpeg',
        '-f', 'lavfi',                 # Input format: libavfilter
        '-i', 'color=c=black:s=640x360:r=30:d=10', # Input source: a black color pattern
        '-f', 'lavfi',                 # Another input format for silent audio
        '-i', 'anullsrc=r=44100:cl=stereo', # Input source: silent audio
        '-c:v', 'libx264',             # Video codec: H.264
        '-c:a', 'aac',                 # Audio codec: AAC
        '-t', '10',                    # Duration: 10 seconds
        '-pix_fmt', 'yuv420p',         # Pixel format for compatibility
        '-y',                          # Overwrite output file if it exists
        str(INPUT_VIDEO_PATH)
    ]
    try:
        subprocess.run(ffmpeg_create_video_cmd, check=True, capture_output=True, text=True)
        print(f"✅ 範例影片已建立 / Sample video created at: {INPUT_VIDEO_PATH}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 建立範例影片失敗 / Failed to create sample video.")
        print(f"   ffmpeg stdout: {e.stdout}")
        print(f"   ffmpeg stderr: {e.stderr}")
        raise
else:
    print(f"\n✅ 範例影片已存在 / Sample video already exists at: {INPUT_VIDEO_PATH}")

# ==========================================
# 5. 將字幕嵌入影片 / Burn Subtitles into Video
# ==========================================
OUTPUT_VIDEO_PATH = OUTPUT_DIR / "output_with_subtitles.mp4"
print(f"\n⏳ 正在將字幕嵌入影片... / Burning subtitles into video...")

# The font name 'Noto Sans SC' is the internal name of the font.
# We must also tell ffmpeg where to find the font files using the `fontsdir` option.
# The `force_style` parameter applies the font for rendering the subtitles.
ffmpeg_burn_subtitles_cmd = [
    'ffmpeg',
    '-i', str(INPUT_VIDEO_PATH),
    '-vf', f"subtitles={SUBTITLE_PATH.as_posix()}:fontsdir={FONT_DIR.as_posix()}:force_style='FontName=Noto Sans SC'",
    '-c:v', 'libx264',
    '-c:a', 'copy',
    '-y',
    str(OUTPUT_VIDEO_PATH)
]

# Explanation of the ffmpeg command:
# -i {input_video}: Specifies the input video file.
# -vf "subtitles=...": Applies a video filter ('vf').
#   - subtitles={subtitle_file}: The name of the filter and the path to the .srt file.
#     - Using .as_posix() ensures forward slashes, which is safer for ffmpeg.
#   - fontsdir={font_directory}: Tells ffmpeg which directory to scan for fonts.
#   - force_style='FontName=Noto Sans SC': Forces the use of the specified font for rendering.
#     'Noto Sans SC' is the name defined inside the .otf font file.
# -c:a copy: Copies the audio stream without re-encoding, which is much faster.
# -y: Overwrites the output file if it exists.

try:
    print("   Executing ffmpeg command:")
    print(f"   {' '.join(ffmpeg_burn_subtitles_cmd)}")
    # Using capture_output=True will hide ffmpeg's progress, but is useful for debugging.
    # If you want to see ffmpeg's progress in real-time, remove `capture_output`.
    subprocess.run(ffmpeg_burn_subtitles_cmd, check=True, capture_output=True, text=True)
    print("\n✅ 字幕嵌入成功！/ Subtitles burned successfully!")
    print(f"✅ 最終影片儲存於 / Final video saved at: {OUTPUT_VIDEO_PATH}")
except subprocess.CalledProcessError as e:
    print("\n❌ 字幕嵌入失敗 / Failed to burn subtitles.")
    print("   Please ensure ffmpeg is installed and the font was downloaded correctly.")
    print(f"   ffmpeg stdout:\n{e.stdout}")
    print(f"   ffmpeg stderr:\n{e.stderr}")
    raise

# ==========================================
# 6. 完成 / Finished
# ==========================================
print("\n🎉 Script finished successfully.")
