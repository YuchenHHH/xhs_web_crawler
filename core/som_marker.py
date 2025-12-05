"""
Set-of-Marks (SoM) 标记注入器
在页面上为可点击元素添加视觉数字标记，提高 LLM 识别准确率
"""
from typing import Dict, List, Optional
from playwright.async_api import Page, ElementHandle


class SoMMarker:
    """
    Set-of-Marks 标记注入器
    在截图前给页面元素添加醒目的数字标记，让 LLM 直接返回数字 ID
    """

    def __init__(self, selectors: Optional[List[str]] = None):
        """
        初始化 SoM 标记注入器

        Args:
            selectors: 目标元素的 CSS 选择器列表
        """
        from config.settings import XHS_NOTE_CARD_SELECTORS
        self.selectors = selectors or XHS_NOTE_CARD_SELECTORS
        self.selector_str = ",".join(self.selectors)
        self.element_map: Dict[int, ElementHandle] = {}

    async def inject_markers(self, page: Page, max_marks: int = 20) -> Dict[int, ElementHandle]:
        """
        在页面上注入数字标记

        Args:
            page: Playwright Page 对象
            max_marks: 最多标记的元素数量（默认20）

        Returns:
            字典映射 {标记ID: ElementHandle}
        """
        print(f"🔢 正在注入 SoM 标记（最多 {max_marks} 个）...")

        # 1. 查询所有符合条件的笔记元素
        elements = await page.query_selector_all(self.selector_str)

        if not elements:
            print("⚠️  未找到任何笔记元素")
            return {}

        # 2. 过滤掉不可见或无效的元素
        visible_elements = []
        for element in elements:
            try:
                # 检查元素是否在视口内且可见
                is_visible = await element.is_visible()
                if not is_visible:
                    continue

                # 获取边界框
                box = await element.bounding_box()
                if not box:
                    continue

                # 过滤掉太小的元素（可能是图标或按钮）
                if box["width"] < 100 or box["height"] < 100:
                    continue

                # 过滤掉极左侧的导航栏（x < 80，通常是侧边栏图标）
                # 注意：笔记内容区域可能从 x=200 左右开始，所以不要过滤太多
                if box["x"] < 80:
                    continue

                visible_elements.append((element, box))

            except Exception as e:
                print(f"   - 检查元素可见性时出错: {e}")
                continue

        # 3. 限制数量
        visible_elements = visible_elements[:max_marks]

        if not visible_elements:
            print("⚠️  没有符合条件的可见元素")
            return {}

        print(f"   - 找到 {len(visible_elements)} 个可标记的笔记元素")

        # 4. 注入标记到页面
        await self._inject_marker_overlay(page, visible_elements)

        # 5. 构建 ID -> ElementHandle 映射
        self.element_map = {
            i + 1: element
            for i, (element, _) in enumerate(visible_elements)
        }

        print(f"✅ 成功注入 {len(self.element_map)} 个 SoM 标记")

        return self.element_map

    async def _inject_marker_overlay(self, page: Page, elements_with_boxes: List):
        """
        使用 JavaScript 在页面上绘制标记覆盖层

        Args:
            page: Playwright Page 对象
            elements_with_boxes: [(ElementHandle, BoundingBox), ...]
        """
        # 准备标记数据（只需要位置信息，不需要 ElementHandle）
        markers_data = [
            {
                "id": i + 1,
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"]
            }
            for i, (_, box) in enumerate(elements_with_boxes)
        ]

        # 注入 JavaScript 绘制标记
        await page.evaluate(
            """(markers) => {
                // 移除旧的覆盖层（如果存在）
                const oldOverlay = document.getElementById('som-overlay');
                if (oldOverlay) oldOverlay.remove();

                // 创建新的覆盖层容器
                const overlay = document.createElement('div');
                overlay.id = 'som-overlay';
                overlay.style.position = 'fixed';
                overlay.style.top = '0';
                overlay.style.left = '0';
                overlay.style.width = '100%';
                overlay.style.height = '100%';
                overlay.style.pointerEvents = 'none';  // 不阻挡鼠标事件
                overlay.style.zIndex = '999999';

                // 为每个元素创建标记
                markers.forEach(marker => {
                    const label = document.createElement('div');
                    label.className = 'som-marker';
                    label.textContent = marker.id;

                    // 样式：亮黄色背景，黑色粗体文字，左上角定位
                    label.style.position = 'absolute';
                    label.style.left = `${marker.x + 5}px`;  // 左上角偏移5px
                    label.style.top = `${marker.y + 5}px`;
                    label.style.width = '40px';
                    label.style.height = '40px';
                    label.style.backgroundColor = '#FFD700';  // 金黄色
                    label.style.color = '#000';
                    label.style.fontSize = '24px';
                    label.style.fontWeight = 'bold';
                    label.style.fontFamily = 'Arial, sans-serif';
                    label.style.display = 'flex';
                    label.style.alignItems = 'center';
                    label.style.justifyContent = 'center';
                    label.style.borderRadius = '50%';  // 圆形标记
                    label.style.border = '3px solid #FF4500';  // 橙红色边框
                    label.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';
                    label.style.pointerEvents = 'none';

                    overlay.appendChild(label);
                });

                document.body.appendChild(overlay);
            }""",
            markers_data
        )

    async def remove_markers(self, page: Page):
        """
        移除页面上的所有 SoM 标记

        Args:
            page: Playwright Page 对象
        """
        try:
            await page.evaluate(
                """() => {
                    const overlay = document.getElementById('som-overlay');
                    if (overlay) overlay.remove();
                }"""
            )
            print("🧹 已清除 SoM 标记")
        except Exception as e:
            print(f"⚠️  清除标记时出错: {e}")

    def get_element_by_id(self, marker_id: int) -> Optional[ElementHandle]:
        """
        根据标记 ID 获取对应的元素

        Args:
            marker_id: 标记 ID

        Returns:
            ElementHandle 或 None
        """
        return self.element_map.get(marker_id)

    def clear_map(self):
        """
        清空元素映射
        """
        self.element_map.clear()
