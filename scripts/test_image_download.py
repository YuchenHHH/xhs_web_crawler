"""
快速验证图片下载链路的小脚本。

用法示例：
python scripts/test_image_download.py \
  --image-url "https://sns-webpic-qc.xhscdn.com/xxx...jpg" \
  --detail-url "https://www.xiaohongshu.com/explore/xxxx" \
  --output /tmp/xhs_test.jpg
"""
import argparse
import asyncio
from pathlib import Path

from core.browser_manager import BrowserManager
from agent.click_nodes import _download_image_from_url


async def main():
    parser = argparse.ArgumentParser(description="Test XHS image download")
    parser.add_argument("--image-url", required=True, help="目标图片的完整 URL")
    parser.add_argument(
        "--detail-url",
        default="https://www.xiaohongshu.com",
        help="作为 Referer 的页面 URL，建议填写图片所属的笔记详情页",
    )
    parser.add_argument(
        "--output",
        default="output/test_image.jpg",
        help="保存文件路径（会自动创建目录）",
    )
    args = parser.parse_args()

    browser = BrowserManager()
    try:
        page = await browser.start()

        # 先进入一个合规的页面，让 page.url 可用作 Referer
        print(f"🌐 打开详情页/Referer: {args.detail_url}")
        await page.goto(args.detail_url, wait_until="domcontentloaded", timeout=30000)

        print(f"🔗 尝试下载: {args.image_url}")
        image_bytes = await _download_image_from_url(page, args.image_url)

        if not image_bytes:
            print("❌ 下载失败，返回 None（可能是 Referer/签名问题）")
            return

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(image_bytes)
        print(f"✅ 下载成功，已保存到 {out_path} （{len(image_bytes)/1024:.1f} KB）")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
