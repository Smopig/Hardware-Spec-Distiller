# AI 硬體規格提煉器（Claude Code Skill）

把電子元件 PDF 規格書，深度提煉成結構化的「全方位硬體設計百科」Markdown 報告，作為電路圖設計、PCB 佈局、底層驅動開發與採購的單一事實來源。

本專案已從原本綁定 Google Colab / Gemini 的 Python 腳本，改寫為一個 **Claude Code Skill**，具備以下特性：

- ✅ **不限定 LLM 供應商**：預設由 Claude Code 主機端直接處理，亦支援 Anthropic / Gemini / OpenAI 任一 API
- ✅ **不需要 Colab**：純本地或 Claude Code 環境
- ✅ **不限定金鑰**：預設模式完全免 API Key；批次模式自動偵測環境變數
- ✅ **路徑彈性**：輸入/輸出資料夾自由指定，亦可使用預設值
- ✅ **強化版提示詞**：頁碼強制溯源、缺漏資訊禁止虛構、多 channel 拆表、Pin Map I/O Type 代碼化、單位規範化等

---

## 安裝

把 `.claude/skills/hardware-spec-distiller/` 整個資料夾複製到你的專案根目錄（或全域 `~/.claude/skills/`）。Claude Code 啟動時會自動掃描並載入。

```
your-project/
└── .claude/
    └── skills/
        └── hardware-spec-distiller/
            ├── SKILL.md
            ├── PROMPT.md
            └── scripts/
                └── distill.py
```

---

## 使用方式

### 模式 A：Claude 直接執行（推薦，無需 API Key）

在 Claude Code session 中直接說：

> 「幫我分析 `./datasheets/foo.pdf`，輸出到 `./out`」
>
> 「處理 `~/Downloads/` 裡所有的 datasheet」
>
> 「提煉這份規格書的 Pin Map 和寄存器」

Claude 會自動觸發本 Skill，逐份讀 PDF、套用 `PROMPT.md`、產出 `*_summary.md`。

### 模式 B：批次/多供應商腳本

適合大量 PDF（≥ 5 份）或 CI 場景。先安裝對應 SDK 並設環境變數：

```bash
# 任選其一
pip install anthropic       && export ANTHROPIC_API_KEY=sk-ant-...
pip install google-genai    && export GEMINI_API_KEY=...
pip install openai          && export OPENAI_API_KEY=sk-...
```

執行：

```bash
python .claude/skills/hardware-spec-distiller/scripts/distill.py \
  --input-dir ./pdfs \
  --output-dir ./summaries
```

CLI 參數：

| 參數 | 預設 | 說明 |
|---|---|---|
| `--input-dir` | `./docs/specs` | PDF 來源資料夾 |
| `--output-dir` | `./docs/summaries` | Markdown 輸出資料夾 |
| `--provider` | 自動偵測 | `anthropic` / `gemini` / `openai` |
| `--model` | 各供應商預設 | 覆寫 model id |
| `--rename-pdf` | 否 | 是否就地重命名原 PDF（不可逆） |

供應商偵測優先序：`ANTHROPIC_API_KEY` → `GEMINI_API_KEY` → `OPENAI_API_KEY`，或以 `--provider` 強制指定。

---

## 輸出範例

每份 PDF → 一份 `廠牌_型號_中文功能_summary.md`，內含：

1. **基本資訊與溯源**（型號、廠商、封裝、特徵）
2. **電氣特性與系統邊界**（電源軌、邏輯電位、極限值、防護）
3. **關鍵性能參數表**（含章節 + 頁碼溯源）
4. **完整的接腳辭典**（標準化 I/O Type 代碼，禁止省略）
5. **硬體整合與佈局指引**（BOM、Layout、上電時序）
6. **韌體開發與驅動框架**（寄存器、計算公式、C 驅動骨架）
7. **採購備援**（cross-reference / 生命週期，若手冊有）

---

## 提示詞 (PROMPT.md) 重點規範

- 第一行強制：`<<FILE_NAME>>: 廠牌_型號_中文功能描述 <<END>>`
- 未揭露資訊一律寫 `N/A (未於手冊揭露)`，**禁止虛構或推估**
- 多 channel 元件（PMIC 等）必須**逐 channel 拆表**
- Pin Map `I/O Type` 限定使用 `PI / PO / DI / DO / AI / AO / PWR / GND / NC / EPAD` 等代碼
- 單位規範：電流 `A/mA/µA`、頻率 `Hz/kHz/MHz`、溫度 `°C`、電阻 `Ω`
- 排除行銷詞彙（Excellent / Industry-leading 等）

如需自訂提示詞，直接編輯 `.claude/skills/hardware-spec-distiller/PROMPT.md`。

---

## 從舊版遷移

舊的 `hardware_distiller.py`（Colab 版）與 `hardware_distiller_local.py`（Gemini-only 版）已刪除，全部功能由 Skill 接手。原 Gemini 行為可透過 `scripts/distill.py --provider gemini` 完整保留。
