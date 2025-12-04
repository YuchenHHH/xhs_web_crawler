"""
Agent 状态定义
定义在不同节点间传递的状态数据结构
"""
from typing import TypedDict, Any, Optional, List, Dict
from playwright.async_api import Page


class AgentState(TypedDict):
    """
    LangGraph Agent 的状态字典
    这个状态会在所有节点间共享和传递
    """
    # === 浏览器相关 ===
    browser_manager: Any  # BrowserManager 实例（避免循环导入，使用 Any）
    page: Optional[Page]  # Playwright Page 对象

    # === 业务数据 ===
    search_keyword: str  # 用户要搜索的关键词
    search_results: Optional[List[Dict]]  # 搜索结果列表（来自视觉分析）

    # === 视觉分析结果 ===
    vision_analysis: Optional[Dict]  # GPT-4o Vision 完整分析结果
    screenshot_base64: Optional[str]  # 页面截图（Base64 编码）
    content_summary: Optional[str]  # 页面内容总结

    # === 笔记处理（新增）===
    note_links: Optional[List[Dict]]  # 笔记卡片链接列表 [{"url": str, "index": int, "selector": str}]
    current_note_index: int  # 当前处理的笔记索引（从0开始）
    max_notes_to_process: int  # 最大处理笔记数量（默认5）
    processed_notes: List[Dict]  # 已处理笔记数据 [{"index": int, "data": Dict, "screenshot_path": str, "json_path": str}]

    # === 文件管理（新增）===
    output_base_dir: str  # 输出目录基础路径 "output/{keyword}_{timestamp}/"

    # === 错误追踪（新增）===
    failed_notes: List[Dict]  # 处理失败的笔记 [{"index": int, "error": str}]

    # === 流程控制 ===
    step: str  # 当前执行到的步骤（用于调试和日志）
    is_logged_in: bool  # 登录状态标识
    error_message: Optional[str]  # 错误信息（如果发生错误）
