"""
下载小红书笔记中的视频（无需手动点击播放）。

步骤：
1) 通过 Playwright 打开笔记详情页（使用已有 auth.json 保持登录）。
2) 监听网络响应，捕获视频的实际请求地址（通常是 m3u8 或 mp4）。
3) 把捕获的地址下载到本地。

用法示例：
python scripts/download_xhs_video.py \
    --url "https://www.xiaohongshu.com/explore/xxxxx" \
    --output video.mp4

说明：
- 如果捕获到的是 m3u8，会先把 m3u8 保存到文件；再尝试直接拉取为 mp4。
- 如果直下 mp4 失败，可使用本地 ffmpeg:  ffmpeg -i captured.m3u8 -c copy output.mp4
"""
import argparse
import asyncio
import os
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from playwright.async_api import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.browser_manager import BrowserManager  # noqa: E402


MEDIA_HINTS = ["video", "mpegurl", ".m3u8", ".mp4"]


def _looks_like_media(url: str, content_type: str) -> bool:
    url_l = url.lower()
    ctype = (content_type or "").lower()
    return any(hint in url_l for hint in MEDIA_HINTS) or any(
        hint in ctype for hint in MEDIA_HINTS
    )


def _download(url: str, headers: Dict[str, str], dest: Path) -> None:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    dest.write_bytes(data)


async def capture_video(url: str, wait_ms: int = 8000) -> List[Dict]:
    """
    打开笔记详情页，捕获视频请求。
    返回 [{url, headers, content_type}]
    """
    manager = BrowserManager()
    page = await manager.start()

    captured: List[Dict] = []

    async def handle_response(resp: Response):
        try:
            ctype = resp.headers.get("content-type", "")
            if not _looks_like_media(resp.url, ctype):
                return
            req_headers = dict(resp.request.headers)
            captured.append(
                {
                    "url": resp.url,
                    "content_type": ctype,
                    "headers": {
                        # 只保留可能需要的头
                        "cookie": req_headers.get("cookie", ""),
                        "referer": req_headers.get("referer", ""),
                        "user-agent": req_headers.get("user-agent", ""),
                    },
                }
            )
            print(f"🎯 捕获媒体: {resp.url} (content-type={ctype})")
        except Exception as e:
            print(f"⚠️ 捕获响应时出错: {e}")

    page.on("response", handle_response)

    try:
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(wait_ms)
    finally:
        page.off("response", handle_response)
        await manager.close()

    return captured


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="从小红书笔记捕获并下载视频")
    parser.add_argument("--url", required=True, help="笔记详情页 URL（/explore/...）")
    parser.add_argument(
        "--output",
        default="downloaded_video.mp4",
        help="输出文件路径（mp4 或 m3u8）",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=8000,
        help="在详情页等待捕获媒体的毫秒数（默认 8000）",
    )
    args = parser.parse_args()

    print(f"🚀 打开笔记: {args.url}")
    captured = asyncio.run(capture_video(args.url, args.wait_ms))

    if not captured:
        print("❌ 未捕获到视频资源，可能需要登录或页面未加载到视频。")
        return

    target = captured[0]
    media_url = target["url"]
    ctype = target["content_type"].lower()
    headers = {k: v for k, v in target["headers"].items() if v}

    out_path = Path(args.output)

    # 先保存原始流（m3u8 或 mp4）
    try:
        if ".m3u8" in media_url or "mpegurl" in ctype:
            if out_path.suffix.lower() != ".m3u8":
                # 先写 m3u8，再告诉用户用 ffmpeg 转码
                m3u8_path = out_path.with_suffix(".m3u8")
                print(f"📥 捕获到 m3u8，保存到 {m3u8_path}")
                _download(media_url, headers, m3u8_path)
                print(
                    "ℹ️ 可用 ffmpeg 将其转为 mp4，例如：\n"
                    f"   ffmpeg -i {m3u8_path} -c copy {out_path}"
                )
            else:
                print(f"📥 保存 m3u8 到 {out_path}")
                _download(media_url, headers, out_path)
        else:
            print(f"📥 捕获到直链视频，下载到 {out_path}")
            _download(media_url, headers, out_path)
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return

    print("✅ 完成")


if __name__ == "__main__":
    main()
