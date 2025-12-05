"""
批量图片筛选脚本：根据描述保留符合内容的图片。

用法示例：
    python scripts/batch_filter_images.py \\
        --input-dir output/板豆腐_20251205_153136 \\
        --description "只保留包含成品菜肴的图片，排除原料、包装、菜单、文字截图" \\
        --output-dir filtered_images
"""
import argparse
import asyncio
import base64
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from openai import AsyncOpenAI


SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _build_prompt(description: str) -> str:
    return f"""你是图片审核助手，需要判断图片是否符合用户描述。

【用户描述】：
{description}

【任务】：
1. 仔细观察图片内容，判断是否与用户描述高度相关。
2. 如果图片明显不符合描述（题材不符、纯文字截图、与主题无关的物体/场景），标记为不保留。
3. 对模糊、裁剪过小、无法辨认的图片，宁可不保留。

【输出】：
返回严格 JSON：
{{
  "keep": true,   // true=保留，false=丢弃
  "reason": "简要说明判断依据"
}}"""


async def _judge_image(
    client: AsyncOpenAI,
    model: str,
    image_path: Path,
    prompt: str,
) -> Tuple[bool, str]:
    """调用 GPT-4o 判断是否保留图片。"""
    base64_image = _encode_image(image_path)
    response = await client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
    )
    raw = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
        keep = bool(parsed.get("keep"))
        reason = str(parsed.get("reason", "")).strip()
    except Exception:
        keep = False
        reason = f"解析失败: {raw[:80]}"
    return keep, reason


async def _process_images(
    image_paths: List[Path],
    description: str,
    output_dir: Path,
    concurrency: int,
    model: str,
) -> List[Dict]:
    prompt = _build_prompt(description)
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    semaphore = asyncio.Semaphore(concurrency)
    results: List[Dict] = []

    async def _worker(path: Path):
        async with semaphore:
            keep, reason = await _judge_image(client, model, path, prompt)
            if keep:
                target = output_dir / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            results.append(
                {
                    "file": str(path),
                    "keep": keep,
                    "reason": reason,
                }
            )

    await asyncio.gather(*[_worker(p) for p in image_paths])
    return results


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="批量筛选图片，保留符合描述的文件。")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="待筛选图片所在目录（会递归扫描）",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="图片内容描述，符合的将被保留",
    )
    parser.add_argument(
        "--output-dir",
        default="filtered_images",
        help="输出目录，保存保留的图片及结果摘要",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="并发调用数，过大可能触发限流",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o"),
        help="使用的 OpenAI 模型，默认取环境变量 OPENAI_MODEL 或 gpt-4o",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    # 收集图片
    image_paths = [
        p for p in input_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTS
    ]
    if not image_paths:
        print("⚠️ 未找到任何图片文件")
        return

    print(f"🎯 描述: {args.description}")
    print(f"📂 输入: {input_dir} （共 {len(image_paths)} 张）")
    print(f"📁 输出: {output_dir}")
    print(f"🧠 模型: {args.model}")
    print(f"🚦 并发: {args.concurrency}\n")

    results = asyncio.run(
        _process_images(
            image_paths=image_paths,
            description=args.description,
            output_dir=output_dir,
            concurrency=args.concurrency,
            model=args.model,
        )
    )

    # 写出摘要
    summary_path = output_dir / "filter_results.json"
    summary = {
        "description": args.description,
        "model": args.model,
        "kept": len([r for r in results if r["keep"]]),
        "total": len(results),
        "details": results,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n✅ 筛选完成，保留 {summary['kept']} / {summary['total']} 张")
    print(f"📝 结果已写入: {summary_path}")


if __name__ == "__main__":
    main()
