"""
小红书爬虫 Agent - 主入口
支持并发执行多个关键词采集任务
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from core.browser_manager import BrowserManager
from agent.graph import run_click_graph
from agent.nodes import (
    init_browser_node,
    check_login_node,
    search_keyword_node,
)
from utils.logger import get_logger

# 初始化日志器
logger = get_logger()
logger.info(f"✅ 已加载环境变量: {env_path}" if env_path.exists() else f"⚠️  未找到 .env 文件: {env_path}")


# ============================================
# 任务配置列表
# ============================================
MISSIONS = [
    {"keyword": "番茄炒蛋", "description": "挑选成品菜肴"},
    {"keyword": "红烧肉", "description": "挑选色泽红亮的"},
    {"keyword": "清蒸鱼", "description": "完整鱼身"},
    {"keyword": "宫保鸡丁", "description": "挑选与菜肴相关的内容"},
    {"keyword": "麻婆豆腐", "description": "挑选与菜肴相关的内容"},
]


async def run_single_mission(
    semaphore: asyncio.Semaphore,
    mission_config: Dict[str, str],
    max_notes: int = 20,
    total_rounds: int = 10,
    browse_images_count: int = 20,
    max_images: int = None
) -> Dict:
    """
    执行单个关键词的采集任务（独立浏览器实例）

    Args:
        semaphore: 信号量，用于控制并发数
        mission_config: 任务配置 {"keyword": "...", "description": "..."}
        max_notes: 每轮最多点击的笔记数量
        total_rounds: 总共执行的轮次
        browse_images_count: 每个笔记进入详情页后按右键浏览图片的次数
        max_images: 图片总数限制，达到后自动结束任务（None=不限制）

    Returns:
        任务执行结果摘要
    """
    keyword = mission_config["keyword"]
    description = mission_config["description"]

    async with semaphore:
        # 初始化独立的 BrowserManager
        browser_manager = BrowserManager()

        try:
            logger.info(f"\n[{keyword}] 🚀 任务启动")

            # 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(__file__).parent / "output" / f"{keyword}_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[{keyword}] 📁 输出目录: {output_dir}")

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

            config_msg = f"[{keyword}] 📋 配置: 每轮{max_notes}个笔记 | {total_rounds}轮 | 每笔记浏览{browse_images_count}张图"
            if max_images:
                config_msg += f" | 图片总数限制{max_images}张"
            logger.info(config_msg)

            # 初始化浏览器
            updates = await init_browser_node(state)
            state.update(updates)

            # 检查登录状态
            updates = await check_login_node(state)
            state.update(updates)

            if not state.get("is_logged_in"):
                logger.warning(f"[{keyword}] ⚠️  未登录，跳过手动登录（使用共享 Cookie）")
                # 注意：如果需要手动登录，多任务并发时需要协调处理
                # 这里假设已经有 auth.json，否则第一个任务会触发登录

            # 搜索关键词
            updates = await search_keyword_node(state)
            state.update(updates)

            # 执行点击任务
            logger.info(f"[{keyword}] 🎯 开始执行点击任务...")
            click_result = await run_click_graph(
                page=state["page"],
                max_notes=max_notes,
                total_rounds=total_rounds,
                browse_images_arrow_count=browse_images_count,
                content_description=description,
                output_dir=str(output_dir),
                max_images=max_images,
            )

            # 统计结果
            entered_count = len(
                [c for c in click_result.get("clicked", []) if c.get("entered_detail")]
            )

            result_summary = {
                "keyword": keyword,
                "status": "success",
                "rounds": click_result.get('current_round', 1) - 1,
                "total_clicked": len(click_result.get('clicked', [])),
                "total_failed": len(click_result.get('failures', [])),
                "entered_detail": entered_count,
                "output_dir": str(output_dir),
            }

            logger.info(f"\n[{keyword}] ✅ 任务完成 - 点击{result_summary['total_clicked']}个 | 进入详情页{entered_count}个")

            return result_summary

        except KeyboardInterrupt:
            logger.warning(f"\n[{keyword}] ⚠️  任务被用户中断")
            return {"keyword": keyword, "status": "interrupted", "error": "用户中断"}

        except Exception as e:
            logger.error(f"\n[{keyword}] ❌ 任务异常: {e}")
            import traceback
            traceback.print_exc()
            return {"keyword": keyword, "status": "failed", "error": str(e)}

        finally:
            # 清理资源
            logger.info(f"[{keyword}] 🧹 清理浏览器资源...")
            await browser_manager.close()


async def main(max_concurrent: int = 3):
    """
    并发执行多个采集任务

    Args:
        max_concurrent: 最大并发任务数（默认3个）
    """
    logger.info("\n" + "="*60)
    logger.info("🤖 小红书爬虫 Agent 启动（并发模式）")
    logger.info("="*60 + "\n")

    logger.info(f"📋 任务列表: 共 {len(MISSIONS)} 个关键词")
    for i, mission in enumerate(MISSIONS, 1):
        logger.info(f"   {i}. {mission['keyword']} - {mission['description']}")

    logger.info(f"\n⚙️  并发配置: 最大并发数 = {max_concurrent}")
    logger.info(f"⚙️  Cookie 文件: {'✅ 存在' if Path('auth.json').exists() else '❌ 不存在（第一个任务将触发登录）'}")
    logger.info("")

    # 创建信号量控制并发数
    semaphore = asyncio.Semaphore(max_concurrent)

    # 任务参数（可根据需要调整）
    max_notes = 20
    total_rounds = 10
    browse_images_count = 20
    max_images = 100  # 每个关键词的图片总数限制（设为 None 则不限制）

    try:
        # 启动所有任务
        start_time = datetime.now()
        tasks = [
            run_single_mission(
                semaphore=semaphore,
                mission_config=mission,
                max_notes=max_notes,
                total_rounds=total_rounds,
                browse_images_count=browse_images_count,
                max_images=max_images
            )
            for mission in MISSIONS
        ]

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now()

        # 打印汇总结果
        logger.info("\n" + "="*60)
        logger.info("📊 所有任务执行完毕 - 汇总报告")
        logger.info("="*60)
        logger.info(f"⏱️  总耗时: {(end_time - start_time).total_seconds():.1f} 秒")
        logger.info("")

        success_count = 0
        failed_count = 0

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ 任务异常: {result}")
                failed_count += 1
            elif isinstance(result, dict):
                status = result.get('status', 'unknown')
                keyword = result.get('keyword', 'N/A')

                if status == 'success':
                    logger.info(f"✅ [{keyword}] 成功 - 点击{result.get('total_clicked', 0)}个 | 详情页{result.get('entered_detail', 0)}个")
                    success_count += 1
                elif status == 'interrupted':
                    logger.warning(f"⚠️  [{keyword}] 中断")
                    failed_count += 1
                else:
                    logger.error(f"❌ [{keyword}] 失败 - {result.get('error', 'Unknown error')}")
                    failed_count += 1

        logger.info("")
        logger.info(f"📈 成功: {success_count}/{len(MISSIONS)} | 失败: {failed_count}/{len(MISSIONS)}")
        logger.info("="*60 + "\n")

    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断程序（所有任务将尝试优雅退出）")
    except Exception as e:
        logger.error(f"\n❌ 主程序异常: {e}")
        import traceback
        traceback.print_exc()


def run():
    """
    便捷启动函数（同步包装）
    支持命令行参数
    """
    parser = argparse.ArgumentParser(description="小红书爬虫 Agent")
    parser.add_argument(
        "--concurrent",
        "-c",
        type=int,
        default=3,
        help="最大并发任务数（默认3）"
    )
    args = parser.parse_args()

    asyncio.run(main(max_concurrent=args.concurrent))


if __name__ == "__main__":
    run()
