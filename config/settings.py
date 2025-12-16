"""
全局配置文件
存放所有常量配置，方便统一管理和修改
"""
import os

# ========== 浏览器配置 ==========
HEADLESS = False  # 调试时设为 False，生产环境可设为 True
SLOW_MO = 500  # 每个操作延迟（毫秒），模拟人类操作速度

# ========== User-Agent 配置 ==========
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ========== 视口配置 ==========
VIEWPORT = {
    "width": 1440,
    "height": 900
}

# ========== Cookie 配置 ==========
# AUTH_FILE_PATH 支持相对路径（相对于项目根目录）
AUTH_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "auth.json")

# ========== 超时配置 ==========
DEFAULT_TIMEOUT = 10000  # 默认超时时间（毫秒）
NAVIGATION_TIMEOUT = 30000  # 页面导航超时时间（毫秒）



# ========== 笔记处理配置 ==========
DEFAULT_MAX_NOTES = 5  # 默认处理的最大笔记数量
OUTPUT_BASE_DIR = "output"  # 输出文件的基础目录
NOTE_SCREENSHOT_FORMAT = "png"  # 截图格式
NOTE_JSON_INDENT = 2  # JSON 文件缩进空格数

# ========== 滚动收集配置 ==========
SCROLL_PAUSE_TIME = 1.5  # 滚动后等待加载时间（秒）
MAX_SCROLL_ATTEMPTS = 3  # 最大滚动尝试次数
SCROLL_DISTANCE = 800  # 每次滚动距离（像素）

# ==========  模型配置 ==========
OPENAI_MODEL = "gpt-4o"  # 使用的 OpenAI 模型名称
OPENAI_TEMPERATURE = 0.2  # 模型温度，越低越稳定
OPENAI_MAX_TOKENS = 2000  # 最大生成 token 数
OPENAI_MAX_RETRIES = 3  # GPT-4o 调用失败时的最大重试次数
OPENAI_RETRY_DELAY = 2  # 重试之间的延迟时间（秒）

# ========== 日志配置 ==========
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
