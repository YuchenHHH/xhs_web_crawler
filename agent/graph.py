"""
LangGraph 最小化编排：只负责截图、识别坐标并顺序点击。
其余登录、搜索、数据处理流程改为普通 Python 逻辑。
"""
from langgraph.graph import StateGraph, END

from agent.state import ClickGraphState
from agent.click_nodes import collect_coordinates_node, click_coordinate_node, scroll_and_wait_node


def _route_after_collect(state: ClickGraphState) -> str:
    return "click" if state.get("coordinates") else "done"


def _route_after_click(state: ClickGraphState) -> str:
    """
    点击后路由：
    - 如果还有坐标未点击，继续点击下一个
    - 如果当前轮次的坐标已全部点击完，检查是否需要进入下一轮
    - 如果所有轮次已完成，结束
    """
    coords = state.get("coordinates", [])
    idx = state.get("current_index", 0)
    current_round = state.get("current_round", 1)
    total_rounds = state.get("total_rounds", 1)

    # 如果还有坐标未点击，继续点击
    if idx < len(coords):
        return "next"

    # 当前轮次点击完成，检查是否需要下一轮
    if current_round < total_rounds:
        return "scroll"  # 滚动页面，准备下一轮

    # 所有轮次完成
    return "done"


def _route_after_scroll(state: ClickGraphState) -> str:
    """
    滚动后路由：重新收集坐标
    """
    return "collect"


def create_click_graph():
    """
    创建包含"截图+坐标识别+顺序点击+滚动循环"的图。

    流程：
    1. collect_coordinates: 截图并识别坐标
    2. click_coordinate: 顺序点击每个坐标
    3. scroll_and_wait: 滚动页面加载更多内容（可选，当需要多轮时）
    4. 返回步骤1，重新收集坐标（循环）
    """
    workflow = StateGraph(ClickGraphState)

    # 添加节点
    workflow.add_node("collect_coordinates", collect_coordinates_node)
    workflow.add_node("click_coordinate", click_coordinate_node)
    workflow.add_node("scroll_and_wait", scroll_and_wait_node)

    # 设置入口
    workflow.set_entry_point("collect_coordinates")

    # 路由：收集坐标后
    workflow.add_conditional_edges(
        "collect_coordinates",
        _route_after_collect,
        {"click": "click_coordinate", "done": END},
    )

    # 路由：点击后
    workflow.add_conditional_edges(
        "click_coordinate",
        _route_after_click,
        {
            "next": "click_coordinate",  # 继续点击下一个坐标
            "scroll": "scroll_and_wait",  # 滚动加载更多
            "done": END,  # 结束
        },
    )

    # 路由：滚动后
    workflow.add_conditional_edges(
        "scroll_and_wait",
        _route_after_scroll,
        {"collect": "collect_coordinates"},  # 重新收集坐标
    )

    return workflow.compile()


async def run_click_graph(
    page,
    max_notes: int = 20,
    total_rounds: int = 1,
    browse_images_arrow_count: int = 5,
    content_description: str = "",
    output_dir: str = "",
    recursion_limit: int = 100,
) -> ClickGraphState:
    """
    便捷函数：运行最小点击图并返回最终状态。

    Args:
        page: Playwright Page 对象
        max_notes: 每轮最多点击的笔记数量（默认20）
        total_rounds: 总共执行的轮次（默认1，设置>1可循环）
    browse_images_arrow_count: 进入详情页后按右键浏览图片的次数（默认5）
    content_description: 内容描述，用于过滤笔记（让 LLM 只选择符合描述的笔记）
    output_dir: 输出目录路径，用于保存截图
    recursion_limit: LangGraph 递归上限（默认100，避免多轮循环时达到25的默认限制）
    """
    app = create_click_graph()
    initial_state: ClickGraphState = {
        "page": page,
        "max_notes": max_notes,
        "press_escape_after_click": True,
        "browse_images_arrow_count": browse_images_arrow_count,
        "content_description": content_description,
        "output_dir": output_dir,
        "coordinates": [],
        "current_index": 0,
        "clicked": [],
        "failures": [],
        "screenshot_base64": None,
        "step": "start",
        "total_rounds": total_rounds,
        "current_round": 1,
    }
    return await app.ainvoke(initial_state, config={"recursion_limit": recursion_limit})
