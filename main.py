"""
小红书爬虫 Agent - 主入口
运行整个自动化流程
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}")
else:
    print(f"⚠️  未找到 .env 文件: {env_path}")

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from core.browser_manager import BrowserManager
from agent.graph import run_click_graph
from agent.nodes import (
    init_browser_node,
    check_login_node,
    manual_login_and_save_cookies_node,
    search_keyword_node,
)


async def main():
    """
    主函数 - 运行完整的爬虫流程
    """
    print("\n" + "="*60)
    print("🤖 小红书爬虫 Agent 启动")
    print("="*60 + "\n")

    # === 1. 初始化 BrowserManager ===
    browser_manager = BrowserManager()

    try:
        keyword = "番茄炒蛋"  # 可以修改为任意关键词
        description = "挑选其中 与菜肴相关的内容"  # 内容描述，用于过滤笔记
        max_notes = 20  # 每轮最多点击的笔记数量
        total_rounds = 10  # 总共执行的轮次（1=不循环，>1=滚动并重复）
        browse_images_count = 20  # 每个笔记进入详情页后按右键浏览图片的次数

        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent / "output" / f"{keyword}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 输出目录: {output_dir}")

        state = {
            "browser_manager": browser_manager,
            "page": None,
            "search_keyword": keyword,
            "search_description": description,
            "max_notes_to_process": max_notes,
            "current_note_index": 0,
            "note_links": [],
            "processed_notes": [],
            "failed_notes": [],
            "output_base_dir": str(output_dir),
            "step": "not_started",
            "is_logged_in": False,
        }

        print("📋 初始配置:")
        print(f"   - 搜索关键词: {keyword}")
        print(f"   - 内容描述: {description}")
        print(f"   - 每轮点击数: {max_notes}")
        print(f"   - 执行轮次: {total_rounds}")
        print(f"   - 图片浏览次数: 每个笔记按{browse_images_count}次右键")
        print(f"   - Cookie 文件: {'存在' if Path('auth.json').exists() else '不存在'}")
        print()

        # === 2. 顺序化流程（减少 LangGraph 上下文） ===
        updates = await init_browser_node(state)
        state.update(updates)

        updates = await check_login_node(state)
        state.update(updates)

        if not state.get("is_logged_in"):
            updates = await manual_login_and_save_cookies_node(state)
            state.update(updates)

        updates = await search_keyword_node(state)
        state.update(updates)

        # === 3. 将"截图+坐标+点击+循环"交给精简版 LangGraph ===
        click_result = await run_click_graph(
            page=state["page"],
            max_notes=state.get("max_notes_to_process", max_notes),
            total_rounds=total_rounds,  # 传入轮次参数
            browse_images_arrow_count=browse_images_count,  # 传入浏览图片次数
            content_description=state.get("search_description", ""),  # 传入内容描述
            output_dir=str(output_dir),  # 传入输出目录
        )

        print("\n" + "="*60)
        print("📊 点击结果")
        print("="*60)
        print(f"   - 执行轮次: {click_result.get('current_round', 1) - 1}/{total_rounds}")
        print(f"   - 累计识别坐标: {len(click_result.get('coordinates', []))}")
        print(f"   - 累计点击: {len(click_result.get('clicked', []))}")
        print(f"   - 累计失败: {len(click_result.get('failures', []))}")
        entered_count = len(
            [c for c in click_result.get("clicked", []) if c.get("entered_detail")]
        )
        print(f"   - 可能进入详情页: {entered_count}")

        if click_result.get("clicked"):
            print("\n✅ 已点击的坐标(前 3 条):")
            for entry in click_result["clicked"][:3]:
                print(
                    f"   {entry['index'] + 1}. ({entry['click_x']}, {entry['click_y']}) - {entry.get('title', 'N/A')[:40]}"
                )

        if click_result.get("failures"):
            print("\n⚠️  点击失败的坐标:")
            for entry in click_result["failures"]:
                print(
                    f"   {entry['index'] + 1}. ({entry['click_x']}, {entry['click_y']}) - {entry.get('error', '')}"
                )

        # === 4. 保持浏览器打开一段时间供观察 ===
        print("\n⏳ 保持浏览器打开 10 秒供观察...")
        await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\n⚠️  用户中断程序")

    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # === 清理资源 ===
        print("\n🧹 正在清理资源...")
        await browser_manager.close()

        print("\n" + "="*60)
        print("✅ 程序执行完毕")
        print("="*60 + "\n")


def run():
    """
    便捷启动函数（同步包装）
    """
    asyncio.run(main())


if __name__ == "__main__":
    run()
