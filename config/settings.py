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
    "width": 1280,
    "height": 800
}

# ========== Cookie 配置 ==========
# AUTH_FILE_PATH 支持相对路径（相对于项目根目录）
AUTH_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "auth.json")

# ========== 超时配置 ==========
DEFAULT_TIMEOUT = 10000  # 默认超时时间（毫秒）
NAVIGATION_TIMEOUT = 30000  # 页面导航超时时间（毫秒）

# ========== 小红书相关配置 ==========
XHS_HOME_URL = "https://www.xiaohongshu.com/explore"
XHS_SEARCH_INPUT_SELECTORS = [
    "input#search-input",
    "[placeholder='搜索小红书']",
    "input[type='text'].search-input"
]

# ========== 笔记处理配置（新增）==========
DEFAULT_MAX_NOTES = 5  # 默认处理的最大笔记数量
OUTPUT_BASE_DIR = "output"  # 输出文件的基础目录
NOTE_SCREENSHOT_FORMAT = "png"  # 截图格式
NOTE_JSON_INDENT = 2  # JSON 文件缩进空格数

# ========== 滚动收集配置（新增）==========
SCROLL_PAUSE_TIME = 1.5  # 滚动后等待加载时间（秒）
MAX_SCROLL_ATTEMPTS = 3  # 最大滚动尝试次数
SCROLL_DISTANCE = 800  # 每次滚动距离（像素）

# ========== 笔记卡片选择器（新增）==========
XHS_NOTE_CARD_SELECTORS = [
    "a[href*='/explore/']",  # 优先级 1: 所有包含 /explore/ 的链接
    ".note-item",  # 优先级 2: 笔记项容器
    "[class*='note-card']",  # 优先级 3: 包含 note-card 的类名
    ".feeds-container > div > a",  # 优先级 4: feeds 容器下的链接
]

# ========== 笔记详情页选择器（新增）==========
XHS_NOTE_DETAIL_SELECTORS = {
    "title": ".note-title, .title, [class*='title']",
    "author": ".author-name, .user-name, [class*='author']",
    "content": ".note-content, .content-text, [class*='content']",
    "likes": "[class*='like-count'], .like-wrapper",
}

# ========== OpenAI 模型配置 ==========
OPENAI_MODEL = "gpt-4o"  # 使用的 OpenAI 模型名称
OPENAI_TEMPERATURE = 0.2  # 模型温度，越低越稳定
OPENAI_MAX_TOKENS = 2000  # 最大生成 token 数

# ========== 日志配置 ==========
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
