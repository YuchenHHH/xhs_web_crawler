"""
多平台爬虫 Agent - 主入口
支持小红书、Pinterest等多个平台
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
from config.sites.xhs import XHSCrawlerStrategy
from config.sites.pinterest import PinterestCrawlerStrategy
from agent.graph import run_click_graph
from agent.nodes import (
    init_browser_node,
    check_login_node,
    manual_login_and_save_cookies_node,
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
    {"site": "xiaohongshu", "keyword": "宫保鸡丁做法", "description": "只挑选和菜谱,做菜流程相关的内容"},
]


def get_crawler_strategy(site: str):
    """
    工厂函数：根据站点名称获取对应的爬虫策略

    Args:
        site: 站点标识（xiaohongshu, pinterest等）

    Returns:
        对应的 CrawlerStrategy 实例

    Raises:
        ValueError: 不支持的站点类型
    """
    strategies = {
        "xiaohongshu": XHSCrawlerStrategy,
        "pinterest": PinterestCrawlerStrategy,
    }

    strategy_class = strategies.get(site)
    if not strategy_class:
        raise ValueError(f"不支持的站点: {site}。可用站点: {list(strategies.keys())}")

    return strategy_class()


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
        mission_config: 任务配置 {"site": "...", "keyword": "...", "description": "..."}
        max_notes: 每轮最多点击的笔记数量
        total_rounds: 总共执行的轮次
        browse_images_count: 每个笔记进入详情页后按右键浏览图片的次数
        max_images: 图片总数限制，达到后自动结束任务（None=不限制）

    Returns:
        任务执行结果摘要
    """
    keyword = mission_config["keyword"]
    description = mission_config["description"]
    site = mission_config.get("site", "xiaohongshu")  # 默认为小红书（向后兼容）

    async with semaphore:
        # 初始化站点特定的 BrowserManager
        browser_manager = BrowserManager(site=site)

        # 使用工厂函数获取站点特定的爬虫策略
        crawler = get_crawler_strategy(site)

        try:
            logger.info(f"\n[{site.upper()} | {keyword}] 🚀 任务启动")

            # 创建输出目录（包含站点前缀）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(__file__).parent / "output" / f"{site}_{keyword}_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[{site.upper()} | {keyword}] 📁 输出目录: {output_dir}")

            state = {
                "browser_manager": browser_manager,
                "crawler": crawler,
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

            config_msg = f"[{site.upper()} | {keyword}] 📋 配置: 每轮{max_notes}个笔记 | {total_rounds}轮 | 每笔记浏览{browse_images_count}张图"
            if max_images:
                config_msg += f" | 图片总数限制{max_images}张"
            logger.info(config_msg)

            # 初始化浏览器
            updates = await init_browser_node(state)
            state.update(updates)

            # 检查登录状态
            updates = await check_login_node(state)
            state.update(updates)

            # 如果未登录，触发手动登录流程
            if not state.get("is_logged_in"):
                logger.warning(f"[{site.upper()} | {keyword}] ⚠️  未登录，启动手动登录流程...")
                logger.info(f"[{site.upper()} | {keyword}] 💡 请在浏览器窗口中完成登录操作")
                logger.info(f"[{site.upper()} | {keyword}] 📝 登录成功后将自动保存到: auth/{site}.json")

                # 执行手动登录并保存 Cookie
                updates = await manual_login_and_save_cookies_node(state)
                state.update(updates)

                # 检查登录是否成功
                if not state.get("is_logged_in"):
                    logger.error(f"[{site.upper()} | {keyword}] ❌ 登录超时或失败，任务终止")
                    return {
                        "site": site,
                        "keyword": keyword,
                        "status": "failed",
                        "error": "登录失败或超时"
                    }
                else:
                    logger.info(f"[{site.upper()} | {keyword}] ✅ 登录成功，Cookie已保存")

            # 搜索关键词
            updates = await search_keyword_node(state)
            state.update(updates)

            # 执行点击任务
            logger.info(f"[{site.upper()} | {keyword}] 🎯 开始执行点击任务...")
            click_result = await run_click_graph(
                page=state["page"],
                crawler=crawler,
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
                "site": site,
                "keyword": keyword,
                "status": "success",
                "rounds": click_result.get('current_round', 1) - 1,
                "total_clicked": len(click_result.get('clicked', [])),
                "total_failed": len(click_result.get('failures', [])),
                "entered_detail": entered_count,
                "output_dir": str(output_dir),
            }

            logger.info(f"\n[{site.upper()} | {keyword}] ✅ 任务完成 - 点击{result_summary['total_clicked']}个 | 进入详情页{entered_count}个")

            return result_summary

        except KeyboardInterrupt:
            logger.warning(f"\n[{site.upper()} | {keyword}] ⚠️  任务被用户中断")
            return {"site": site, "keyword": keyword, "status": "interrupted", "error": "用户中断"}

        except Exception as e:
            logger.error(f"\n[{site.upper()} | {keyword}] ❌ 任务异常: {e}")
            import traceback
            traceback.print_exc()
            return {"site": site, "keyword": keyword, "status": "failed", "error": str(e)}

        finally:
            # 清理资源
            logger.info(f"[{site.upper()} | {keyword}] 🧹 清理浏览器资源...")
            await browser_manager.close()


async def main(max_concurrent: int = 3):
    """
    并发执行多个采集任务

    Args:
        max_concurrent: 最大并发任务数（默认3个）
    """
    logger.info("\n" + "="*60)
    logger.info("🤖 多平台爬虫 Agent 启动（并发模式）")
    logger.info("="*60 + "\n")

    logger.info(f"📋 任务列表: 共 {len(MISSIONS)} 个任务")
    for i, mission in enumerate(MISSIONS, 1):
        site = mission.get("site", "xiaohongshu")
        logger.info(f"   {i}. [{site.upper()}] {mission['keyword']} - {mission['description']}")

    logger.info(f"\n⚙️  并发配置: 最大并发数 = {max_concurrent}")
    logger.info(f"⚙️  认证目录: auth/ (各平台使用独立认证文件)")
    logger.info("")

    # 创建信号量控制并发数
    semaphore = asyncio.Semaphore(max_concurrent)

    # 任务参数（可根据需要调整）
    max_notes = 20
    total_rounds = 10
    browse_images_count = 20
    max_images = 50  # 每个关键词的图片总数限制（设为 None 则不限制）

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
                site = result.get('site', 'unknown')
                keyword = result.get('keyword', 'N/A')

                if status == 'success':
                    logger.info(f"✅ [{site.upper()} | {keyword}] 成功 - 点击{result.get('total_clicked', 0)}个 | 详情页{result.get('entered_detail', 0)}个")
                    success_count += 1
                elif status == 'interrupted':
                    logger.warning(f"⚠️  [{site.upper()} | {keyword}] 中断")
                    failed_count += 1
                else:
                    logger.error(f"❌ [{site.upper()} | {keyword}] 失败 - {result.get('error', 'Unknown error')}")
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
    parser = argparse.ArgumentParser(description="多平台爬虫 Agent（支持小红书、Pinterest等）")
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
