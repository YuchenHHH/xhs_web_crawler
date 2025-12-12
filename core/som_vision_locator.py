"""
基于 Set-of-Marks 的视觉定位器
使用数字标记提高识别准确率
"""
import os
import base64
import json
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import Page
from openai import AsyncOpenAI

from config.settings import OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_MAX_RETRIES, OPENAI_RETRY_DELAY
from core.som_marker import SoMMarker


class SoMVisionLocator:
    """
    使用 Set-of-Marks 方案的视觉定位器
    不再预测坐标，而是识别数字标记 ID
    """

    def __init__(self, selectors: List[str], api_key: Optional[str] = None):
        """
        初始化 SoM Vision Locator

        Args:
            selectors: 笔记卡片的 CSS 选择器列表（必需参数）
            api_key: OpenAI API Key（可选，默认从环境变量读取）
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("需要提供 OPENAI_API_KEY")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = OPENAI_MODEL
        self.marker = SoMMarker(selectors=selectors)

    async def locate_note_cards(
        self,
        page: Page,
        max_notes: int = 20,
        content_description: str = ""
    ) -> List[Dict]:
        """
        使用 SoM 方案识别笔记卡片

        Args:
            page: Playwright Page 对象
            max_notes: 最多识别的笔记数量
            content_description: 内容描述，用于过滤笔记（只选择符合描述的笔记）

        Returns:
            笔记位置列表，格式:
            [{
                "marker_id": 1,
                "element": ElementHandle,
                "click_x": 0,  # 保留兼容性，但不再使用
                "click_y": 0
            }]
        """
        if content_description:
            print(f"🎯 使用 SoM 方案识别笔记（最多 {max_notes} 个，过滤条件: {content_description[:50]}...）")
        else:
            print(f"🎯 使用 SoM 方案识别笔记（最多 {max_notes} 个）...")

        try:
            # 1. 注入标记
            element_map = await self.marker.inject_markers(page, max_notes)

            if not element_map:
                print("❌ 未找到可标记的笔记元素")
                return []

            # 2. 等待标记渲染
            await asyncio.sleep(0.5)

            # 3. 截图（带标记）
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")

            # 4. 构建 Prompt（包含内容过滤）
            prompt = self._build_som_prompt(max_notes, len(element_map), content_description)

            # 5. 调用 GPT-4o Vision（带重试机制）
            print("   - 正在调用 GPT-4o Vision 识别标记...")

            marker_ids = []
            for attempt in range(OPENAI_MAX_RETRIES):
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
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ],
                        response_format={"type": "json_object"},
                        max_completion_tokens=OPENAI_MAX_TOKENS,
                    )

                    # 6. 解析响应
                    result_text = response.choices[0].message.content or ""

                    if not result_text or result_text.strip() == "":
                        raise ValueError("GPT-4o 返回了空响应")

                    marker_ids = self._parse_marker_ids(result_text)

                    if marker_ids:
                        # 成功解析到标记，跳出重试循环
                        print(f"✅ GPT-4o 识别到 {len(marker_ids)} 个标记: {marker_ids}")
                        break
                    else:
                        # 解析失败，但可能是合法的空结果
                        if attempt < OPENAI_MAX_RETRIES - 1:
                            print(f"⚠️  GPT-4o 未识别到标记（第 {attempt + 1}/{OPENAI_MAX_RETRIES} 次尝试），{OPENAI_RETRY_DELAY}秒后重试...")
                            await asyncio.sleep(OPENAI_RETRY_DELAY)
                        else:
                            print(f"⚠️  GPT-4o 在 {OPENAI_MAX_RETRIES} 次尝试后仍未识别到标记")

                except Exception as e:
                    if attempt < OPENAI_MAX_RETRIES - 1:
                        print(f"⚠️  GPT-4o 调用失败（第 {attempt + 1}/{OPENAI_MAX_RETRIES} 次尝试）: {e}")
                        print(f"   - {OPENAI_RETRY_DELAY}秒后重试...")
                        await asyncio.sleep(OPENAI_RETRY_DELAY)
                    else:
                        print(f"❌ GPT-4o 在 {OPENAI_MAX_RETRIES} 次尝试后仍然失败: {e}")
                        raise

            # 7. 移除标记（保持页面整洁）
            await self.marker.remove_markers(page)
            print("🧹 已清除 SoM 标记")

            # 8. 构建返回结果
            results = []
            for marker_id in marker_ids:
                element = self.marker.get_element_by_id(marker_id)
                if not element:
                    print(f"   ⚠️  标记 ID {marker_id} 没有对应的元素")
                    continue

                # 获取元素的中心坐标（用于兼容性）
                try:
                    box = await element.bounding_box()
                    click_x = int(box["x"] + box["width"] / 2) if box else 0
                    click_y = int(box["y"] + box["height"] / 2) if box else 0
                except:
                    click_x, click_y = 0, 0

                results.append({
                    "marker_id": marker_id,
                    "element": element,
                    "click_x": click_x,
                    "click_y": click_y,
                    "index": len(results),
                    # 兼容字段
                    "bounding_box": {},
                    "title": "",
                    "note_id": ""
                })

            print(f"🎯 成功定位 {len(results)} 个笔记元素")

            return results

        except Exception as e:
            print(f"❌ SoM 识别失败: {e}")
            import traceback
            traceback.print_exc()

            # 清理标记
            try:
                await self.marker.remove_markers(page)
            except:
                pass

            return []

    def _build_som_prompt(self, max_notes: int, total_marks: int, content_description: str = "") -> str:
        """
        构建 SoM 方案的 Prompt

        Args:
            max_notes: 请求的最大笔记数
            total_marks: 实际标记的数量
            content_description: 内容描述，用于过滤笔记

        Returns:
            Prompt 字符串
        """
        # 基础 prompt
        prompt = f"""你是一个网页元素识别专家。这是一张小红书搜索结果页面的截图。

**重要信息**：
- 图片中每个笔记卡片的左上角都有一个**金黄色圆形数字标记**（带橙红色边框）
- 这些数字从 1 到 {total_marks}
- 你的任务是识别这些数字标记"""

        # 如果有内容描述，添加内容过滤要求
        if content_description:
            prompt += f"""

**🎯 内容过滤要求（非常重要）**：
{content_description}

**你必须**：
1. 仔细观察每个标记对应的笔记封面图和标题
2. 只选择**符合上述内容描述**的笔记标记
3. 如果笔记内容与描述不符，**不要选择该标记**
4. 优先选择封面图和描述最匹配的笔记
5. **宁可少选，不要选错**"""

        # 继续添加任务要求
        prompt += f"""

**任务要求**：
1. 找出图片中所有的金黄色数字标记
2. """

        if content_description:
            prompt += f"根据上述内容过滤要求，只选择符合描述的笔记标记\n3. "

        prompt += f"""按照从左到右、从上到下的顺序，列出最多 {max_notes} 个标记的数字
{'4' if content_description else '3'}. **只返回数字 ID**，不要返回坐标或其他信息

**笔记卡片特征**（必须满足）：
- 每个标记对应一个笔记卡片
- 笔记卡片包含**较大的封面图片**（通常是美食照片、室内照片等实际内容）
- 封面图片下方有标题文字
- 标记位于笔记卡片的左上角
- 呈网格或瀑布流布局排列

**❌ 严格排除以下元素（不要选择这些标记）**：
- ❌ "大家都在搜"区域的推荐词条（通常在搜索框下方）
- ❌ "猜你想搜"、"相关搜索"、"热门搜索"等搜索推荐
- ❌ 导航栏按钮（首页、发现、我等）
- ❌ 搜索框或搜索建议
- ❌ 个人头像、用户名等个人信息区域
- ❌ 顶部或底部的固定导航栏
- ❌ 侧边栏或悬浮按钮
- ❌ 任何纯文字列表（没有大封面图的）"""

        if content_description:
            prompt += f"""
- ❌ **内容不符合过滤要求的笔记**"""

        prompt += f"""

**识别技巧**：
- 真正的笔记卡片有**较大的正方形或竖版封面图**
- 搜索推荐词条通常只有小图标或纯文字，**没有大封面图**
- "大家都在搜"通常位于页面顶部，呈横向排列的小卡片
- 笔记卡片通常有点赞数、评论数等互动数据"""

        if content_description:
            prompt += f"""
- 通过笔记的**封面图**和**标题**判断内容是否符合过滤要求"""

        prompt += f"""

**输出格式**（严格 JSON）：
```json
{{
  "marker_ids": [1, 2, 3, 4, 5]
}}
```

**注意**：
- 只返回你在图片中**真实看到**的金黄色圆形数字标记"""

        if content_description:
            prompt += f"""
- **优先考虑内容过滤要求**，只选择符合描述的笔记"""

        prompt += f"""
- 只选择真正的**笔记卡片**上的标记，严格排除搜索推荐区域
- 按照笔记的视觉顺序排列（从左到右，从上到下）
- 最多返回 {max_notes} 个 ID
- 如果某个区域没有标记，不要猜测或编造数字
- **宁可少选，不要错选"""

        if content_description:
            prompt += f"""
- **如果没有符合内容描述的笔记，可以返回空数组 []**"""

        prompt += """
"""
        return prompt

    def _parse_marker_ids(self, response_text: str) -> List[int]:
        """
        解析 GPT-4o 返回的标记 ID 列表

        Args:
            response_text: GPT-4o 返回的文本

        Returns:
            标记 ID 列表
        """
        try:
            # 提取 JSON
            json_text = response_text.strip()

            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            # 解析 JSON
            data = json.loads(json_text)

            # 提取 marker_ids
            marker_ids = data.get("marker_ids", [])

            # 验证和过滤
            valid_ids = []
            for id in marker_ids:
                try:
                    id_int = int(id)
                    if id_int > 0:
                        valid_ids.append(id_int)
                except:
                    continue

            return valid_ids

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析失败: {e}")
            print(f"原始响应: {response_text[:500]}...")
            return []

        except Exception as e:
            print(f"⚠️  解析标记 ID 失败: {e}")
            return []
