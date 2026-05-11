---
name: hardware-spec-distiller
description: Distill electronic component PDF datasheets into structured Markdown hardware-design encyclopedias (pinout, electrical limits, layout guidance, register map, C-driver skeleton). Use when the user asks to analyze, summarize, or extract specs from hardware datasheets / 規格書 / PDF datasheet, or wants a Pin Map / 電氣特性 / 佈局指引 / 韌體寄存器 from a datasheet.
---

# Hardware Spec Distiller

把硬體規格書 PDF → 結構化「全方位硬體設計百科」Markdown 報告。

## 何時觸發此 Skill

當使用者提及以下情境時：

- 「幫我分析這份規格書 / datasheet」
- 「提煉 PDF 規格 / extract spec from datasheet」
- 「整理 Pin Map / 電氣特性 / 佈局指引 / 寄存器」
- 任何指向電子元件 PDF 規格書並要求結構化摘要的請求

## 兩種執行模式

### 模式 A：Claude 直接執行（預設，無需 API Key）

直接用 Claude Code 本身的 PDF 多模態能力處理。不需任何第三方 API、不需任何金鑰。

### 模式 B：批次/多供應商腳本（選用）

呼叫 `scripts/distill.py`，自動偵測環境變數使用 Anthropic / Gemini / OpenAI 任一供應商。適合大量批次或 CI 場景。

**決策樹**：
1. 若使用者沒明確說「用 API 跑批次」 → 用模式 A
2. 若 PDF 數量 ≥ 5 份且環境已設好 `ANTHROPIC_API_KEY` 或 `GEMINI_API_KEY` 或 `OPENAI_API_KEY` → 建議模式 B
3. 若使用者明確指定供應商 → 模式 B

---

## 模式 A 操作流程（Claude 直接執行）

### Step 1 — 確認輸入與輸出

詢問或從上下文判斷：
- **輸入**：單一 PDF 路徑、PDF 資料夾路徑、或當前工作目錄下的 PDF
- **輸出資料夾**：預設為「輸入資料夾旁邊的 `./summaries/`」；若使用者指定則照辦
- **不可逆動作**：是否要把原始 PDF 就地重新命名成 `廠牌_型號_功能.pdf`？**預設「不」**，除非使用者明確同意

如果使用者完全沒指定路徑，先列出 cwd 的 PDF 給他確認。

### Step 2 — 跳過已存在摘要

對每份輸入 PDF，先檢查輸出資料夾是否已存在 `{stem}_summary.md`。已存在則跳過並回報。

### Step 3 — 讀取 PDF

使用 Read 工具讀 PDF。

- **小檔（≤ 20 頁）**：一次 Read，不帶 `pages` 參數。
- **大檔（> 20 頁）**：分批 Read，每批最多 20 頁（例如 `pages: "1-20"`、`"21-40"`），並在心中彙整。先讀首頁/前 5 頁取得手冊版本與型號，再讀 Pin Map 段、電氣特性段、寄存器段。

### Step 4 — 套用 PROMPT.md

讀取本 skill 目錄下的 `PROMPT.md` 全文，作為系統指令套用到 PDF 內容，生成摘要。

**強制遵守 PROMPT.md 中所有規則**，特別是：
- 第一行必須是 `<<FILE_NAME>>: 廠牌_型號_中文功能描述 <<END>>`
- 未揭露資訊一律寫 `N/A (未於手冊揭露)`，**禁止虛構**
- 多 channel 元件須逐 channel 拆表
- Pin Map 的 `I/O Type` 須使用限定代碼
- 單位規範（電流 A/mA/µA、頻率 Hz/kHz/MHz、溫度 °C）

### Step 5 — 解析檔名標籤並寫檔

從生成內容第一行解析 `<<FILE_NAME>>: ... <<END>>`，正則：`<<FILE_NAME>>:\s*(.+?)\s*<<END>>`。

- 清除非法檔名字元：`\ / * ? : " < > |`
- 寫出 `{output_dir}/{pro_naming}_summary.md`
- 檔頭附上：

```
--- 硬體規格提煉報告 ---
📅 生成日期: <YYYY-MM-DD HH:MM:SS>
🤖 分析模型: claude (via Claude Code Skill)
📄 原始參考: <原始 PDF 檔名>
------------------------
```

- 移除生成內容中的 `<<FILE_NAME>>: ... <<END>>` 行
- 若使用者同意，再把原始 PDF 重新命名為 `{pro_naming}.pdf`（同檔名已存在則跳過重命名）

### Step 6 — 結束總結

回報統計：成功 N / 跳過 N / 失敗 N，以及所有產出檔的路徑清單。

---

## 模式 B 操作流程（外部 API 批次）

把 PDF 放入輸入資料夾，執行：

```bash
python .claude/skills/hardware-spec-distiller/scripts/distill.py \
  --input-dir <輸入資料夾> \
  --output-dir <輸出資料夾> \
  [--provider anthropic|gemini|openai] \
  [--model <model-id>] \
  [--rename-pdf]
```

腳本特性：
- **自動偵測供應商**：依環境變數順序 `ANTHROPIC_API_KEY` → `GEMINI_API_KEY` → `OPENAI_API_KEY`，或用 `--provider` 強制指定
- **輸入/輸出路徑可選**：兩者都有 CLI 參數，沒指定則預設 `./docs/specs` 和 `./docs/summaries`，但**不再寫死**
- **不依賴 Colab**：純本地端執行
- **重複保護**：已存在 `_summary.md` 自動跳過
- **PDF 重命名**：預設不重命名原檔（不可逆），加 `--rename-pdf` 才會
- **API 冷卻**：批次間隔 8 秒避免觸發 rate limit

執行前，提醒使用者確認：
1. 已 `pip install` 對應供應商 SDK（`anthropic` / `google-genai` / `openai`）
2. 已設定對應 `*_API_KEY` 環境變數
3. 輸入/輸出資料夾路徑

---

## 路徑彈性原則

**絕對不要**寫死 `/content/...`、`./docs/specs`、`./docs/summaries` 等舊路徑。一律由使用者指定，預設 cwd。

## 失敗處理

- PDF 讀取失敗 → 跳過該檔，繼續下一份，最後彙整失敗清單
- 解析不到 `<<FILE_NAME>>` 標籤 → 回退用原 PDF stem 命名為 `{stem}_summary.md`，並提醒使用者檢視
- 模式 B 缺 SDK 或 API Key → 提示使用者改用模式 A，或安裝對應套件

## 提示詞檔案位置

`PROMPT.md`（與本檔同目錄）— 切勿就地修改提示詞內容；如需調整，整份替換並提醒使用者「提示詞已更新」。
