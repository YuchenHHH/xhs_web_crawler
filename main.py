"""
小红书爬虫 Agent - 主入口
运行整个自动化流程
"""
import asyncio
import sys
from pathlib import Path
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
from agent.graph import get_compiled_graph


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
        # === 2. 构建 Agent 图 ===
        app = get_compiled_graph()

        # === 3. 准备初始状态 ===
        from core.file_manager import FileManager

        keyword = "鱼香肉丝"  # 可以修改为任意关键词
        output_dir = FileManager.create_output_directory(keyword)

        initial_state = {
            "browser_manager": browser_manager,
            "page": None,
            "search_keyword": keyword,
            "max_notes_to_process": 20,  # 最多处理5个笔记（可配置）
            "current_note_index": 0,
            "note_links": [],
            "processed_notes": [],
            "failed_notes": [],
            "output_base_dir": output_dir,
            "step": "not_started",
            "is_logged_in": False,
        }

        print("📋 初始配置:")
        print(f"   - 搜索关键词: {keyword}")
        print(f"   - 最大处理笔记数: {initial_state['max_notes_to_process']}")
        print(f"   - 输出目录: {output_dir}")
        print(f"   - Cookie 文件: {'存在' if Path('auth.json').exists() else '不存在'}")
        print()

        # === 4. 运行 Agent 工作流 ===
        print("🚀 开始执行工作流...\n")
        final_state = await app.ainvoke(initial_state)

        # === 5. 输出最终状态 ===
        print("\n" + "="*60)
        print("📊 执行结果")
        print("="*60)
        print(f"   - 最终步骤: {final_state.get('step', 'unknown')}")
        print(f"   - 登录状态: {'已登录' if final_state.get('is_logged_in') else '未登录'}")

        # 输出笔记处理统计
        processed_notes = final_state.get('processed_notes', [])
        failed_notes = final_state.get('failed_notes', [])

        print(f"   - 成功处理笔记: {len(processed_notes)} 个")
        print(f"   - 失败笔记: {len(failed_notes)} 个")
        print(f"   - 输出目录: {output_dir}")

        if processed_notes:
            print("\n" + "="*60)
            print("✅ 成功处理的笔记")
            print("="*60)
            for note in processed_notes:
                title = note["data"].get("title", "N/A")[:50]
                print(f"   {note['index'] + 1}. {title}")
                print(f"      截图: {Path(note['screenshot_path']).name}")
                print(f"      数据: {Path(note['json_path']).name}")
                print()

        if failed_notes:
            print("="*60)
            print("⚠️  处理失败的笔记")
            print("="*60)
            for fail in failed_notes:
                print(f"   {fail['index'] + 1}. 错误: {fail['error'][:60]}")

        print()

        # === 6. 保持浏览器打开一段时间供观察 ===
        print("⏳ 保持浏览器打开 15 秒供观察...")
        print("   (你可以手动在浏览器中继续操作)\n")
        await asyncio.sleep(15)

        # === 7. 可选：保存 Cookie ===
        # 如果需要保存当前的登录状态，取消下面的注释
        # if final_state.get("is_logged_in"):
        #     await browser_manager.save_cookies()

    except KeyboardInterrupt:
        print("\n⚠️  用户中断程序")

    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # === 8. 清理资源 ===
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
