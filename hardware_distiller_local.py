# 安裝必要的函式庫
# pip install -U google-genai

import os
import re
import time
import getpass
import shutil
import zipfile
import argparse
from pathlib import Path
from google import genai

# ==========================================
# ⚙️ 配置區
# ==========================================

# API 頻率保護冷卻秒數
API_COOLDOWN_SEC = 8

# 雲端檔案處理最大等待秒數
FILE_PROCESSING_TIMEOUT_SEC = 120

AVAILABLE_MODELS = {
    "1": "gemini-3-flash-preview",
    "2": "gemini-3.1-flash-lite-preview",
}

# ==========================================
# 📝 提煉 Prompt (全方位整合版)
# ==========================================
DISTILL_PROMPT = """
你是一位頂尖的硬體系統架構師、電子工程師與底層韌體專家。請深度閱讀這份 PDF 規格書，提煉出一份「全方位硬體設計百科」。
【核心指令】：此摘要將作為設計電路圖 (Schematic)、佈局 (PCB Layout)、底層驅動 (Driver) 及採購 (Sourcing) 的唯一事實來源。數據精確度須達到 100%。

---
【任務一：標準化存檔標籤】
請在回覆第一行輸出：
[FILE_NAME]: 廠牌_型號_中文功能描述
規則：1. 全部使用底線(_)串接。 2. 中文功能描述需簡練(10字內)。

---
【任務二：全方位技術摘要】

### 1. 基本資訊與溯源 (General Info)
- **型號 (Part Number)**:
- **製造商 (Manufacturer)**:
- **元件類型 (Component Type)**: (例如：DC-DC Buck, Sensor, MCU, MOSFET 等)
- **型號解碼 (Part Number Suffix)**: 簡述不同後綴的差異 (如封裝、溫度等級、包裝捲帶)。
- **封裝與尺寸**: 封裝名稱、腳位數及物理尺寸 (mm)。
- **核心功能**: 用一句話描述該元件的精準技術定位。
- **核心特徵**: 條列式總結 3-5 點該元件最突出的技術優勢。

### 2. 電氣特性與系統邊界 (Electrical & Interface)
- **電源軌**: 建議工作電壓 (Min/Typ/Max)、靜態功耗 (Iq)、待機功耗 (Isd)。
- **邏輯電位 (Logic Levels)**: (若有數字介面) 提取 Vih, Vil, Voh, Vol 的門檻電壓。
- **極限值 (Absolute Max)**: 耐壓極限、崩潰電流、結溫極限 (Tj)。
- **防護與可靠性**: ESD 等級 (HBM/CDM)、熱阻參數 (Theta-JA)、保護功能 (OCP, OVP, OTP, UVLO)。

### 3. 關鍵性能參數表 (Performance Table)
使用表格：`| 參數 | 符號 | 條件 (Conditions) | 典型值 | 單位 | 頁碼 |`
- **動態提取規則**: 根據元件類型自動抓取核心參數 (例如電源IC抓 Fsw/Efficiency/..; MOSFET 抓 Vth/Rds_on/Qg/.. ; 感測器抓 Accuracy/Noise/..)。

### 4. 完整的接腳辭典 (Pin Map)
- **嚴格要求**: 絕對禁止省略任何接腳。必須完整列出所有腳位資訊。
- 使用表格：`| Pin # | Name | I/O Type | Description | Internal Pull-up/down | 關鍵連接建議 |`。

### 5. 硬體整合與佈局指引 (HW Design & Layout)
- **關鍵 BOM 要求**: 外部電感 (L) 的飽和電流、電容 (C) 的 ESR 與耐壓建議值。
- **佈局關鍵 (Layout Rules)**: 散熱焊盤 (EPAD) 處理、功率地與信號地隔離、高頻迴路最小化建議。
- **應用電路描述**: 簡述典型參考電路的連接邏輯 (例如：FB 腳位的分壓電阻計算公式)。
- **上電時序 (Power Sequence)**: 是否有 Enable 延遲、Soft-start 時間或特定 Power-up 順序要求。

### 6. 韌體開發與驅動框架 (FW & Register Map)
若此元件具有通訊介面，請生成：
- **通訊參數**: I2C 地址 (7-bit/8-bit)、SPI 極性 (CPOL/CPHA)、最高 Clock 頻率。
- **核心寄存器**: 列出最重要的控制 (Control) 與狀態 (Status) 寄存器地址與位元定義 (Bit-fields)。
- **數據計算**: Raw Data 轉物理單位 (如 ℃, V, g) 的數學公式。
- **C 驅動預覽**: 提供 C 語言的宏定義 (#define) 與初始化虛擬碼。

---
【嚴格格式限制】
1. **禁止 LaTeX 語法**: 一律使用純文字 (如 Vin, Vout, Theta-JA, Tj)。
2. **語系限制**: 除專有名詞外，說明內容一律使用「繁體中文 (zh-TW)」。
3. **數據溯源**: 在關鍵參數表末尾或備註中標註手冊中的來源頁碼。
4. **排除行銷**: 刪除所有「Excellent」、「Industry-leading」等非技術宣傳詞彙。
"""

# ==========================================
# 🧠 核心提煉邏輯
# ==========================================
def distill_file(client, file_path, model_choice, input_dir, output_dir):
    """執行全方位硬體規格提煉，包含 Token 監控與檔案管理"""

    temp_path = file_path.parent / f"processing_{int(time.time())}.pdf"
    shutil.copy(file_path, temp_path)

    gemini_file = None
    try:
        print(f"📡 正在上傳並分析檔案: {file_path.name}...")
        gemini_file = client.files.upload(file=str(temp_path))

        # 等待雲端處理狀態 (含超時保護)
        elapsed = 0
        while gemini_file.state.name == "PROCESSING":
            if elapsed >= FILE_PROCESSING_TIMEOUT_SEC:
                raise TimeoutError(
                    f"雲端檔案處理超時 ({FILE_PROCESSING_TIMEOUT_SEC} 秒)，請稍後重試。"
                )
            time.sleep(2)
            elapsed += 2
            gemini_file = client.files.get(name=gemini_file.name)

        if gemini_file.state.name != "ACTIVE":
            raise RuntimeError(f"雲端檔案狀態異常: {gemini_file.state.name}")

        response = client.models.generate_content(
            model=model_choice, contents=[gemini_file, DISTILL_PROMPT]
        )

        usage = response.usage_metadata
        print(
            f"    📊 [Token 使用量] 輸入: {usage.prompt_token_count} | "
            f"輸出: {usage.candidates_token_count} | 總計: {usage.total_token_count}"
        )

        full_text = response.text
        match = re.search(r"\[FILE_NAME\]:\s*([^\n\r]+)", full_text)

        if match:
            pro_naming = match.group(1).strip()
            pro_naming = re.sub(r'[\\/*?:"<>|]', "", pro_naming)

            final_md_path = output_dir / f"{pro_naming}_summary.md"
            final_content = re.sub(r"\[FILE_NAME\]:.*?\n", "", full_text, count=1).strip()

            with open(final_md_path, "w", encoding="utf-8") as f:
                header = (
                    f"--- 硬體規格提煉報告 ---\n"
                    f"📅 生成日期: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"🤖 分析模型: {model_choice}\n"
                    f"📄 原始參考: {file_path.name}\n"
                    f"------------------------\n\n"
                )
                f.write(header + final_content)

            final_pdf_path = input_dir / f"{pro_naming}.pdf"
            if file_path.resolve() != final_pdf_path.resolve() and not final_pdf_path.exists():
                file_path.rename(final_pdf_path)

            print(f"✅ 成功完成分析並存檔: {pro_naming}")
            return True
        else:
            print("⚠️ 警告：無法識別檔名標籤，請檢查 AI 回傳格式是否正確。")
            return False

    except Exception as e:
        print(f"❌ 處理過程中發生錯誤: {e}")
        return False
    finally:
        if gemini_file is not None:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception:
                pass
        if temp_path.exists():
            temp_path.unlink()


# ==========================================
# 🚀 執行主入口
# ==========================================
def main():
    parser = argparse.ArgumentParser(
        description="AI 硬體規格提煉器 - 本地端版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join([
            "範例:",
            "  python hardware_distiller_local.py",
            "  python hardware_distiller_local.py --input-dir ./pdfs --output-dir ./out",
            "  python hardware_distiller_local.py --model 2",
            "  GEMINI_API_KEY=your_key python hardware_distiller_local.py",
        ])
    )
    parser.add_argument("--input-dir",  type=Path, default=Path("specs"),
                        help="含有 PDF 的資料夾（預設：./specs）")
    parser.add_argument("--output-dir", type=Path, default=Path("summaries"),
                        help="Markdown 輸出資料夾（預設：./summaries）")
    parser.add_argument("--model", choices=["1", "2"], default="1",
                        help="1=gemini-3-flash-preview, 2=gemini-3.1-flash-lite-preview（預設：1）")
    parser.add_argument("--api-key", default=None,
                        help="Gemini API Key（也可設定環境變數 GEMINI_API_KEY）")
    args = parser.parse_args()

    input_dir  = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    # API Key：CLI 參數 > 環境變數 > 互動輸入
    api_key = (
        args.api_key
        or os.environ.get("GEMINI_API_KEY")
        or getpass.getpass("請輸入您的 GEMINI_API_KEY: ")
    )
    if not api_key:
        print("❌ 錯誤：未提供 API KEY。")
        return

    selected_model = AVAILABLE_MODELS[args.model]

    print("--- 🛠️ 環境初始化 ---")
    print(f"📂 輸入目錄: {input_dir}")
    print(f"📂 輸出目錄: {output_dir}")
    print(f"🤖 分析模型: {selected_model}")

    # 初始化目錄
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 清除殘留暫存檔
    for stale in input_dir.glob("processing_*.pdf"):
        stale.unlink()
        print(f"🗑️ 清除殘留暫存檔: {stale.name}")

    # 掃描 PDF（支援大小寫副檔名，保留順序並去重）
    pdf_files = list(
        dict.fromkeys(input_dir.glob("*.pdf")) |
        dict.fromkeys(input_dir.glob("*.PDF"))
    )

    if not pdf_files:
        print(f"\n📂 {input_dir} 中沒有待處理的 PDF 檔案。")
        print("請將 PDF 規格書放入該資料夾後重新執行。")
        return

    print(f"\n📦 開始處理任務，共 {len(pdf_files)} 個檔案...")

    client = genai.Client(api_key=api_key)

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, pdf in enumerate(pdf_files):
        if pdf.name.startswith("processing_"):
            continue

        existing = list(output_dir.glob(f"{pdf.stem}_summary.md"))
        if existing:
            print(f"⏭️  跳過已存在摘要: {pdf.name}")
            skip_count += 1
            continue

        print(f"\n[{i+1}/{len(pdf_files)}] 🚀 啟動引擎分析: {pdf.name}")

        ok = distill_file(client, pdf, selected_model, input_dir, output_dir)
        if ok:
            success_count += 1
        else:
            fail_count += 1

        if i < len(pdf_files) - 1:
            print(f"⏳ 休息 {API_COOLDOWN_SEC} 秒以避免觸發 API 頻率限制...")
            time.sleep(API_COOLDOWN_SEC)

    print(f"\n📊 任務完成：成功 {success_count} | 跳過 {skip_count} | 失敗 {fail_count}")

    # 打包結果
    md_files = list(output_dir.glob("*.md"))
    pdf_files_out = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))

    if not md_files:
        print("⚠️ 無產出檔案，取消打包。")
        return

    zip_path = Path(f"Hardware_Analysis_Package_{int(time.time())}.zip").resolve()
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for md in md_files:
            zipf.write(md, arcname=f"Summaries/{md.name}")
        for pdf in pdf_files_out:
            zipf.write(pdf, arcname=f"Renamed_PDFs/{pdf.name}")

    print(f"\n✨ 任務圓滿結束！結果已打包至:\n   {zip_path}")


if __name__ == "__main__":
    main()
