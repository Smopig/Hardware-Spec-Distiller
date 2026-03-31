# AI 硬體規格提煉器 (Hardware Spec Distiller)

使用 Google Gemini 自動深度分析電子元件 PDF 規格書，輸出結構化的全方位硬體設計百科（Markdown 格式），作為電路圖設計、PCB 佈局、底層驅動開發與採購的參考依據。

## 功能特色

- **全方位規格提取**：自動識別元件型號、腳位定義、電氣特性、極限值、佈局指引、韌體寄存器框架等
- **AI 智慧命名**：依據分析結果自動以 `廠牌_型號_功能描述` 格式命名輸出檔
- **Token 使用量監控**：每次分析後顯示輸入/輸出/總計 Token 數
- **重複保護**：自動跳過已存在摘要的檔案，避免重複呼叫 API
- **批次處理**：支援一次上傳多份 PDF，依序自動處理
- **結果打包下載**：分析完成後自動壓縮成 ZIP 檔並觸發下載

## 環境需求

- [Google Colab](https://colab.research.google.com/)
- `google-genai` Python 套件
- [Gemini API Key](https://aistudio.google.com/app/apikey)

## 使用方式

1. 在 Colab 安裝套件：
   ```bash
   !pip install -U google-genai -q
   ```

2. 執行 `hardware_distiller.py`

3. 輸入 Gemini API Key（使用安全輸入，不會明文顯示）

4. 上傳一份或多份 PDF 規格書

5. 選擇分析模型：
   - `[1]` gemini-3-flash-preview
   - `[2]` gemini-3.1-flash-lite-preview

6. 等待分析完成，結果自動下載為 ZIP 檔

## 輸出結構

```
Hardware_Analysis_Package_<timestamp>.zip
├── Summaries/
│   └── 廠牌_型號_功能描述_summary.md   # 結構化 Markdown 規格報告
└── Renamed_PDFs/
    └── 廠牌_型號_功能描述.pdf           # 依分析結果重新命名的原始 PDF
```

每份 Markdown 報告包含：基本資訊、電氣特性、關鍵性能參數表、完整接腳辭典、硬體佈局指引、韌體驅動框架（若有通訊介面）。
