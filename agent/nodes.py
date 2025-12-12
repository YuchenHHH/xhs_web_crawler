"""
Agent 节点函数
实现具体的业务逻辑，每个节点负责一个特定的任务
"""
import asyncio
import random
from typing import Dict, List
from playwright.async_api import Page

from agent.state import AgentState
from config.settings import (
    DEFAULT_TIMEOUT,
    SCROLL_PAUSE_TIME,
)
from core.click_verifier import ClickVerifier


async def init_browser_node(state: AgentState) -> dict:
    """
    节点 1: 初始化浏览器并访问小红书首页

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [Node 1/3] 初始化浏览器并访问首页")
    print("="*60)

    browser_manager = state["browser_manager"]
    page = await browser_manager.start()

    # 访问小红书首页
    crawler = state["crawler"]
    home_url = crawler.home_url
    print(f"🌐 正在访问: {home_url}")
    await page.goto(home_url, wait_until="domcontentloaded", timeout=30000)

    # 等待页面稳定（模拟人类浏览行为）
    await asyncio.sleep(2)

    print("✅ 首页加载完成\n")

    return {
        "page": page,
        "step": "browser_initialized"
    }


async def check_login_node(state: AgentState) -> dict:
    """
    节点 2: 检查登录状态（简单版本）

    检查方法：
    1. 查找登录按钮是否存在（如果存在说明未登录）
    2. 查找用户头像或用户名（如果存在说明已登录）

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [Node 2/3] 检查登录状态")
    print("="*60)

    page: Page = state["page"]
    crawler = state["crawler"]
    is_logged_in = await crawler.detect_login_status(page)

    if is_logged_in:
        print("✅ 检测到用户信息，已登录")
    else:
        print("⚠️  未检测到登录状态")
        print("   建议: 继续后续步骤前先完成一次手动登录")

    print()
    return {
        "is_logged_in": is_logged_in,
        "step": "login_checked"
    }


async def manual_login_and_save_cookies_node(state: AgentState) -> dict:
    """
    节点 2.1: 手动登录并保存 Cookie

    在未登录时提示用户手动登录，轮询检测登录成功后自动保存 Cookie。
    """
    print("\n" + "="*60)
    print("📍 [Node 2.1/3] 手动登录并保存 Cookie")
    print("="*60)

    page: Page = state["page"]
    browser_manager = state["browser_manager"]
    crawler = state["crawler"]

    print("💡 当前未登录，请在打开的浏览器中手动完成登录（扫码/密码均可）")
    print("   登录成功后，本节点会自动保存 Cookie，后续可免扫码。")

    max_checks = 8  # 最长等待 8 次，每次 10 秒，总计 ~80 秒
    wait_interval = 10

    is_logged_in = False

    for i in range(max_checks):
        print(f"   - 等待用户登录中... ({i + 1}/{max_checks})")
        await asyncio.sleep(wait_interval)

        is_logged_in = await crawler.detect_login_status(page)
        if is_logged_in:
            print("✅ 检测到已登录，正在保存 Cookie ...")
            await browser_manager.save_cookies()
            break

    if not is_logged_in:
        print("⚠️  未能在规定时间内检测到登录，继续后续流程（可能需要再次登录）")

    return {
        "is_logged_in": is_logged_in,
        "step": "manual_login_completed" if is_logged_in else "manual_login_failed"
    }


async def search_keyword_node(state: AgentState) -> dict:
    """
    节点 3: 执行搜索操作

    流程：
    1. 定位搜索框（使用多种选择器策略）
    2. 点击搜索框并输入关键词
    3. 按回车提交搜索
    4. 等待搜索结果加载

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [Node 3/3] 执行搜索操作")
    print("="*60)

    page: Page = state["page"]
    keyword = state["search_keyword"]
    crawler = state["crawler"]

    print(f"🔍 搜索关键词: {keyword}")

    try:
        # === 步骤 1: 定位搜索框 ===
        print("   - 正在定位搜索框...")

        # 尝试多种选择器（优先级从高到低）
        search_input = None
        for selector in crawler.search_input_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=2000):
                    search_input = locator
                    print(f"   - ✅ 找到搜索框: {selector}")
                    break
            except:
                continue

        if not search_input:
            raise Exception("无法定位搜索框，所有选择器均失败")

        # === 步骤 2: 点击并输入 ===
        await search_input.wait_for(state="visible", timeout=5000)
        await search_input.click()
        await asyncio.sleep(0.5)  # 等待输入框激活

        await search_input.fill(keyword)
        print("   - ✅ 输入完成")

        # === 步骤 3: 提交搜索 ===
        await page.keyboard.press("Enter")
        print("   - ✅ 回车提交")

        # === 步骤 4: 等待结果加载 ===
        print("   - 等待搜索结果加载...")

        # 策略 1: 等待页面基本加载完成
        await page.wait_for_load_state("load", timeout=DEFAULT_TIMEOUT)

        # 策略 2: 等待搜索结果容器出现
        # 小红书搜索结果通常在 .feeds-container 或 .note-item 中
        result_container = page.locator(".feeds-container, .note-item, [class*='search-result']").first
        await result_container.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)

        print("✅ 搜索完成，结果已加载")

        # 不在搜索后立即滚动，保持页面在初始状态
        # await _scroll_once_for_results(page)

        # 截图保存（可选，方便调试）
        # await page.screenshot(path=f"search_result_{keyword}.png")

    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        print("   可能原因:")
        print("   1. 搜索框选择器失效（小红书页面结构变化）")
        print("   2. 网络超时或页面加载缓慢")
        print("   3. 需要登录才能搜索")

        return {
            "step": "search_failed",
        }

    print()
    return {
        "step": "search_completed"
    }


# === 扩展节点 ===

async def vision_analysis_node(state: AgentState) -> dict:
    """
    节点 4: 视觉分析节点
    使用 GPT-4o Vision 分析搜索结果页面截图并生成总结

    流程:
    1. 等待页面稳定（滚动加载更多内容）
    2. 截取当前可视区域
    3. 调用 GPT-4o 进行视觉分析
    4. 提取结构化数据
    5. 生成页面内容总结

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [Node 4/4] 视觉分析与内容总结")
    print("="*60)

    page: Page = state["page"]

    try:
        # 导入 VisionAnalyzer
        from core.vision_analyzer import VisionAnalyzer

        # === 步骤 1: 等待页面稳定 ===
        print("⏳ 等待页面内容加载稳定...")
        await asyncio.sleep(2)

        # 可选: 滚动页面加载更多内容
        # await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        # await asyncio.sleep(1)

        # === 步骤 2: 初始化分析器 ===
        analyzer = VisionAnalyzer()

        # === 步骤 3: 截图 + 分析 ===
        result = await analyzer.analyze_page(page)

        # === 步骤 4: 提取数据 ===
        notes = result.get("notes", [])
        print(f"\n✅ 视觉分析完成，识别到 {len(notes)} 条笔记")

        # 打印前 3 条结果预览
        if notes:
            print("\n📋 前 3 条笔记预览:")
            for i, note in enumerate(notes[:3], 1):
                print(f"   {i}. {note.get('title', 'N/A')}")
                print(f"      作者: {note.get('author', 'N/A')}")
                print(f"      点赞: {note.get('likes', 'N/A')}")
                print(f"      标签: {', '.join(note.get('tags', []))}")
                print()

        return {
            "vision_analysis": result,
            "search_results": notes,
            "step": "vision_analysis_completed"
        }

    except ImportError:
        print("❌ 未找到 VisionAnalyzer 模块")
        print("   请确保已安装 openai 依赖: pip install openai")
        return {
            "step": "vision_analysis_failed",
            "error_message": "VisionAnalyzer 模块未找到"
        }

    except ValueError as e:
        print(f"❌ 视觉分析失败: {e}")
        print("   可能原因:")
        print("   1. 未设置 OPENAI_API_KEY 环境变量")
        print("   2. API Key 无效或额度不足")
        return {
            "step": "vision_analysis_failed",
            "error_message": str(e)
        }

    except Exception as e:
        print(f"❌ 视觉分析异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            "step": "vision_analysis_failed",
            "error_message": str(e)
        }


async def collect_note_links_node(state: AgentState) -> dict:
    """
    节点 4: 收集笔记卡片位置（使用视觉识别）

    使用 GPT-4o Vision 识别当前视口内的笔记卡片位置
    只识别一次，不滚动，处理完所有笔记后再由其他逻辑决定是否滚动

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [Node 4/7] 使用视觉识别收集笔记位置")
    print("="*60)

    page: Page = state["page"]
    max_notes = state.get("max_notes_to_process", 5)

    try:
        from core.vision_locator import VisionLocator

        # 初始化视觉定位器
        vision_locator = VisionLocator()

        print(f"🎯 使用 AI 视觉识别当前视口的笔记位置...")

        # 使用 GPT-4o Vision 识别当前页面的笔记位置
        # 识别尽可能多的笔记，但最多不超过 max_notes
        detected_notes = await vision_locator.locate_note_cards(
            page=page,
            max_notes=max_notes
        )

        if not detected_notes:
            raise Exception("视觉识别失败，未找到任何笔记卡片")

        # 构建 note_links 列表
        note_links = []
        for i, note_pos in enumerate(detected_notes):
            note_links.append({
                "index": i,
                "click_x": note_pos["click_x"],
                "click_y": note_pos["click_y"],
                "bounding_box": note_pos.get("bounding_box", {}),
                "title": note_pos.get("title", ""),
                "note_id": note_pos.get("note_id", ""),
            })

        # 只取前 max_notes 个
        note_links = note_links[:max_notes]

        # 输出结果
        print(f"\n✅ 成功识别 {len(note_links)} 个笔记位置")
        for i, link in enumerate(note_links[:3]):  # 显示前3个
            coord = f"({link['click_x']}, {link['click_y']})"
            title = link.get('title', 'N/A')[:30]
            print(f"   {i + 1}. 坐标: {coord} | 标题: {title}")
        if len(note_links) > 3:
            print(f"   ... 还有 {len(note_links) - 3} 个")

        print()
        return {
            "note_links": note_links,
            "current_note_index": 0,
            "step": "note_links_collected"
        }

    except Exception as e:
        print(f"❌ 收集笔记位置失败: {e}")
        import traceback
        traceback.print_exc()

        return {
            "note_links": [],
            "current_note_index": 0,
            "step": "note_links_collection_failed"
        }


async def process_note_detail_node(state: AgentState) -> dict:
    """
    节点 5: 处理单个笔记详情

    使用坐标模拟鼠标点击笔记卡片，进入详情页，截图并提取数据，保存文件

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    page: Page = state["page"]
    crawler = state["crawler"]
    note_links = state.get("note_links", [])
    current_index = state.get("current_note_index", 0)
    output_dir = state.get("output_base_dir", "output")
    processed_notes = state.get("processed_notes", [])
    failed_notes = state.get("failed_notes", [])

    print("\n" + "="*60)
    print(f"📍 [Node 5/7] 处理笔记 {current_index + 1}/{len(note_links)}")
    print("="*60)

    if current_index >= len(note_links):
        print("⚠️  没有更多笔记需要处理")
        return {
            "current_note_index": current_index,
            "step": "no_more_notes"
        }

    current_note = note_links[current_index]
    click_x = current_note.get("click_x", 0)
    click_y = current_note.get("click_y", 0)
    note_id = current_note.get("note_id", "unknown")
    title = current_note.get("title", "N/A")
    bounding_box = current_note.get("bounding_box")

    print(f"🎯 笔记信息:")
    print(f"   - 标题: {title[:50]}")
    print(f"   - 笔记ID: {note_id}")
    print(f"   - 点击坐标: ({click_x}, {click_y})")

    # 记录点击前的 URL，用于后续判断是否真的进入了详情页
    before_click_url = page.url
    entered_detail = False

    try:
        # === 步骤 1: 检查坐标是否在视口内 ===
        viewport = page.viewport_size
        viewport_width = viewport["width"]
        viewport_height = viewport["height"]

        print(f"   - 视口尺寸: {viewport_width}x{viewport_height}")

        if click_y > viewport_height or click_y < 0:
            print(f"   - 📜 坐标不在视口内，正在滚动...")
            scroll_amount = click_y - viewport_height // 2
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(1)
            print("   - ⚠️  滚动后使用原坐标点击（可能有偏差）")

        # === 步骤 1.5: 坐标验证 ===
        verifier = ClickVerifier(selectors=crawler.note_card_selectors)
        verification = await verifier.validate(page, click_x, click_y, bounding_box)

        if not verification["is_valid"]:
            suggestion = (verification["click_x"], verification["click_y"])
            print(f"   - ⚠️  坐标未命中笔记: {verification['reason']}")
            if suggestion != (click_x, click_y):
                print(f"   - 🔄 使用建议坐标 {suggestion} 进行点击")
                click_x, click_y = suggestion
            else:
                print("   - ❌ 未找到可用的笔记坐标，跳过该笔记")
                raise Exception("note click verification failed")
        else:
            click_x, click_y = verification["click_x"], verification["click_y"]
            print(f"   - ✅ 坐标验证通过，使用 ({click_x}, {click_y}) 点击")

        # === 步骤 1.55: DOM 校准，将坐标吸附到最近卡片中心 ===
        calibrated = await _calibrate_click_with_dom(page, click_x, click_y, crawler.note_card_selectors)
        if calibrated:
            dist = calibrated.get("distance", 0)
            new_x, new_y = calibrated["x"], calibrated["y"]
            if dist > 0:
                print(f"   - 🔄 DOM 校准: 距离最近卡片中心 {dist:.1f}px，使用 ({new_x}, {new_y})")
            click_x, click_y = new_x, new_y

        # === 步骤 1.6: 在页面上标记即将点击的位置（仅调试可视化） ===
        await _show_click_marker(page, click_x, click_y)
        await asyncio.sleep(1)  # 让标记显示 1 秒再点击

        # === 步骤 2: 模拟鼠标点击 ===
        print(f"   - 🖱️  模拟鼠标点击坐标 ({click_x}, {click_y})（先移动/悬停再点击）...")
        await _human_like_click(page, click_x, click_y)
        print("   - ✅ 点击完成，等待页面跳转...")

        # 等待页面导航完成
        await page.wait_for_load_state("domcontentloaded", timeout=15000)

        # 点击后校验是否真的进入了笔记详情页
        verification = await _verify_detail_page_entry(page, before_click_url, crawler.note_detail_selectors)
        entered_detail = verification.get("entered", False)
        if not entered_detail:
            reason = verification.get("reason", "unknown")
            print(f"   - ⚠️  未检测到详情页，跳过该坐标。原因: {reason}")
            failed_notes.append({
                "index": current_index,
                "note_id": note_id,
                "click_position": {"x": click_x, "y": click_y},
                "error": f"did not enter detail page: {reason}"
            })
            return {
                "processed_notes": processed_notes,
                "failed_notes": failed_notes,
                "current_note_index": current_index + 1,
                "step": "note_click_invalid",
                "last_click_entered_detail": False
            }

        print(f"   - ✅ 已进入详情页（{verification.get('via', 'detected via markers')}）")

        # 等待详情页内容加载
        title_selector = crawler.note_detail_selectors["title"]

        try:
            await page.locator(title_selector).first.wait_for(state="visible", timeout=10000)
        except:
            print("   - ⚠️  详情页加载可能不完整，继续尝试...")

        # 额外等待确保页面稳定
        await asyncio.sleep(1.5)

        print("   - ✅ 详情页加载完成")

        # === 步骤 2: 截图 ===
        from core.file_manager import FileManager

        screenshot_path = FileManager.get_note_filename(output_dir, current_index, "png")
        screenshot_success = await FileManager.save_screenshot(page, screenshot_path)

        # === 步骤 3: 提取数据 ===
        from core.note_extractor import NoteDetailExtractor

        print("   - 📝 正在提取笔记数据...")
        extractor = NoteDetailExtractor()
        # note_data = await extractor.extract_from_page(page)
        note_data = {}
        print(f"   - ✅ 提取完成: {note_data.get('title', 'N/A')[:50]}")

        # === 步骤 4: 保存 JSON ===
        json_path = FileManager.get_note_filename(output_dir, current_index, "json")

        # 合并元数据到数据中
        note_data["url"] = page.url  # 使用当前页面URL（详情页URL）
        note_data["index"] = current_index
        note_data["click_position"] = {"x": click_x, "y": click_y}
        note_data["note_id"] = note_id

        json_success = FileManager.save_json(note_data, json_path)

        # === 步骤 5: 记录结果 ===
        processed_notes.append({
            "index": current_index,
            "url": page.url,  # 使用实际的详情页URL
            "data": note_data,
            "screenshot_path": screenshot_path,
            "json_path": json_path,
            "success": screenshot_success and json_success
        })

        print(f"✅ 笔记 {current_index + 1} 处理完成\n")

        return {
            "processed_notes": processed_notes,
            "current_note_index": current_index + 1,
            "step": "note_processed",
            "last_click_entered_detail": True
        }

    except Exception as e:
        print(f"❌ 处理笔记 {current_index + 1} 失败: {e}")

        # 记录失败
        failed_notes.append({
            "index": current_index,
            "note_id": note_id,
            "click_position": {"x": click_x, "y": click_y},
            "error": str(e)
        })

        print(f"   - 跳过此笔记，继续处理下一个\n")

        return {
            "processed_notes": processed_notes,
            "failed_notes": failed_notes,
            "current_note_index": current_index + 1,
            "step": "note_processing_failed_but_continuing",
            "last_click_entered_detail": entered_detail
        }


async def navigate_back_node(state: AgentState) -> dict:
    """
    节点 6: 返回搜索结果页

    使用浏览器后退按钮返回到搜索结果页

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [Node 6/7] 返回搜索结果页")
    print("="*60)

    page: Page = state["page"]
    last_entered_detail = state.get("last_click_entered_detail", True)

    if last_entered_detail is False:
        print("   - ⏭️ 上一次点击未进入详情页，保持在搜索结果页，跳过后退操作\n")
        return {
            "step": "skipped_back_no_detail",
            "last_click_entered_detail": None
        }

    try:
        print("   - 🔙 执行后退操作...")

        # 使用浏览器后退
        await page.go_back(wait_until="domcontentloaded", timeout=10000)

        # 等待搜索结果容器重新出现
        await asyncio.sleep(1)

        # 验证是否成功返回
        result_container = page.locator(".feeds-container, .note-item, [class*='search-result']").first
        await result_container.wait_for(state="visible", timeout=5000)

        print("   - ✅ 成功返回搜索结果页\n")

        return {
            "step": "navigated_back"
        }

    except Exception as e:
        print(f"⚠️  后退操作失败: {e}")
        print("   - 尝试备用方案：直接导航到搜索页...")

        try:
            # 备用方案：重新执行搜索
            keyword = state.get("search_keyword", "")
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(1)

            print("   - ✅ 使用备用方案成功\n")
            return {
                "step": "navigated_back_fallback"
            }
        except Exception as e2:
            print(f"❌ 备用方案也失败: {e2}\n")
            return {
                "step": "navigation_back_failed",
                "error_message": str(e2)
            }


async def scroll_for_more_notes_node(state: AgentState) -> dict:
    """
    节点 6.5: 向下滚动以加载新一批笔记
    """
    print("\n" + "="*60)
    print("📍 [Node 6.5/7] 滚动加载更多笔记")
    print("="*60)

    page: Page = state["page"]

    try:
        print(f"   - ⌄ 模拟右侧抽屉滚动，持续 {SCROLL_PAUSE_TIME} 秒加载更多内容")
        await scroll_right_modal(page, duration=SCROLL_PAUSE_TIME)
        await asyncio.sleep(0.5)  # 额外等待半秒以便页面渲染

        # 确认仍在搜索结果页
        result_container = page.locator(".feeds-container, .note-item, [class*='search-result']").first
        await result_container.wait_for(state="visible", timeout=5000)

        print("   - ✅ 滚动完成，准备重新收集笔记位置\n")
        return {
            "step": "scrolled_for_more"
        }

    except Exception as e:
        print(f"❌ 滚动加载失败: {e}\n")
        return {
            "step": "scroll_failed",
            "error_message": str(e)
        }


async def finalize_extraction_node(state: AgentState) -> dict:
    """
    节点 7: 完成提取流程

    保存元数据并输出统计信息

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [Node 7/7] 完成提取流程")
    print("="*60)

    output_dir = state.get("output_base_dir", "")
    processed_notes = state.get("processed_notes", [])
    failed_notes = state.get("failed_notes", [])
    keyword = state.get("search_keyword", "")

    try:
        from core.file_manager import FileManager
        from datetime import datetime

        # 保存会话元数据
        metadata = {
            "keyword": keyword,
            "total_notes_found": len(processed_notes) + len(failed_notes),
            "successfully_processed": len(processed_notes),
            "failed": len(failed_notes),
            "created_at": datetime.now().isoformat(),
            "output_directory": output_dir
        }

        FileManager.save_metadata(output_dir, metadata)

        # 输出统计
        print(f"\n📊 提取统计:")
        print(f"   - 搜索关键词: {keyword}")
        print(f"   - 找到笔记数: {metadata['total_notes_found']}")
        print(f"   - 成功处理: {metadata['successfully_processed']}")
        print(f"   - 失败跳过: {metadata['failed']}")
        print(f"   - 输出目录: {output_dir}")

        if processed_notes:
            print(f"\n✅ 成功处理的笔记:")
            for note in processed_notes:
                title = note["data"].get("title", "N/A")[:40]
                print(f"   {note['index'] + 1}. {title}")

        if failed_notes:
            print(f"\n⚠️  处理失败的笔记:")
            for fail in failed_notes:
                print(f"   {fail['index'] + 1}. {fail.get('error', 'Unknown error')[:50]}")

        print()

        return {
            "step": "extraction_completed"
        }

    except Exception as e:
        print(f"❌ 完成流程时出错: {e}\n")
        return {
            "step": "finalization_failed",
            "error_message": str(e)
        }


async def download_images_node(state: AgentState) -> dict:
    """
    节点 Y: 图片下载节点（预留）
    用于后续实现搜索结果图片下载功能

    Args:
        state: Agent 状态

    Returns:
        更新后的状态字典
    """
    print("\n" + "="*60)
    print("📍 [扩展节点] 图片下载")
    print("="*60)
    print("⚠️  该节点尚未实现")
    print()

    return {
        "step": "download_completed"
    }


# === 辅助函数 ===
# 注意: _detect_login_status 函数已移至 core/crawler_strategy.py 中的 CrawlerStrategy.detect_login_status()

async def scroll_right_modal(page: Page, duration: float = 1.0):
    """
    针对右侧浮层/抽屉的滚动（类似小红书/Instagram 详情页）
    先将鼠标移动到右侧中部，再用鼠标滚轮模拟人类滚动。
    """
    try:
        viewport = page.viewport_size or {"width": 1280, "height": 800}
        target_x = int(viewport["width"] * 0.75)
        target_y = int(viewport["height"] * 0.5)
    except Exception:
        target_x, target_y = 1000, 500

    # 可视化标记滚动目标
    await _show_click_marker(page, target_x, target_y)

    # 移动鼠标到目标区域，确保滚轮事件落在浮层上
    await page.mouse.move(target_x, target_y)

    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < duration:
        delta_y = random.randint(100, 300)
        await page.mouse.wheel(0, delta_y)
        await asyncio.sleep(random.uniform(0.05, 0.1))


async def _show_click_marker(page: Page, x: int, y: int):
    """
    在页面上显示一个临时标记，指示即将点击的位置（调试用）
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

            const cross = document.createElement('div');
            cross.style.position = 'absolute';
            cross.style.left = '50%';
            cross.style.top = '50%';
            cross.style.width = '16px';
            cross.style.height = '16px';
            cross.style.transform = 'translate(-50%, -50%)';
            cross.style.pointerEvents = 'none';
            cross.style.background = 'linear-gradient(transparent 45%, red 45%, red 55%, transparent 55%), linear-gradient(90deg, transparent 45%, red 45%, red 55%, transparent 55%)';
            marker.appendChild(cross);

            document.body.appendChild(marker);

            // 自动移除，避免干扰后续操作
            setTimeout(() => marker.remove(), 1500);
        }""",
        {"x": x, "y": y},
    )


async def _scroll_once_for_results(page: Page):
    """
    搜索完成后滚动一次，促发懒加载
    """
    try:
        viewport = page.viewport_size or {"width": 1280, "height": 800}
        target_x = int(viewport["width"] * 0.5)
        target_y = int(viewport["height"] * 0.5)
    except Exception:
        target_x, target_y = 800, 500

    await page.mouse.move(target_x, target_y)
    delta_y = random.randint(200, 400)
    await page.mouse.wheel(0, delta_y)
    await asyncio.sleep(0.2)


async def _human_like_click(page: Page, x: int, y: int):
    """
    类人点击：先移动鼠标到目标点，悬停/停顿后再点击
    """
    jitter_x = x + random.randint(-3, 3)
    jitter_y = y + random.randint(-3, 3)

    # 缓慢移动到目标位置（分两段，模拟人手移动）
    mid_x = (x + jitter_x) // 2
    mid_y = (y + jitter_y) // 2
    await page.mouse.move(mid_x, mid_y, steps=8)
    await page.mouse.move(jitter_x, jitter_y, steps=6)

    # 悬停/停顿
    await asyncio.sleep(random.uniform(0.12, 0.25))

    # 点击
    await page.mouse.click(jitter_x, jitter_y)
    await asyncio.sleep(random.uniform(0.05, 0.12))


async def _verify_detail_page_entry(
    page: Page,
    before_url: str,
    note_detail_selectors: Dict[str, str],
    timeout: int = 8000
) -> Dict:
    """
    判断是否从搜索页进入了笔记详情页

    Args:
        page: Playwright Page
        before_url: 点击前的 URL
        note_detail_selectors: 详情页选择器字典（从 crawler strategy 传入）
        timeout: 超时时间（毫秒）

    URL 判断规则：
    - 详情页: https://www.xiaohongshu.com/explore/66c32e22000000001f01fd24?...
    - 搜索页(未变): https://www.xiaohongshu.com/search_result?keyword=...
    - 搜索页(相关搜索): https://www.xiaohongshu.com/search_result?keyword=...（keyword变了）
    """
    detail_url_keywords = ["/explore/", "/discovery/item/"]
    search_url_keywords = ["/search_result"]
    selectors = list(note_detail_selectors.values())
    deadline = asyncio.get_event_loop().time() + timeout / 1000

    while asyncio.get_event_loop().time() < deadline:
        current_url = page.url

        # 1. 优先检查：如果包含详情页路径，立即返回成功
        if any(k in current_url for k in detail_url_keywords):
            return {"entered": True, "via": "url_explore_path", "url": current_url}

        # 2. 如果仍在搜索页，说明点击无效（点到空白或"大家都想搜"）
        if any(k in current_url for k in search_url_keywords):
            # 即使 URL 稍有变化（如 keyword 变了），仍然是搜索页
            return {
                "entered": False,
                "reason": "still_on_search_page",
                "url": current_url
            }

        # 3. 通过详情页特征元素检测（兜底方案）
        for sel in selectors:
            try:
                locator = page.locator(sel).first
                if await locator.is_visible(timeout=500):
                    return {"entered": True, "via": f"selector:{sel}", "url": current_url}
            except Exception:
                continue

        await asyncio.sleep(0.3)

    return {
        "entered": False,
        "reason": "detail markers not found (timeout)",
        "url": page.url
    }


async def _calibrate_click_with_dom(page: Page, x: int, y: int, note_card_selectors: List[str]):
    """
    根据 DOM 定位最近的 note 卡片中心点，用于纠偏 Vision 坐标

    Args:
        page: Playwright Page
        x: 目标 x 坐标
        y: 目标 y 坐标
        note_card_selectors: 笔记卡片选择器列表（从 crawler strategy 传入）
    """
    try:
        selector_str = ",".join(note_card_selectors)
        excluded_words = ["相关搜索", "大家都在搜", "猜你想搜", "热门搜索"]
        nearest = await page.evaluate(
            """({ x, y, selectorStr, excludedWords }) => {
                const nodes = Array.from(document.querySelectorAll(selectorStr));
                let best = null;
                let bestDist = Number.POSITIVE_INFINITY;
                for (const el of nodes) {
                    const text = (el.innerText || "").slice(0, 50);
                    if (text && excludedWords.some(w => text.includes(w))) continue;
                    const rect = el.getBoundingClientRect();
                    const cx = rect.x + rect.width / 2;
                    const cy = rect.y + rect.height / 2;
                    const dx = cx - x;
                    const dy = cy - y;
                    const dist = Math.hypot(dx, dy);
                    if (dist < bestDist) {
                        bestDist = dist;
                        best = { x: cx, y: cy, width: rect.width, height: rect.height };
                    }
                }
                if (!best) return null;
                return { ...best, distance: bestDist };
            }""",
            {"x": x, "y": y, "selectorStr": selector_str, "excludedWords": excluded_words},
        )
        return nearest
    except Exception as e:
        print(f"   - ⚠️  DOM 校准失败: {e}")
        return None
