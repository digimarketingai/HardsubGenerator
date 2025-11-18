# Whisper Colab 硬字幕產生器 / Hardsub Generator

# 繁體中文說明

這是一個專為 Google Colab 設計的 Python 腳本，可以自動化為影片產生並「硬燒」翻譯字幕的完整流程。您只需要上傳影片，腳本就會利用 OpenAI 的 Whisper 模型進行語音轉錄，透過 Google Translate 進行翻譯，最後使用 FFmpeg 將字幕直接嵌入影片畫面中。

## ✨ 功能特色

*   **一鍵在 Colab 中執行**：無需複雜的本機環境設定，直接在瀏覽器中使用 Google Colab 的免費運算資源（包含 GPU）。
*   **自動語音轉錄**：使用 OpenAI 強大的 Whisper 模型，能自動偵測影片的原始語言並產生高準確度的逐字稿。
*   **自動翻譯**：整合 Google 翻譯，可將逐字稿翻譯成多種語言（英文、繁中、簡中、日文等）。
*   **硬字幕燒錄**：使用 FFmpeg 的 `drawtext` 濾鏡將翻譯好的字幕直接「燒」進影片中，確保在任何裝置上播放都能顯示字幕。
*   **自動化流程**：從抽取音訊、轉錄、翻譯到最後的影片合成，整個過程完全自動化。
*   **檔案產出**：除了最終的影片，腳本也會儲存原始語言和翻譯語言的純文字檔（`.txt`），方便後續使用。

## 🚀 如何使用

1.  **開啟 Colab 腳本**：點擊本頁面最上方的 "Open In Colab" 徽章。
2.  **執行腳本**：
    *   在開啟的 Colab 頁面中，點擊頂部選單的「執行階段」 (Runtime) -> 「全部執行」 (Run all)。
    *   Google 會提示「警告：這個筆記本不是由 Google 編寫的」，點擊「仍要執行」 (Run anyway)。
3.  **上傳影片**：
    *   腳本執行後，會出現一個上傳按鈕。點擊它並選擇您要處理的影片檔案（如 `.mp4`, `.mov`, `.mkv`）。
4.  **選擇 Whisper 模型**：
    *   在輸出框中，系統會提示您選擇 Whisper 模型的大小。模型越大，準確率越高，但處理時間也越長。直接按 Enter 會使用預設的 `small` 模型。
    *   可選模型：`tiny`, `base`, `small`, `medium`, `large`。
5.  **選擇目標翻譯語言**：
    *   接著，系統會提示您輸入目標翻譯語言的代碼。直接按 Enter 會使用預設的 `en` (英文)。
    *   常用代碼：`zh-TW` (繁體中文), `zh-CN` (簡體中文), `ja` (日文), `ko` (韓文), `es` (西班牙文) 等。
6.  **等待處理完成**：
    *   腳本會開始執行所有步驟：抽取音訊、轉錄、翻譯、燒錄字幕。所需時間取決於影片長度和您選擇的模型大小。
    *   您可以在 Colab 的輸出格中看到詳細的進度。
7.  **下載成品**：
    *   處理完成後，最終的影片檔案會儲存在 Colab 環境的 `transcripts/` 資料夾中。
    *   在 Colab 頁面左側的檔案總管面板中，展開 `transcripts` 資料夾，找到檔名包含 `_sub_` 的 `.mp4` 檔案。
    *   在檔案上點擊右鍵，選擇「下載」 (Download) 即可。

## 📝 輸出檔案

腳本執行完成後，您會在 `transcripts/` 資料夾中找到以下檔案：

*   `{影片原始檔名}_original.txt`：Whisper 轉錄的原始語言逐字稿。
*   `{影片原始檔名}_translated_{語言代碼}.txt`：翻譯後的目標語言逐字稿。
*   `{影片原始檔名}_sub_{語言代碼}_drawtext.mp4`：已經燒錄好字幕的最終影片成品。

## ⚠️ 注意事項

*   此腳本專為 Google Colab 設計，無法在您的本機電腦直接執行。
*   Google 翻譯有其使用限制與準確度問題，對於較長的影片或專業術語，翻譯結果可能不盡理想。
*   處理時間受影片長度、Whisper 模型大小以及 Colab 分配的硬體資源影響，可能需要數分鐘到數小時不等。
*   字幕的樣式（字體大小、位置、顏色）已在腳本中預設，如需客製化，請直接修改 Python 腳本中的 `drawtext` 相關參數。

---

# English Description

This is a Python script designed specifically for Google Colab to automate the entire workflow of generating and "burning" translated subtitles onto a video. You just need to upload a video file, and the script will use OpenAI's Whisper model for transcription, Google Translate for translation, and FFmpeg to embed the subtitles directly into the video frames (hardsubbing).

## ✨ Features

*   **One-Click Execution in Colab**: No need for complex local environment setup. Directly use Google Colab's free computing resources (including GPUs) in your browser.
*   **Automatic Speech-to-Text**: Utilizes OpenAI's powerful Whisper model to auto-detect the source language of the video and generate a highly accurate transcript.
*   **Automatic Translation**: Integrates with Google Translate to translate the transcript into various languages (English, Traditional/Simplified Chinese, Japanese, etc.).
*   **Hardsub Burning**: Uses FFmpeg's `drawtext` filter to "burn" the translated subtitles directly onto the video, ensuring they are visible on any playback device.
*   **Automated Pipeline**: The entire process, from audio extraction, transcription, translation, to final video rendering, is fully automated.
*   **File Outputs**: In addition to the final video, the script also saves plain text files (`.txt`) of both the original and translated transcripts for other uses.

## 🚀 How to Use

1.  **Open the Colab Script**: Click the "Open In Colab" badge at the top of this page.
2.  **Run the Script**:
    *   In the opened Colab notebook, click on the "Runtime" menu at the top and select "Run all".
    *   Google will show a warning: "Warning: This notebook was not authored by Google." Click "Run anyway".
3.  **Upload Your Video**:
    *   After the script starts, an upload button will appear. Click it and select the video file you want to process (e.g., `.mp4`, `.mov`, `.mkv`).
4.  **Choose a Whisper Model**:
    *   In the output cell, you will be prompted to choose a Whisper model size. Larger models offer higher accuracy but take longer to process. Pressing Enter without typing anything will select the default `small` model.
    *   Available models: `tiny`, `base`, `small`, `medium`, `large`.
5.  **Choose a Target Language**:
    *   Next, you will be prompted to enter the language code for translation. Pressing Enter will use the default `en` (English).
    *   Common codes: `zh-TW` (Traditional Chinese), `zh-CN` (Simplified Chinese), `ja` (Japanese), `ko` (Korean), `es` (Spanish).
6.  **Wait for Processing**:
    *   The script will now execute all steps: extracting audio, transcribing, translating, and burning subtitles. The time required depends on the video length and the model size you selected.
    *   You can monitor the detailed progress in the Colab output cell.
7.  **Download the Final Product**:
    *   Once processing is complete, the final video file will be saved in the `transcripts/` folder within the Colab environment.
    *   On the left side of the Colab page, open the "Files" panel, expand the `transcripts` folder, and find the `.mp4` file with `_sub_` in its name.
    *   Right-click on the file and select "Download" to save it to your computer.

## 📝 Output Files

After the script finishes, you will find the following files in the `transcripts/` directory:

*   `{original_video_name}_original.txt`: The original language transcript generated by Whisper.
*   `{original_video_name}_translated_{lang_code}.txt`: The translated transcript in the target language.
*   `{original_video_name}_sub_{lang_code}_drawtext.mp4`: The final video with the hardcoded subtitles.

## ⚠️ Notes

*   This script is designed exclusively for Google Colab and will not run directly on your local machine.
*   Google Translate has its own usage limits and accuracy issues. The translation quality may not be perfect, especially for long videos or technical jargon.
*   Processing time depends on video length, Whisper model size, and the hardware resources allocated by Colab. It can range from a few minutes to several hours.
*   The subtitle style (font size, position, color) is preset in the script. If you need to customize it, you will have to modify the `drawtext` parameters directly in the Python script.
