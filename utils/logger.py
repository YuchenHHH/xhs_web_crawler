"""
日志工具模块
同时输出到控制台和日志文件
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


class DualLogger:
    """
    双输出日志器：同时输出到控制台和文件
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # 创建日志目录
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        # 生成日志文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"crawler_{timestamp}.log"

        # 配置日志格式
        log_format = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 创建根日志器
        self.logger = logging.getLogger('xhs_crawler')
        self.logger.setLevel(logging.INFO)

        # 清除现有的处理器（避免重复）
        self.logger.handlers.clear()

        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        # 控制台使用简化格式（不显示时间，与原有 print 类似）
        console_format = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # 保存日志文件路径
        self.log_file = log_file

        # 记录启动信息
        self.info(f"📝 日志文件: {log_file}")

    def info(self, message):
        """记录信息级别日志"""
        self.logger.info(message)

    def warning(self, message):
        """记录警告级别日志"""
        self.logger.warning(message)

    def error(self, message):
        """记录错误级别日志"""
        self.logger.error(message)

    def debug(self, message):
        """记录调试级别日志"""
        self.logger.debug(message)

    def get_log_file(self):
        """获取日志文件路径"""
        return self.log_file


# 全局日志器实例
_logger = None


def get_logger():
    """获取全局日志器"""
    global _logger
    if _logger is None:
        _logger = DualLogger()
    return _logger


def log_info(message):
    """快捷方法：记录信息"""
    get_logger().info(message)


def log_warning(message):
    """快捷方法：记录警告"""
    get_logger().warning(message)


def log_error(message):
    """快捷方法：记录错误"""
    get_logger().error(message)


def log_debug(message):
    """快捷方法：记录调试信息"""
    get_logger().debug(message)
