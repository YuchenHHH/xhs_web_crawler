"""
视觉定位器 - 使用 GPT-4o Vision 识别页面元素位置
用于模拟真人鼠标点击操作
"""
import os
import base64
import json
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import Page
from openai import AsyncOpenAI
from config.settings import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS


class VisionLocator:
    """
    使用 GPT-4o Vision API 识别页面上的笔记卡片位置
    返回可点击的坐标信息
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 VisionLocator

        Args:
            api_key: OpenAI API Key（如未提供则从环境变量读取）
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("需要提供 OPENAI_API_KEY（环境变量或构造参数）")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = OPENAI_MODEL  # 支持视觉分析的模型

    async def locate_note_cards(
        self,
        page: Page,
        max_notes: int = 5
    ) -> List[Dict]:
        """
        识别页面上的笔记卡片位置

        Args:
            page: Playwright Page 对象
            max_notes: 最多识别的笔记数量

        Returns:
            笔记位置列表，每个元素格式:
            {
                "index": 0,
                "click_x": 300,
                "click_y": 450,
                "bounding_box": {"x": 200, "y": 350, "width": 200, "height": 250},
            }
        """
        print(f"🔍 使用 GPT-4o Vision 识别笔记位置（最多 {max_notes} 个）...")

        try:
            # 1. 截取当前页面
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")

            # 2. 获取视口尺寸（用于坐标验证）
            viewport_size = page.viewport_size
            viewport_width = viewport_size["width"]
            viewport_height = viewport_size["height"]

            print(f"   - 页面视口尺寸: {viewport_width}x{viewport_height}")

            # 3. 构建提示词
            prompt = self._build_prompt(max_notes, viewport_width, viewport_height)

            # 4. 调用 GPT-4o Vision
            print("   - 正在调用 GPT-4o Vision 分析页面...")

            max_retries = 3
            last_error = ""

            for attempt in range(1, max_retries + 1):
                try:
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
                                            "detail": "high"  # 高质量分析
                                        }
                                    }
                                ]
                            }
                        ],
                        response_format={"type": "json_object"},
                        max_completion_tokens=OPENAI_MAX_TOKENS,
                        # 部分模型不支持自定义 temperature，使用默认值
                    )

                    # 5. 解析响应
                    result_text = response.choices[0].message.content or ""
                    if not result_text.strip():
                        raise ValueError("模型返回空内容")

                    print(f"   - GPT-4o 返回内容长度: {len(result_text)} 字符")

                    # 6. 提取 JSON
                    note_positions = self._parse_response(result_text)

                    # 7. 过滤掉可能的误识别（如导航栏、个人中心按钮等）
                    filtered_positions = self._filter_invalid_positions(
                        note_positions,
                        viewport_width,
                        viewport_height
                    )

                    print(f"✅ 成功识别 {len(filtered_positions)} 个笔记位置（原始: {len(note_positions)}）")
                    for i, pos in enumerate(filtered_positions[:3]):
                        print(f"   {i + 1}. 坐标: ({pos['click_x']}, {pos['click_y']}) - {pos.get('title', 'N/A')[:30]}")

                    return filtered_positions

                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries:
                        print(f"   - ⚠️  视觉定位尝试 {attempt} 失败，重试中... 原因: {last_error}")
                        await asyncio.sleep(0.6)
                        continue
                    else:
                        raise

        except Exception as e:
            print(f"❌ 视觉定位失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _build_prompt(self, max_notes: int, viewport_width: int, viewport_height: int) -> str:
        """
        构建 GPT-4o Vision 提示词

        Args:
            max_notes: 最大笔记数量
            viewport_width: 视口宽度
            viewport_height: 视口高度

        Returns:
            提示词字符串
        """
        prompt = f"""你是一个网页元素定位专家。请分析这张小红书搜索结果页面的截图，识别出页面上的笔记卡片位置。

**任务要求**：
1. 识别页面上最多 {max_notes} 个笔记卡片（通常是带有封面图的矩形区域）
2. 对于每个笔记卡片，提供：
   - 可点击的中心坐标 (x, y)
   - 边界框信息 (x, y, width, height)
   - 笔记标题（如果图片中能看到）
   - 笔记ID（如果图片中有URL或ID信息）

**笔记卡片的特征**（必须满足）：
- 包含一张较大的封面图片（通常是内容截图或照片）
- 图片下方有笔记标题文字
- 可能有作者头像（小圆形图标）和作者名
- 可能有点赞数、评论数等互动数据
- 呈网格布局或瀑布流布局排列
- 尺寸相对较大（通常宽度 > 150px，高度 > 200px）

**必须排除的元素**（这些不是笔记卡片）：
- ❌ 导航栏按钮（如"首页"、"发现"、"我"等顶部按钮）
- ❌ 个人头像按钮（右上角的圆形头像）
- ❌ 搜索框
- ❌ 底部导航栏的图标
- ❌ 单独的小图标或按钮（没有标题和内容的）
- ❌ 侧边栏或悬浮按钮
- ❌ 广告横幅或提示框

**坐标系统**：
- 页面左上角为 (0, 0)
- 页面宽度: {viewport_width}px
- 页面高度: {viewport_height}px
- 所有坐标必须在这个范围内

**输出格式**：
请严格按照以下 JSON 格式返回（不要添加任何其他文字）：

```json
{{
  "notes": [
    {{
      "index": 0,
      "click_x": 300,
      "click_y": 450,
      "bounding_box": {{
        "x": 200,
        "y": 350,
        "width": 200,
        "height": 250
      }},
      "title": "笔记标题",
      "note_id": "ID（如果能识别）"
    }}
  ]
}}
```
"""
        return prompt

    def _parse_response(self, response_text: str) -> List[Dict]:
        """
        解析 GPT-4o Vision 的响应

        Args:
            response_text: GPT-4o 返回的文本

        Returns:
            笔记位置列表
        """
        try:
            # 尝试提取 JSON（可能被包裹在 ```json ``` 中）
            json_text = response_text.strip()

            # 移除可能的代码块标记
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            # 解析 JSON
            data = json.loads(json_text)

            # 提取笔记列表
            notes = data.get("notes", [])

            # 验证和清理数据
            cleaned_notes = []
            for note in notes:
                if "click_x" in note and "click_y" in note:
                    if int(note["click_x"]) < 300:
                        continue
                    cleaned_notes.append({
                        "index": note.get("index", len(cleaned_notes)),
                        "click_x": int(note["click_x"]),
                        "click_y": int(note["click_y"]),
                        "bounding_box": note.get("bounding_box", {}),
                        "title": note.get("title", ""),
                        "note_id": note.get("note_id", "")
                    })

            return cleaned_notes

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析失败: {e}")
            print(f"原始响应: {response_text[:500]}...")
            return []

        except Exception as e:
            print(f"⚠️  响应解析失败: {e}")
            return []

    def _filter_invalid_positions(
        self,
        positions: List[Dict],
        viewport_width: int,
        viewport_height: int
    ) -> List[Dict]:
        """
        过滤掉可能的误识别位置（如导航栏、个人中心按钮等）

        Args:
            positions: 原始识别的位置列表
            viewport_width: 视口宽度
            viewport_height: 视口高度

        Returns:
            过滤后的位置列表
        """
        filtered = []

        # 定义排除区域
        TOP_NAV_HEIGHT = 80  # 顶部导航栏高度（像素）
        BOTTOM_NAV_HEIGHT = 80  # 底部导航栏高度（像素）
        RIGHT_EDGE_WIDTH = 300  # 右侧边缘宽度（个人中心按钮通常在右上角）

        for pos in positions:
            click_x = pos.get('click_x', 0)
            click_y = pos.get('click_y', 0)
            bbox = pos.get('bounding_box', {})
            width = bbox.get('width', 0)
            height = bbox.get('height', 0)
            title = pos.get('title', '').strip()

            # 过滤条件 1: 排除顶部导航栏区域
            if click_y < TOP_NAV_HEIGHT:
                print(f"   ⚠️  过滤: 位于顶部导航栏 ({click_x}, {click_y})")
                continue

            # 过滤条件 2: 排除右上角区域（个人中心按钮）
            if click_x > (viewport_width - RIGHT_EDGE_WIDTH) and click_y < TOP_NAV_HEIGHT * 2:
                print(f"   ⚠️  过滤: 位于右上角区域 ({click_x}, {click_y})")
                continue

            # 过滤条件 2.5: 排除底部导航栏区域
            if click_y > (viewport_height - BOTTOM_NAV_HEIGHT):
                print(f"   ⚠️  过滤: 位于底部导航栏 ({click_x}, {click_y})")
                continue

            # 过滤条件 3: 标题包含特定关键词（导航按钮或搜索推荐）
            EXCLUDED_KEYWORDS = ['首页', '发现', '我', '消息', '搜索', '购物车', '关注', '相关搜索', '大家都在搜', '猜你想搜', '热门搜索']
            if title and any(keyword in title for keyword in EXCLUDED_KEYWORDS):
                # 但如果标题很长（超过4个字），可能是笔记标题包含这些词，不过滤
                if len(title) <= 4:
                    print(f"   ⚠️  过滤: 标题疑似导航按钮 '{title}' ({click_x}, {click_y})")
                    continue

            # 通过所有过滤条件，保留
            filtered.append(pos)

        return filtered
