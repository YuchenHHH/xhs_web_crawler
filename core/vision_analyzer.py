"""
视觉分析模块
使用 OpenAI GPT-4o Vision API 分析小红书搜索结果页面截图
"""
import os
import json
import base64
import re
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import Page
from openai import AsyncOpenAI
from dotenv import load_dotenv
from config.settings import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS

# 加载 .env 文件
# 优先从项目根目录加载，然后是当前目录
root_env = Path(__file__).parent.parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()  # 从当前目录或父目录查找


class VisionAnalyzer:
    """
    GPT-4o Vision 分析器
    用于分析小红书搜索结果页面截图并提取结构化数据
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Vision 分析器

        Args:
            api_key: OpenAI API Key，如果为 None 则从环境变量读取
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 OPENAI_API_KEY，请设置环境变量或传入参数")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = OPENAI_MODEL

    async def capture_screenshot(self, page: Page) -> str:
        """
        截取当前页面的可视区域并转换为 Base64

        Args:
            page: Playwright Page 对象

        Returns:
            Base64 编码的图片字符串
        """
        print("📸 正在截取当前页面...")

        # 截取当前可视区域（不截全页，保证清晰度）
        screenshot_bytes = await page.screenshot(
            type="png",
            full_page=False  # 只截当前窗口
        )

        # 转换为 Base64
        base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")

        print(f"   - 截图完成，大小: {len(screenshot_bytes) / 1024:.2f} KB")
        return base64_image

    async def analyze_image(
        self,
        base64_image: str,
        custom_prompt: Optional[str] = None
    ) -> Dict:
        """
        使用 GPT-4o 分析截图并提取结构化数据

        Args:
            base64_image: Base64 编码的图片
            custom_prompt: 自定义 Prompt（可选）

        Returns:
            解析后的 JSON 数据（Python Dict）
        """
        print("🤖 正在调用 GPT-4o 进行视觉分析...")

        # 默认 Prompt - 针对小红书搜索结果页面优化
        default_prompt = """
你是一个专业的网页内容分析助手。请仔细分析这张小红书搜索结果页面的截图。

**任务**:
识别截图中所有的"笔记卡片"（通常呈网格布局），并提取以下信息：

1. **title**: 笔记标题（通常在图片下方）
2. **author**: 作者名（如果可见）
3. **likes**: 点赞数（保留原始字符串，如 "1.2万"、"5000" 等）
4. **tags**: 根据笔记封面图片内容，生成 3 个视觉标签（如 "穿搭", "极简", "家居" 等）

**输出格式**:
请返回纯净的 JSON 格式，不要使用 Markdown 代码块。格式如下：

{
  "notes": [
    {
      "title": "笔记标题",
      "author": "作者名",
      "likes": "1.2万",
      "tags": ["标签1", "标签2", "标签3"]
    }
  ]
}

**重要提示**:
- 如果某个字段无法识别，使用 null
- 只返回 JSON，不要添加任何解释文字
- tags 必须基于图片内容生成，而非从文字中提取
"""

        prompt = custom_prompt or default_prompt

        try:
            # 调用 OpenAI Vision API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"  # 高清晰度分析
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=OPENAI_MAX_TOKENS,
                # 部分模型不支持自定义 temperature，使用默认值
            )

            # 提取 LLM 返回的文本
            raw_response = response.choices[0].message.content
            print(f"   - GPT-4o 返回: {len(raw_response)} 字符")

            # 清洗并解析 JSON
            parsed_data = self._clean_and_parse_json(raw_response)

            return parsed_data

        except Exception as e:
            print(f"❌ GPT-4o 分析失败: {e}")
            raise

    def _clean_and_parse_json(self, raw_text: str) -> Dict:
        """
        清洗 LLM 返回的文本并解析为 JSON

        处理以下情况:
        1. Markdown 代码块: ```json ... ```
        2. 多余的空白字符
        3. 非法字符

        Args:
            raw_text: LLM 返回的原始文本

        Returns:
            解析后的 Python Dictionary

        Raises:
            ValueError: 如果无法解析为 JSON
        """
        print("🧹 正在清洗并解析 JSON...")

        # 去除 Markdown 代码块标记
        cleaned = raw_text.strip()

        # 移除 ```json 和 ```
        if cleaned.startswith("```"):
            # 找到第一个换行符后的内容
            lines = cleaned.split("\n")
            # 移除第一行（```json）和最后一行（```）
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        # 再次检查是否有残留的代码块标记
        cleaned = re.sub(r'^```\w*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)

        try:
            parsed = json.loads(cleaned)
            print(f"   - ✅ JSON 解析成功，共 {len(parsed.get('notes', []))} 条笔记")
            return parsed

        except json.JSONDecodeError as e:
            print(f"   - ❌ JSON 解析失败: {e}")
            print(f"   - 原始文本: {raw_text[:200]}...")
            raise ValueError(f"无法解析 LLM 返回的 JSON: {e}")

    async def analyze_page(self, page: Page) -> Dict:
        """
        便捷方法: 截图 + 分析一步完成

        Args:
            page: Playwright Page 对象

        Returns:
            解析后的笔记数据
        """
        # 1. 截图
        base64_image = await self.capture_screenshot(page)

        # 2. 分析
        result = await self.analyze_image(base64_image)

        return result


# ============================================================
# 独立使用示例 (可直接运行此文件进行测试)
# ============================================================

async def demo_standalone():
    """
    演示如何独立使用 VisionAnalyzer
    """
    from playwright.async_api import async_playwright

    print("\n" + "="*60)
    print("🧪 VisionAnalyzer 独立测试")
    print("="*60 + "\n")

    # 初始化分析器
    analyzer = VisionAnalyzer()

    # 启动浏览器
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800}
    )
    page = await context.new_page()

    try:
        # TODO: 在这里填入你的登录和搜索代码
        # ================================================
        # 示例: 访问小红书搜索结果页
        await page.goto("https://www.xiaohongshu.com/search_result?keyword=穿搭", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=10000)
        # ================================================

        # 执行视觉分析
        result = await analyzer.analyze_page(page)

        # 打印结果
        print("\n" + "="*60)
        print("📊 分析结果")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 保存为文件（可选）
        with open("analysis_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("\n💾 结果已保存到 analysis_result.json")

    finally:
        await browser.close()
        await p.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_standalone())
