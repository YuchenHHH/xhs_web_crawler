"""
Agent 图编排
使用 LangGraph 构建节点流程图
"""
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    init_browser_node,
    check_login_node,
    manual_login_and_save_cookies_node,
    search_keyword_node,
    # 新增笔记处理节点
    collect_note_links_node,
    process_note_detail_node,
    navigate_back_node,
    scroll_for_more_notes_node,
    finalize_extraction_node,
    # 扩展节点（暂不使用）
    # vision_analysis_node,
    # download_images_node,
)


def route_after_collection(state: AgentState) -> str:
    """
    路由函数：收集笔记链接后决定下一步

    Args:
        state: Agent 状态

    Returns:
        下一个节点的名称
    """
    note_links = state.get("note_links", [])

    if len(note_links) > 0:
        return "process_first_note"
    else:
        return "no_notes_found"


def route_after_login_check(state: AgentState) -> str:
    """
    路由函数：登录检测后决定是否需要手动登录
    """
    return "logged_in" if state.get("is_logged_in") else "need_manual_login"


def route_after_manual_login(state: AgentState) -> str:
    """
    路由函数：手动登录节点之后决定下一步
    """
    return "login_ready" if state.get("is_logged_in") else "login_still_required"


def route_after_back(state: AgentState) -> str:
    """
    路由函数：返回搜索页后决定是否继续处理下一个笔记

    Args:
        state: Agent 状态

    Returns:
        下一个节点的名称
    """
    current_index = state.get("current_note_index", 0)
    max_notes = state.get("max_notes_to_process", 3)
    note_links = state.get("note_links", [])
    processed_total = len(state.get("processed_notes", [])) + len(state.get("failed_notes", []))

    # 如果还有笔记需要处理，且未达到最大数量，继续处理
    if current_index < len(note_links) and processed_total < max_notes:
        return "process_next_note"

    # 如果当前批次耗尽但仍未达到最大数量，尝试滚动加载新一批
    if processed_total < max_notes:
        return "need_more_notes"

    return "all_notes_processed"


def create_agent_graph():
    """
    创建并编译 Agent 工作流图

    新流程:
        init_browser -> check_login -> search_keyword ->
        collect_note_links -> [条件判断] ->
        process_note_detail -> navigate_back -> [循环或结束] ->
        finalize_extraction -> END

    Returns:
        编译后的 LangGraph 应用
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # === 添加所有节点 ===
    workflow.add_node("init_browser", init_browser_node)
    workflow.add_node("check_login", check_login_node)
    workflow.add_node("manual_login_and_save_cookies", manual_login_and_save_cookies_node)
    workflow.add_node("search_keyword", search_keyword_node)
    workflow.add_node("collect_note_links", collect_note_links_node)
    workflow.add_node("process_note_detail", process_note_detail_node)
    workflow.add_node("navigate_back", navigate_back_node)
    workflow.add_node("scroll_for_more_notes", scroll_for_more_notes_node)
    # 暂时注释掉提取节点，专注自动化点击（如需数据保存，请恢复）
    # workflow.add_node("finalize_extraction", finalize_extraction_node)

    # === 设置入口点 ===
    workflow.set_entry_point("init_browser")

    # === 线性边 ===
    workflow.add_edge("init_browser", "check_login")

    # === 条件边：登录检测后 ===
    workflow.add_conditional_edges(
        "check_login",
        route_after_login_check,
        {
            "logged_in": "search_keyword",
            "need_manual_login": "manual_login_and_save_cookies"
        }
    )

    # === 条件边：手动登录后 ===
    workflow.add_conditional_edges(
        "manual_login_and_save_cookies",
        route_after_manual_login,
        {
            "login_ready": "search_keyword",
            "login_still_required": "search_keyword"  # 即便未登录也继续执行，后续可能再提示
        }
    )

    workflow.add_edge("search_keyword", "collect_note_links")

    # === 条件边 1: 收集链接后 ===
    workflow.add_conditional_edges(
        "collect_note_links",
        route_after_collection,
        {
            "process_first_note": "process_note_detail",
            "no_notes_found": END
        }
    )

    # === 处理笔记后返回 ===
    workflow.add_edge("process_note_detail", "navigate_back")

    # === 条件边 2: 返回后决定循环或结束 ===
    workflow.add_conditional_edges(
        "navigate_back",
        route_after_back,
        {
            "process_next_note": "process_note_detail",  # 循环回处理节点
            "need_more_notes": "scroll_for_more_notes",  # 滚动加载新一批
            "all_notes_processed": END  # 结束处理
        }
    )
    # === 滚动后重新收集笔记 ===
    workflow.add_edge("scroll_for_more_notes", "collect_note_links")

    # 编译图
    app = workflow.compile()

    return app


# 便捷函数：直接获取编译好的 app
def get_compiled_graph():
    """
    获取编译后的 Agent 图
    可直接用于 main.py 中

    Returns:
        编译后的 LangGraph 应用
    """
    return create_agent_graph()
