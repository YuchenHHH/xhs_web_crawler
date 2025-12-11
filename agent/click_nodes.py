"""
Minimal LangGraph nodes: screenshot -> coordinates -> sequential clicks.
其他流程在普通 Python 中编排，只把截图与点击留给 LangGraph。
"""
import asyncio
import base64
import io
import random
from typing import Dict, Optional
from playwright.async_api import Page

from agent.state import ClickGraphState
from core.click_verifier import ClickVerifier
from core.som_vision_locator import SoMVisionLocator  # 使用 SoM 方案
from config.settings import XHS_NOTE_DETAIL_SELECTORS
from PIL import Image
from utils.logger import get_logger

logger = get_logger()


async def collect_coordinates_node(state: ClickGraphState) -> Dict:
    """
    使用 SoM 方案识别笔记元素（注入标记 -> 截图 -> LLM识别ID）
    """
    page: Page = state["page"]
    max_notes = state.get("max_notes", 20)
    content_description = state.get("content_description", "")

    # 使用 SoM 方案定位元素
    locator = SoMVisionLocator()
    elements = await locator.locate_note_cards(
        page=page,
        max_notes=max_notes,
        content_description=content_description
    )

    if not elements:
        logger.warning("⚠️  未识别到可点击的笔记元素")
        return {
            "coordinates": [],
            "current_index": 0,
            "screenshot_base64": None,
            "step": "no_elements_found",
        }

    logger.info(f"✅ 识别到 {len(elements)} 个笔记元素")
    for i, elem in enumerate(elements[:3]):
        marker_id = elem.get("marker_id", "?")
        click_pos = f"({elem.get('click_x')}, {elem.get('click_y')})"
        logger.info(f"   {i + 1}. 标记ID={marker_id} 位置={click_pos}")

    return {
        "coordinates": elements,
        "current_index": 0,
        "screenshot_base64": None,
        "step": "elements_collected",
    }


async def click_coordinate_node(state: ClickGraphState) -> Dict:
    """
    对识别到的元素逐个点击（使用 SoM 方案的 ElementHandle）
    """
    page: Page = state["page"]
    coords = state.get("coordinates", [])
    idx = state.get("current_index", 0)
    clicked = state.get("clicked", [])
    failures = state.get("failures", [])
    press_escape = state.get("press_escape_after_click", False)
    arrow_count = state.get("browse_images_arrow_count", 5)
    output_dir = state.get("output_dir", "")
    current_round = state.get("current_round", 1)

    if idx >= len(coords):
        return {"step": "all_clicked"}

    elem_data = coords[idx]
    marker_id = elem_data.get("marker_id", "?")
    element = elem_data.get("element")
    click_x = int(elem_data.get("click_x", 0))
    click_y = int(elem_data.get("click_y", 0))

    logger.info(f"\n🎯 点击第 {idx + 1}/{len(coords)} 个元素: 标记ID={marker_id}")

    try:
        before_url = page.url

        # 使用 ElementHandle 直接点击（100% 准确）
        if element:
            logger.info("   - 📌 使用 SoM ElementHandle 直接点击")
            await element.click()
            logger.info("   - ✅ 已执行元素点击（SoM 方案）")
        else:
            # 降级方案：使用坐标点击
            logger.warning(f"   - ⚠️ 元素不可用，降级为坐标点击 ({click_x}, {click_y})")
            await _show_click_marker(page, click_x, click_y)
            await _human_like_click(page, click_x, click_y)
            logger.info("   - ✅ 已执行坐标点击（降级方案）")

        # 等待页面响应
        await asyncio.sleep(0.2)
        entered_detail = await _verify_detail_entry(page, before_url=before_url)

        # 如果成功进入详情页，按右键浏览图片
        if entered_detail.get("entered", False):
            logger.info(f"   - 📸 进入详情页，开始浏览图片")
            # 生成笔记ID（用于文件夹命名）
            note_id = f"round{current_round}_note{idx+1}_marker{marker_id}"
            saved_images = await _browse_images_with_arrow_keys(
                page,
                arrow_count=arrow_count,
                output_dir=output_dir,
                note_id=note_id,
                state=state
            )
            logger.info(f"   - ✅ 图片浏览完成，保存了{saved_images}张图片")

        if press_escape:
            await _press_escape(page)

        clicked.append(
            {
                "index": idx,
                "marker_id": marker_id,
                "click_x": click_x,
                "click_y": click_y,
                "note_id": elem_data.get("note_id", ""),
                "title": elem_data.get("title", "N/A"),
                "entered_detail": entered_detail.get("entered", False),
                "click_method": "element" if element else "coordinate"
            }
        )

        # 给页面一些反应时间，避免过快
        await asyncio.sleep(0.6)

        return {
            "clicked": clicked,
            "failures": failures,
            "current_index": idx + 1,
            "step": "clicked",
            "last_click_entered": entered_detail.get("entered", False),
        }

    except Exception as e:
        logger.error(f"   - ❌ 点击失败: {e}")
        failures.append(
            {
                "index": idx,
                "marker_id": marker_id,
                "click_x": click_x,
                "click_y": click_y,
                "note_id": elem_data.get("note_id", ""),
                "error": str(e),
            }
        )
        return {
            "clicked": clicked,
            "failures": failures,
            "current_index": idx + 1,
            "step": "click_failed",
            "last_click_entered": False,
        }


async def _human_like_click(page: Page, x: int, y: int):
    """
    简化的类人点击：轻微抖动 + 停顿。
    """
    jitter_x = x + random.randint(-3, 3)
    jitter_y = y + random.randint(-3, 3)

    mid_x = (x + jitter_x) // 2
    mid_y = (y + jitter_y) // 2

    await page.mouse.move(mid_x, mid_y, steps=6)
    await page.mouse.move(jitter_x, jitter_y, steps=6)
    await asyncio.sleep(random.uniform(0.08, 0.2))
    await page.mouse.click(jitter_x, jitter_y)


async def _show_click_marker(page: Page, x: int, y: int):
    """
    在页面标记即将点击的位置，方便观察。
    """
    await page.evaluate(
        """({ x, y }) => {
            const existing = document.getElementById('codex-click-marker');
            if (existing) existing.remove();
            const marker = document.createElement('div');
            marker.id = 'codex-click-marker';
            marker.style.position = 'fixed';
            marker.style.left = `${x}px`;
            marker.style.top = `${y}px`;
            marker.style.transform = 'translate(-50%, -50%)';
            marker.style.width = '24px';
            marker.style.height = '24px';
            marker.style.border = '2px solid red';
            marker.style.borderRadius = '50%';
            marker.style.boxShadow = '0 0 6px rgba(255,0,0,0.7)';
            marker.style.pointerEvents = 'none';
            marker.style.zIndex = 999999;
            document.body.appendChild(marker);
            setTimeout(() => marker.remove(), 1200);
        }""",
        {"x": x, "y": y},
    )


async def _verify_detail_entry(page: Page, before_url: Optional[str] = None) -> Dict:
    """
    粗略检测是否进入详情页（URL 改变或详情选择器出现）。
    """
    detail_url_keywords = ["/explore/", "/discovery/item/"]
    selectors = list(XHS_NOTE_DETAIL_SELECTORS.values())
    current_url = page.url

    if before_url and current_url != before_url and any(k in current_url for k in detail_url_keywords):
        return {"entered": True, "via": "url_changed", "url": current_url}

    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if await locator.is_visible(timeout=500):
                return {"entered": True, "via": f"selector:{sel}", "url": current_url}
        except Exception:
            continue

    return {"entered": False, "via": "not_detected", "url": current_url}


async def _press_escape(page: Page):
    """
    模拟 Esc 退回，用于关闭详情浮层或退出预览。
    """
    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.2)
    except Exception:
        pass


async def _browse_images_with_arrow_keys(
    page: Page,
    arrow_count: int = 5,
    output_dir: str = "",
    note_id: str = "",
    state: Dict = None
) -> int:
    """
    在笔记详情页，按右键浏览图片轮播。
    如果检测到图片重复或高度相似（到达最后一张），自动结束浏览。
    同时保存每张图片到指定目录。

    Args:
        page: Playwright Page 对象
        arrow_count: 按右键的次数（默认5次）
        output_dir: 输出根目录路径
        note_id: 笔记ID，用于创建子目录
        state: 状态字典，用于更新图片总数

    Returns:
        实际保存的图片数量
    """
    from pathlib import Path

    try:
        # 等待详情页稳定
        await asyncio.sleep(0.5)

        # 获取图片限制配置
        max_images = state.get("max_images") if state else None
        total_images = state.get("total_images", 0) if state else 0

        # 创建笔记专属目录（如果提供了参数）
        note_dir = None
        if output_dir and note_id:
            note_dir = Path(output_dir) / note_id
            note_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"   - 📁 创建图片保存目录: {note_dir}")

        # 检查是否已达到图片总数限制
        if max_images and total_images >= max_images:
            logger.warning(f"   - ⚠️ 已达到图片总数限制({max_images}张)，跳过浏览")
            return 0

        # 初始截图（第一张图）
        prev_screenshot = await page.screenshot(type="png")
        prev_hash = _compute_image_hash(prev_screenshot)

        # 保存第一张图片
        saved_count = 0
        if note_dir:
            screenshot_path = note_dir / "image_001.png"
            screenshot_path.write_bytes(prev_screenshot)
            logger.info(f"   - 💾 保存: {screenshot_path.name}")
            saved_count = 1
            if state:
                state["total_images"] = total_images + 1

        actual_browsed = 1  # 实际浏览的图片数（包含首张）

        for i in range(arrow_count):
            # 检查是否已达到图片总数限制
            if state and max_images:
                current_total = state.get("total_images", 0)
                if current_total >= max_images:
                    logger.info(f"   - 🎯 已达到图片总数限制({max_images}张)，停止浏览")
                    break

            # 按右键
            await page.keyboard.press("ArrowRight")
            # 等待图片切换
            await asyncio.sleep(random.uniform(0.4, 0.8))

            # 截图当前页面
            current_screenshot = await page.screenshot(type="png")
            current_hash = _compute_image_hash(current_screenshot)

            # 保存截图（在检查重复之前保存）
            screenshot_path = None
            if note_dir:
                screenshot_path = note_dir / f"image_{str(i + 2).zfill(3)}.png"
                screenshot_path.write_bytes(current_screenshot)
                logger.info(f"   - 💾 保存: {screenshot_path.name}")
                saved_count += 1
                if state:
                    state["total_images"] = state.get("total_images", 0) + 1

            # 对比截图是否相同或高度相似
            is_duplicate = False
            if current_screenshot == prev_screenshot:
                logger.info(f"   - 📸 检测到图片重复，已浏览完所有图片（共 {actual_browsed} 张）")
                is_duplicate = True
            elif prev_hash and current_hash:
                distance = _hamming_distance(prev_hash, current_hash)
                # 阈值越小越严格；8 表示 8x8 dhash 允许少量像素差异
                if distance <= 4:
                    logger.info(f"   - 📸 检测到图片高度相似（dhash 距离={distance}），结束浏览（共 {actual_browsed} 张）")
                    is_duplicate = True

            # 如果检测到重复，删除刚才保存的截图
            if is_duplicate:
                if screenshot_path and screenshot_path.exists():
                    screenshot_path.unlink()
                    logger.info(f"   - 🗑️  删除重复截图: {screenshot_path.name}")
                    saved_count -= 1
                    if state:
                        state["total_images"] = max(0, state.get("total_images", 0) - 1)
                break

            # 更新上一张截图
            prev_screenshot = current_screenshot
            prev_hash = current_hash
            actual_browsed += 1
        else:
            # 正常完成所有浏览
            logger.info(f"   - 📸 完成图片浏览（共按 {arrow_count} 次右键）")

        return saved_count

    except Exception as e:
        logger.warning(f"   - ⚠️ 浏览图片时出错: {e}")
        return saved_count if 'saved_count' in locals() else 0


def _compute_image_hash(image_bytes: bytes, hash_size: int = 8) -> Optional[int]:
    """
    使用 dhash 计算图片的感知哈希，用于相似度判断。
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("L").resize((hash_size + 1, hash_size), Image.LANCZOS)
            pixels = list(img.getdata())

        differences = []
        for row in range(hash_size):
            row_start = row * (hash_size + 1)
            for col in range(hash_size):
                left = pixels[row_start + col]
                right = pixels[row_start + col + 1]
                differences.append(left > right)

        hash_int = 0
        for bit in differences:
            hash_int = (hash_int << 1) | int(bit)
        return hash_int
    except Exception:
        return None


def _hamming_distance(hash1: int, hash2: int) -> int:
    """
    计算两个哈希值的汉明距离。
    """
    return bin(hash1 ^ hash2).count("1")


async def scroll_and_wait_node(state: ClickGraphState) -> Dict:
    """
    完成一轮点击后，滚动页面加载更多内容，为下一轮做准备。
    """
    page: Page = state["page"]
    current_round = state.get("current_round", 1)

    logger.info("\n" + "="*60)
    logger.info(f"📍 第 {current_round} 轮完成，滚动加载更多内容")
    logger.info("="*60)

    try:
        # 滚动页面
        viewport = page.viewport_size or {"width": 1280, "height": 800}
        target_x = int(viewport["width"] * 0.5)
        target_y = int(viewport["height"] * 0.5)

        # 移动鼠标到页面中央
        await page.mouse.move(target_x, target_y)

        # 模拟人类滚动：多次小幅滚动
        scroll_times = random.randint(3, 5)
        for i in range(scroll_times):
            delta_y = random.randint(200, 400)
            await page.mouse.wheel(0, delta_y)
            await asyncio.sleep(random.uniform(0.3, 0.6))

        # 等待内容加载
        await asyncio.sleep(2)

        logger.info("✅ 滚动完成，页面已加载新内容\n")

        return {
            "step": "scrolled_for_next_round",
            "coordinates": [],  # 清空坐标列表，准备重新收集
            "current_index": 0,  # 重置索引
            "current_round": current_round + 1,  # 进入下一轮
        }

    except Exception as e:
        logger.error(f"❌ 滚动失败: {e}\n")
        return {
            "step": "scroll_failed",
            "current_round": current_round + 1,
        }
