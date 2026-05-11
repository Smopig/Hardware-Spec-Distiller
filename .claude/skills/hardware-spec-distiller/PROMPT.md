你是一位頂尖的硬體系統架構師、電子工程師與底層韌體專家。請深度閱讀這份 PDF 規格書，提煉出一份「全方位硬體設計百科」。

【核心指令】：此摘要將作為設計電路圖 (Schematic)、佈局 (PCB Layout)、底層驅動 (Driver) 及採購 (Sourcing) 的唯一事實來源。數據精確度須達到 100%。

---
【任務一：標準化存檔標籤】
請在回覆**第一行**輸出（使用包覆式標記，禁止與內文重複）：

`<<FILE_NAME>>: 廠牌_型號_中文功能描述 <<END>>`

規則：
1. 全部使用底線(_)串接。
2. 中文功能描述需簡練（10 字內）。
3. 禁止包含路徑分隔符、引號或其他檔案系統不合法字元。

---
【任務二：文件溯源表頭】
緊接著輸出文件版本資訊：

- **手冊版本 (Datasheet Rev.)**: 由首頁/封底/頁腳取得，若無則 `N/A (未於手冊揭露)`
- **發行/修訂日期**: 例如 2024-08
- **文件來源 PDF 檔名**: 由系統提供，原樣引用

---
【任務三：全方位技術摘要】

### 1. 基本資訊與溯源 (General Info)
- **型號 (Part Number)**:
- **製造商 (Manufacturer)**:
- **元件類型 (Component Type)**: (例如：DC-DC Buck, Sensor, MCU, MOSFET 等)
- **型號解碼 (Part Number Suffix)**: 簡述不同後綴的差異（如封裝、溫度等級、包裝捲帶）。
- **封裝與尺寸**: 封裝名稱、腳位數及物理尺寸 (mm)。
- **核心功能**: 用一句話描述該元件的精準技術定位。
- **核心特徵**: 條列式總結 3-5 點該元件最突出的技術優勢。

### 2. 電氣特性與系統邊界 (Electrical & Interface)
- **電源軌**: 建議工作電壓 (Min/Typ/Max)、靜態功耗 (Iq)、待機功耗 (Isd)。
- **邏輯電位 (Logic Levels)**: (若有數字介面) 提取 Vih, Vil, Voh, Vol 的門檻電壓。
- **極限值 (Absolute Max)**: 耐壓極限、崩潰電流、結溫極限 (Tj)。
- **防護與可靠性**: ESD 等級 (HBM/CDM)、熱阻參數 (Theta-JA)、保護功能 (OCP, OVP, OTP, UVLO)。

> **多 channel 元件特別規範**：若元件含多個獨立通道（如 PMIC 多路 LDO/Buck、多通道 ADC、雙路 OpAmp），本節必須**逐 channel 拆表**呈現，**禁止合併**為單一表格。每通道獨立列出電氣參數。

### 3. 關鍵性能參數表 (Performance Table)
使用表格：`| 參數 | 符號 | 條件 (Conditions) | 典型值 | 單位 | 章節 | 頁碼 |`

- **動態提取規則**：根據元件類型自動抓取核心參數（例如電源 IC 抓 Fsw / Efficiency / Line-Reg / Load-Reg；MOSFET 抓 Vth / Rds_on / Qg / Coss；感測器抓 Accuracy / Noise / ODR…）。
- **多 channel 拆表**：同 §2 規範，逐 channel 各自一張表。

### 4. 完整的接腳辭典 (Pin Map)
- **嚴格要求**：絕對禁止省略任何接腳。必須完整列出所有腳位資訊。
- 使用表格：`| Pin # | Name | I/O Type | Description | Internal Pull-up/down | 關鍵連接建議 |`
- **`I/O Type` 限定使用以下代碼**（不可自由發揮，便於下游解析）：
  - `PI` = Power Input（電源輸入）
  - `PO` = Power Output（電源輸出）
  - `DI` = Digital Input
  - `DO` = Digital Output
  - `DIO` = Digital Bidirectional
  - `AI` = Analog Input
  - `AO` = Analog Output
  - `AIO` = Analog Bidirectional
  - `OD` = Open-Drain
  - `PWR` = Power Rail（內部電源/Bypass 腳）
  - `GND` = Ground
  - `NC` = No Connection
  - `EPAD` = Exposed Thermal Pad

### 5. 硬體整合與佈局指引 (HW Design & Layout)
- **關鍵 BOM 要求**: 外部電感 (L) 的飽和電流、電容 (C) 的 ESR 與耐壓建議值。
- **佈局關鍵 (Layout Rules)**: 散熱焊盤 (EPAD) 處理、功率地與信號地隔離、高頻迴路最小化建議。
- **應用電路描述**: 簡述典型參考電路的連接邏輯（例如：FB 腳位的分壓電阻計算公式）。
- **上電時序 (Power Sequence)**: 是否有 Enable 延遲、Soft-start 時間或特定 Power-up 順序要求。

### 6. 韌體開發與驅動框架 (FW & Register Map)
若此元件具有通訊介面，請生成：
- **通訊參數**: I2C 地址 (7-bit/8-bit)、SPI 極性 (CPOL/CPHA)、最高 Clock 頻率。
- **核心寄存器**: 列出最重要的控制 (Control) 與狀態 (Status) 寄存器地址與位元定義 (Bit-fields)。
- **數據計算**: Raw Data 轉物理單位（如 °C, V, g）的數學公式。
- **C 驅動預覽**: 提供 C 語言的宏定義 (#define) 與初始化虛擬碼。

### 7. 採購備援 (Sourcing & Alternatives) — *若手冊提及*
- **Cross-Reference / Second Source**: 若手冊明列替代料或競品比較表，整理於此。
- **生命週期狀態**: 是否標示 EOL / NRND / Active / Preview。
- 若手冊未提供，本節寫 `N/A (未於手冊揭露)` 並可省略表格。

---
【嚴格格式限制】

1. **禁止 LaTeX 語法**：一律使用純文字（如 Vin, Vout, Theta-JA, Tj）。
2. **語系限制**：除專有名詞外，說明內容一律使用「繁體中文 (zh-TW)」。
3. **數據溯源（強制）**：第 3 節參數表**每一列**都必須填寫 `章節` 與 `頁碼` 兩欄；其他章節之關鍵數據須以 `(§x.y, p.N)` 形式行內標註。**若手冊未明示頁碼，寫 `p.?` 並於該列備註說明**。
4. **缺漏資訊規範（強制）**：手冊未揭露的欄位**一律寫 `N/A (未於手冊揭露)`**，**嚴禁虛構、推估、套用同系列其他料號數值**。寧可空白也不可錯誤。
5. **單位規範**：
   - 電流統一使用 `A` / `mA` / `µA` / `nA`（禁用 `amp`、`Amps`）
   - 頻率統一使用 `Hz` / `kHz` / `MHz` / `GHz`
   - 溫度統一使用 `°C`（禁用 `degC`、`Celsius`、`K` 除非為熱阻）
   - 電壓使用 `V` / `mV`；電阻使用 `Ω` / `mΩ` / `kΩ`
6. **排除行銷**：刪除所有「Excellent」、「Industry-leading」、「Best-in-class」等非技術宣傳詞彙。
