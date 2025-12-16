"""
笔记详情提取模块
使用 OpenAI GPT-4o Vision API 分析小红书笔记详情页截图并提取结构化数据
"""
import os
import json
import base64
import re
from pathlib import Path
from typing import Dict, Optional
from playwright.async_api import Page
from openai import AsyncOpenAI
from dotenv import load_dotenv
from config.settings import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS

# 加载 .env 文件
root_env = Path(__file__).parent.parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()


class NoteDetailExtractor:
    """
    笔记详情页提取器
    用于分析小红书笔记详情页截图并提取结构化数据
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化笔记详情提取器

        Args:
            api_key: OpenAI API Key，如果为 None 则从环境变量读取
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 OPENAI_API_KEY，请设置环境变量或传入参数")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = OPENAI_MODEL

    async def extract_from_page(self, page: Page) -> Dict:
        """
        从当前笔记详情页提取数据

        Args:
            page: Playwright Page 对象（当前在笔记详情页）

        Returns:
            提取的结构化数据字典
        """
        print("   - 📸 截取笔记详情页...")

        # 截取并分析
        result = await self._capture_and_analyze(page)

        return result

    async def _capture_and_analyze(self, page: Page) -> Dict:
        """
        截图并使用 GPT-4o Vision 进行分析

        Args:
            page: Playwright Page 对象

        Returns:
            解析后的数据字典
        """
        # 1. 截取当前可视区域
        screenshot_bytes = await page.screenshot(
            type="png",
            full_page=False  # 只截当前视口
        )

        base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
        print(f"   - 截图完成，大小: {len(screenshot_bytes) / 1024:.2f} KB")

        # 2. 调用 GPT-4o Vision 分析
        print("   - 🤖 分析笔记内容...")

        prompt = self._build_extraction_prompt()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的小红书内容分析助手，擅长从笔记截图中提取结构化数据。"
                    },
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
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=OPENAI_MAX_TOKENS,
                # 部分模型不支持自定义 temperature，使用默认值
            )

            # 3. 解析响应
            content = response.choices[0].message.content.strip()
            print(f"   - ✅ GPT-4o 分析完成")

            # 4. 清理并解析 JSON
            parsed_data = self._clean_and_parse_json(content)

            return parsed_data

        except Exception as e:
            print(f"   - ❌ GPT-4o 分析失败: {e}")
            # 返回空数据结构
            return {
                "title": "",
                "author": "",
                "publish_date": "",
                "content_text": "",
                "likes": "",
                "comments": "",
                "collects": "",
                "tags": [],
                "image_urls": []
            }

    def _build_extraction_prompt(self) -> str:
        """
        构建针对笔记详情页的提取提示词

        Returns:
            Prompt 字符串
        """
        return """
请仔细分析这张小红书笔记详情页的截图，提取以下信息：

**提取字段**:
1. **title**: 笔记标题（通常在顶部显著位置）
2. **author**: 作者昵称（通常在头像旁边）
3. **publish_date**: 发布日期（如果可见，格式如 "2024-12-03" 或 "3天前"）
4. **content_text**: 笔记正文内容（尽可能完整提取，保留换行）
5. **likes**: 点赞数（如 "1.2万", "5000" 等，保留原始格式）
6. **comments**: 评论数（如 "230", "1.5k" 等）
7. **collects**: 收藏数（如果可见）
8. **tags**: 笔记标签列表（从界面上提取的话题标签，如 ["#穿搭", "#OOTD"]）
9. **image_urls**: 如果页面中有图片链接，尽量提取（可选，暂时可以留空数组）

**输出格式**:
请返回纯净的 JSON 格式，不要使用 Markdown 代码块。格式如下：

{
  "title": "笔记标题",
  "author": "作者昵称",
  "publish_date": "发布日期",
  "content_text": "笔记正文内容",
  "likes": "点赞数",
  "comments": "评论数",
  "collects": "收藏数",
  "tags": ["标签1", "标签2"],
  "image_urls": []
}

**注意事项**:
- 如果某个字段在截图中不可见或无法识别，请使用空字符串 "" 或空数组 []
- 保持原始数据格式（如 "1.2万" 不要转换为 12000）
- content_text 尽可能完整，如果截图只显示部分内容，提取可见部分即可
- 不要添加任何额外的文字说明，只返回 JSON
"""

    def _clean_and_parse_json(self, raw_content: str) -> Dict:
        """
        清理 GPT 响应并解析为 JSON

        Args:
            raw_content: GPT 返回的原始字符串

        Returns:
            解析后的 Python 字典
        """
        try:
            # 1. 移除 Markdown 代码块标记
            cleaned = raw_content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]  # 移除 ```json
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]  # 移除 ```

            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]  # 移除尾部 ```

            cleaned = cleaned.strip()

            # 2. 使用正则去除其他可能的 Markdown 残留
            cleaned = re.sub(r'^```.*\n', '', cleaned)
            cleaned = re.sub(r'\n```$', '', cleaned)

            # 3. 解析 JSON
            data = json.loads(cleaned)

            return data

        except json.JSONDecodeError as e:
            print(f"   - ⚠️  JSON 解析失败: {e}")
            print(f"   - 原始内容:\n{raw_content}")

            # 返回默认空结构
            return {
                "title": "",
                "author": "",
                "publish_date": "",
                "content_text": raw_content, 
                "likes": "",
                "comments": "",
                "collects": "",
                "tags": [],
                "image_urls": []
            }
