# Whisper Subtitle Tool (Gradio)
# Whisper 影音字幕工具（Gradio）

A simple Gradio-based tool that:
- Transcribes video audio with **OpenAI Whisper**
- Translates the transcript with **deep-translator (GoogleTranslator)**
- Burns translated subtitles into the video using **ffmpeg drawtext**
- Exports **TXT**, **SRT**, and **bilingual (original + translation)** files

一個基於 Gradio 的簡易工具，可以：
- 使用 **OpenAI Whisper** 將影片音訊轉成逐字稿
- 使用 **deep-translator（GoogleTranslator）** 將逐字稿翻譯成目標語言
- 使用 **ffmpeg drawtext** 將翻譯後字幕「硬燒」進影片
- 匯出 **TXT**、**SRT**，以及**中英雙語對照檔（原文 + 譯文）**

---

## ✨ Features
## ✨ 功能特色

- Upload a video (mp4 / mkv / mov / etc.) via Gradio
- Auto language detection with Whisper
- Choose Whisper model size (tiny / base / small / medium / large)
- Choose translation target language (e.g. `en`, `zh-TW`, `zh-CN`, `ja`, etc.)
- Burn subtitles directly into the video (hardsub) using ffmpeg drawtext
- Generate multiple subtitle & transcript files, including bilingual comparison

- 透過 Gradio 介面上傳影片（mp4 / mkv / mov / 等常見格式）
- Whisper 自動偵測來源語言
- 可選擇 Whisper 模型大小（tiny / base / small / medium / large）
- 可選擇翻譯目標語言（例如：`en`、`zh-TW`、`zh-CN`、`ja`…）
- 使用 ffmpeg drawtext 直接將字幕「硬燒」到影片中
- 自動產生多種字幕與文字稿檔案，包含雙語對照檔

---

## 📁 Output Files
## 📁 輸出檔案種類

For each processed video `<video>` you will get:

對於每一個處理的影片 `<video>`，會產生：

1. **Subtitled video (MP4)**  
   - File: `transcripts/<video>_sub_<lang>_drawtext.mp4`  
   - Video with translated subtitles burned in.

   **含字幕影片（MP4）**  
   - 檔名：`transcripts/<video>_sub_<lang>_drawtext.mp4`  
   - 已將翻譯後字幕「硬燒」在畫面中。

2. **Original transcript (TXT)**  
   - File: `transcripts/<video>_original.txt`  
   - Full original transcription from Whisper.

   **原文逐字稿（TXT）**  
   - 檔名：`transcripts/<video>_original.txt`  
   - Whisper 輸出的完整原文逐字稿。

3. **Translated transcript (TXT)**  
   - File: `transcripts/<video>_translated_<lang>.txt`  
   - Full translated text only.

   **翻譯逐字稿（TXT）**  
   - 檔名：`transcripts/<video>_translated_<lang>.txt`  
   - 僅包含翻譯後的完整文字內容。

4. **Original subtitles (SRT)**  
   - File: `transcripts/<video>_original.srt`  
   - Time-aligned SRT in the original language.

   **原文字幕檔（SRT）**  
   - 檔名：`transcripts/<video>_original.srt`  
   - 以原文語言輸出的 SRT 時碼字幕。

5. **Translated subtitles (SRT)**  
   - File: `transcripts/<video>_translated_<lang>.srt`  
   - Time-aligned SRT in the target language.

   **翻譯字幕檔（SRT）**  
   - 檔名：`transcripts/<video>_translated_<lang>.srt`  
   - 以目標語言輸出的 SRT 時碼字幕。

6. **Bilingual comparison text (TXT)**  
   - File: `transcripts/<video>_bilingual_<lang>.txt`  
   - Layout:
     ```text
     Original line
     Translated line

     Original line
     Translated line

     ...
     ```

   **雙語對照文字檔（TXT）**  
   - 檔名：`transcripts/<video>_bilingual_<lang>.txt`  
   - 版面格式：
     ```text
     原文一行
     翻譯一行

     原文一行
     翻譯一行

     …
     ```

7. **Bilingual subtitles (SRT)**  
   - File: `transcripts/<video>_bilingual_<lang>.srt`  
   - Each SRT cue:
     ```text
     1
     00:00:00,000 --> 00:00:03,000
     Original text
     Translated text
     ```

   **雙語字幕檔（SRT）**  
   - 檔名：`transcripts/<video>_bilingual_<lang>.srt`  
   - 每一條字幕會同時顯示原文與譯文，例如：
     ```text
     1
     00:00:00,000 --> 00:00:03,000
     原文內容
     翻譯內容
     ```

---

## 🔧 Installation
## 🔧 安裝方式

This project is designed primarily for **Google Colab** or environments where you can run Python scripts and install packages.

本專案主要設計給 **Google Colab** 或任何可以執行 Python 並安裝套件的環境。

### 1. Clone this repository
### 1. 下載此專案

```bash
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
cd <YOUR_REPO_NAME>
```

### 2. Install dependencies
### 2. 安裝相依套件

You can let the script install everything automatically (recommended), or install manually.

可以讓腳本自動安裝（建議），也可以自行手動安裝。

**Automatic (inside the script):**  
When you run `whisper_sub_burner_colab.py`, it will execute:

**自動安裝（由腳本處理）：**  
當你執行 `whisper_sub_burner_colab.py` 時，會自動呼叫：

```bash
pip install -U "httpx>=0.28.1" gradio "git+https://github.com/openai/whisper.git" deep-translator
```

**Manual install:**  

**手動安裝：**

```bash
pip install -U "httpx>=0.28.1" gradio "git+https://github.com/openai/whisper.git" deep-translator
```

You also need **ffmpeg** and **ffprobe** available in your system `PATH`.

系統中也需要安裝 **ffmpeg** 與 **ffprobe**，且可在命令列中呼叫。

---

## 🚀 Usage (Colab)
## 🚀 在 Colab 中使用

1. Upload this project folder to your Colab environment (e.g., to `/content/HardsubGenerator/HardsubGenerator`), or clone from GitHub directly in Colab.
2. Open a Colab notebook.

1. 將此專案資料夾上傳到 Colab（例如 `/content/HardsubGenerator/HardsubGenerator`），或直接在 Colab 裡用 git clone。  
2. 開啟一個 Colab Notebook。

In a Colab cell:

在 Colab 其中一個 cell 中輸入：

```python
%cd /content/HardsubGenerator/HardsubGenerator
!python whisper_sub_burner_colab.py
```

This will:

- Install required Python packages
- Start a Gradio web interface
- Show you a public share link (if `share=True`)

這會：

- 自動安裝所需的 Python 套件  
- 啟動 Gradio 網頁介面  
- 顯示可對外訪問的分享連結（如果設定 `share=True`）

---

## 🖥️ Gradio Interface
## 🖥️ Gradio 介面說明

In the Gradio UI you will see:

在 Gradio 介面中你會看到：

- **Video upload**: upload your source video file  
- **Model size**: choose Whisper model (`tiny`, `base`, `small`, `medium`, `large`)  
- **Target language**: e.g. `en`, `zh-TW`, `zh-CN`, `ja`, `ko`, `fr`…  
- **Start button**: runs transcription + translation + hardsub  
- Outputs:
  - Subtitled video (preview and downloadable)
  - Original / translated transcripts (.txt)
  - Original / translated / bilingual subtitles (.srt)
  - Bilingual comparison (.txt)
  - Logs (process messages)

- **影片上傳**：上傳要處理的影片檔  
- **模型大小**：選擇 Whisper 模型（`tiny`、`base`、`small`、`medium`、`large`）  
- **目標語言**：例如 `en`、`zh-TW`、`zh-CN`、`ja`、`ko`、`fr`…  
- **Start 按鈕**：執行轉錄 + 翻譯 + 硬燒字幕  
- 輸出區塊包含：
  - 預覽與下載「含字幕影片」  
  - 原文 / 翻譯逐字稿（.txt）  
  - 原文 / 翻譯 / 雙語字幕（.srt）  
  - 雙語對照文字檔（.txt）  
  - 執行過程的日誌訊息（log）

---

## 🔤 Font & Subtitle Style
## 🔤 字型與字幕樣式

- The script automatically downloads **NotoSansCJK-Regular.ttc** and uses it for drawtext.
- Subtitles are centered at the bottom of the video.
- The font size is currently **fixed at 18**.

- 腳本會自動下載 **NotoSansCJK-Regular.ttc** 字型並用於 ffmpeg drawtext。  
- 字幕會顯示在畫面下方置中位置。  
- 字體大小目前固定為 **18**。

If you want to change font size or position, edit this part in `whisper_sub_burner_colab.py`:

如果你想調整字體大小或位置，可編輯 `whisper_sub_burner_colab.py` 中這段：

```python
font_size = 18  # change this value if needed

draw = (
    f"{input_label}drawtext=fontfile='{fontfile_str}':"
    f"text='{safe_text}':"
    f"fontsize={font_size}:"
    f"fontcolor=white:bordercolor=black:borderw=2:"
    f"x=(w-text_w)/2:y=h-1.5*text_h:"
    f"enable='between(t,{start},{end})'{output_label}"
)
```

---

## ❗ Notes & Limitations
## ❗ 注意事項與限制

- Whisper models can be slow on CPU; using a GPU (e.g. in Colab) is highly recommended.
- Translation quality depends on GoogleTranslator (deep-translator).
- Very long videos will take longer to process and may hit resource limits in free Colab.

- 在純 CPU 上執行 Whisper 會比較慢，建議使用 GPU（例如在 Colab 中）。  
- 翻譯品質取決於 GoogleTranslator / deep-translator 的結果。  
- 影片越長，處理時間越久，在免費版 Colab 可能會遇到資源限制。

---

## 🐛 Troubleshooting
## 🐛 常見問題排除

**Q1. ffmpeg not found / ffprobe not found**  
Make sure ffmpeg / ffprobe are installed and accessible from your PATH.

**Q1. 出現 ffmpeg not found / ffprobe not found**  
請先在系統中安裝 ffmpeg / ffprobe，並確認已加入 PATH。

---

**Q2. Gradio link not working in Colab**  
- Try setting `share=True` when launching the app  
- Or open the **local URL** from the Colab output in a new browser tab (if supported)

**Q2. 在 Colab 中 Gradio 分享連結無法使用**  
- 確認在 `demo.launch()` 有設定 `share=True`  
- 或嘗試使用輸出中顯示的 **local URL**（視 Colab 環境支援情況而定）

---

**Q3. Subtitle language looks wrong**  
- Check you selected the correct **target language code** (e.g. `zh-TW` vs `zh-CN`)  
- Some languages may have limited translation quality.

**Q3. 字幕語言或內容怪怪的**  
- 請確認你選擇的 **目標語言代碼** 正確（例如 `zh-TW` 與 `zh-CN` 有區別）  
- 個別語言在翻譯準確度上可能有所差異。
