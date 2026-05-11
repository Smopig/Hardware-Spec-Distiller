#!/usr/bin/env python3
"""
Hardware Spec Distiller - Multi-provider batch script.

This is the optional advanced mode for the hardware-spec-distiller Skill.
The default Skill mode is run by Claude Code directly (no API key required);
use this script only for headless batch processing or CI pipelines.

Supported providers (auto-detected by env var):
  - anthropic : ANTHROPIC_API_KEY  (uses claude-* models, native PDF input)
  - gemini    : GEMINI_API_KEY     (uses gemini-* models, Files API upload)
  - openai    : OPENAI_API_KEY     (uses gpt-* models, native PDF input)

CLI:
  python distill.py --input-dir ./pdfs --output-dir ./out
  python distill.py --provider anthropic --model claude-opus-4-7
  python distill.py --rename-pdf       # also rename source PDFs (irreversible)
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import sys
import time
from pathlib import Path


API_COOLDOWN_SEC = 8
FILE_PROCESSING_TIMEOUT_SEC = 120

PROVIDER_DEFAULT_MODEL = {
    "anthropic": "claude-opus-4-5",
    "gemini": "gemini-2.5-pro",
    "openai": "gpt-4.1",
}

FILE_NAME_PATTERNS = [
    re.compile(r"<<FILE_NAME>>:\s*(.+?)\s*<<END>>"),
    re.compile(r"\[FILE_NAME\]:\s*([^\n\r]+)"),
]


def load_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "PROMPT.md"
    return prompt_path.read_text(encoding="utf-8")


def detect_provider(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    sys.exit(
        "❌ 未偵測到任何 API Key。請設定 ANTHROPIC_API_KEY / GEMINI_API_KEY / "
        "OPENAI_API_KEY 其中之一，或改用 Skill 預設模式（讓 Claude Code 直接處理）。"
    )


def distill_anthropic(pdf_path: Path, prompt: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        sys.exit("❌ 缺少 anthropic 套件，請執行：pip install anthropic")

    client = anthropic.Anthropic()
    pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")

    msg = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    usage = msg.usage
    print(
        f"    📊 [Token] input={usage.input_tokens} output={usage.output_tokens} "
        f"total={usage.input_tokens + usage.output_tokens}"
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def distill_gemini(pdf_path: Path, prompt: str, model: str) -> str:
    try:
        from google import genai
    except ImportError:
        sys.exit("❌ 缺少 google-genai 套件，請執行：pip install google-genai")

    client = genai.Client()
    temp = pdf_path.parent / f"processing_{int(time.time())}.pdf"
    shutil.copy(pdf_path, temp)
    gfile = None
    try:
        gfile = client.files.upload(file=str(temp))
        elapsed = 0
        while gfile.state.name == "PROCESSING":
            if elapsed >= FILE_PROCESSING_TIMEOUT_SEC:
                raise TimeoutError("Gemini 雲端檔案處理超時")
            time.sleep(2)
            elapsed += 2
            gfile = client.files.get(name=gfile.name)
        if gfile.state.name != "ACTIVE":
            raise RuntimeError(f"檔案狀態異常: {gfile.state.name}")

        resp = client.models.generate_content(model=model, contents=[gfile, prompt])
        u = resp.usage_metadata
        print(
            f"    📊 [Token] input={u.prompt_token_count} "
            f"output={u.candidates_token_count} total={u.total_token_count}"
        )
        return resp.text
    finally:
        if gfile is not None:
            try:
                client.files.delete(name=gfile.name)
            except Exception:
                pass
        if temp.exists():
            temp.unlink()


def distill_openai(pdf_path: Path, prompt: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("❌ 缺少 openai 套件，請執行：pip install openai")

    client = OpenAI()
    with open(pdf_path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="user_data")

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_file", "file_id": uploaded.id},
                        {"type": "input_text", "text": prompt},
                    ],
                }
            ],
        )
        u = resp.usage
        print(
            f"    📊 [Token] input={u.input_tokens} output={u.output_tokens} "
            f"total={u.total_tokens}"
        )
        return resp.output_text
    finally:
        try:
            client.files.delete(uploaded.id)
        except Exception:
            pass


PROVIDER_FN = {
    "anthropic": distill_anthropic,
    "gemini": distill_gemini,
    "openai": distill_openai,
}


def parse_file_name(text: str) -> str | None:
    for pat in FILE_NAME_PATTERNS:
        m = pat.search(text)
        if m:
            name = m.group(1).strip()
            name = re.sub(r'[\\/*?:"<>|]', "", name)
            return name
    return None


def strip_file_name_line(text: str) -> str:
    for pat in FILE_NAME_PATTERNS:
        text = pat.sub("", text, count=1)
    return text.strip()


def process_one(
    pdf: Path,
    prompt: str,
    provider: str,
    model: str,
    input_dir: Path,
    output_dir: Path,
    rename_pdf: bool,
) -> bool:
    print(f"📡 分析: {pdf.name}  (provider={provider}, model={model})")
    fn = PROVIDER_FN[provider]
    try:
        text = fn(pdf, prompt, model)
    except Exception as e:
        print(f"❌ 失敗: {e}")
        return False

    pro_name = parse_file_name(text)
    body = strip_file_name_line(text)

    if not pro_name:
        print("⚠️  未解析到 <<FILE_NAME>> 標籤，回退使用原 PDF 名稱。")
        pro_name = pdf.stem

    md_path = output_dir / f"{pro_name}_summary.md"
    header = (
        "--- 硬體規格提煉報告 ---\n"
        f"📅 生成日期: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🤖 分析模型: {provider}:{model}\n"
        f"📄 原始參考: {pdf.name}\n"
        "------------------------\n\n"
    )
    md_path.write_text(header + body, encoding="utf-8")
    print(f"✅ 已存檔: {md_path}")

    if rename_pdf:
        target = input_dir / f"{pro_name}.pdf"
        if pdf.resolve() != target.resolve() and not target.exists():
            pdf.rename(target)
            print(f"🔁 已重新命名 PDF → {target.name}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Hardware Spec Distiller - multi-provider batch script."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("docs/specs"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/summaries"))
    parser.add_argument(
        "--provider", choices=["anthropic", "gemini", "openai"], default=None
    )
    parser.add_argument("--model", default=None, help="覆蓋預設 model id")
    parser.add_argument(
        "--rename-pdf",
        action="store_true",
        help="處理完成後就地重新命名原 PDF（不可逆，預設關閉）",
    )
    args = parser.parse_args()

    provider = detect_provider(args.provider)
    model = args.model or PROVIDER_DEFAULT_MODEL[provider]

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    for stale in input_dir.glob("processing_*.pdf"):
        stale.unlink()

    pdfs = sorted(
        set(input_dir.glob("*.pdf")) | set(input_dir.glob("*.PDF")),
        key=lambda p: p.name,
    )
    if not pdfs:
        print(f"📂 {input_dir} 沒有待處理的 PDF。")
        return

    prompt = load_prompt()
    print(f"📂 input={input_dir}  output={output_dir}")
    print(f"🔧 provider={provider}  model={model}  files={len(pdfs)}")

    ok = skip = fail = 0
    for i, pdf in enumerate(pdfs):
        if (output_dir / f"{pdf.stem}_summary.md").exists():
            print(f"⏭️  跳過已存在: {pdf.name}")
            skip += 1
            continue
        print(f"\n[{i+1}/{len(pdfs)}] {pdf.name}")
        if process_one(pdf, prompt, provider, model, input_dir, output_dir, args.rename_pdf):
            ok += 1
        else:
            fail += 1
        if i < len(pdfs) - 1:
            time.sleep(API_COOLDOWN_SEC)

    print(f"\n📊 完成：成功 {ok} | 跳過 {skip} | 失敗 {fail}")


if __name__ == "__main__":
    main()
