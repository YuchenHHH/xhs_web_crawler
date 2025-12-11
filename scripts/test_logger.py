"""
测试日志功能
验证日志是否同时输出到控制台和文件
"""
import sys
from pathlib import Path

# 将项目根目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger

def test_logger():
    """测试日志功能"""
    logger = get_logger()

    print("=" * 60)
    print("🧪 测试日志功能")
    print("=" * 60)
    print()

    # 测试不同级别的日志
    logger.info("✅ 这是一条信息日志")
    logger.warning("⚠️  这是一条警告日志")
    logger.error("❌ 这是一条错误日志")

    # 测试带格式的日志
    logger.info(f"📋 任务列表: 共 5 个关键词")
    for i in range(5):
        logger.info(f"   {i+1}. 测试任务 {i+1}")

    # 显示日志文件位置
    log_file = logger.get_log_file()
    print()
    print("=" * 60)
    print(f"📝 日志文件保存在: {log_file}")
    print("=" * 60)
    print()
    print("✅ 测试完成！请检查日志文件查看完整记录。")


if __name__ == "__main__":
    test_logger()
