# 小红书爬虫 Agent

基于 LangGraph + Playwright 的模块化小红书自动化爬虫项目。

## 项目结构

```
xhs_crawler_agent/
├── config/                      # 配置层
│   ├── __init__.py
│   └── settings.py              # 全局配置（USER_AGENT, TIMEOUT, URL等）
├── core/                        # 核心能力层
│   ├── __init__.py
│   ├── browser_manager.py       # 浏览器管理器（启动/关闭/Cookie/Stealth）
│   └── vision_analyzer.py       # GPT-4o Vision 分析器
├── agent/                       # 业务逻辑层
│   ├── __init__.py
│   ├── state.py                 # Agent 状态定义
│   ├── nodes.py                 # 节点函数（init/login/search/vision）
│   └── graph.py                 # LangGraph 流程编排
├── main.py                      # 程序入口（基础版）
├── example_with_vision.py       # 完整示例（含视觉分析）
├── requirements.txt             # 依赖列表
└── README.md                    # 项目说明
```

## 功能特性

- ✅ 浏览器自动化（Playwright）
- ✅ 反爬虫伪装（User-Agent + Stealth JS）
- ✅ Cookie 持久化（维持登录态）
- ✅ 登录状态检测
- ✅ 关键词搜索
- ✅ **GPT-4o Vision 分析**（识别笔记标题、作者、点赞数、标签）
- 🚧 图片下载（预留）

## 快速开始

### 1. 安装依赖

```bash
cd xhs_crawler_agent
pip install -r requirements.txt

# 安装 Playwright 浏览器驱动
playwright install chromium
```

### 2. 配置（可选）

编辑 `config/settings.py`：

```python
HEADLESS = False  # False=可视化调试，True=无头模式
SLOW_MO = 500     # 操作延迟（毫秒）
```

### 3. 配置 OpenAI API Key（使用视觉分析功能时必需）

```bash
export OPENAI_API_KEY='your-api-key-here'
```

或在代码中设置：
```python
import os
os.environ['OPENAI_API_KEY'] = 'your-api-key-here'
```

### 4. 运行

**基础版（不含视觉分析）：**
```bash
python main.py
```

**完整版（含 GPT-4o Vision 分析）：**
```bash
python example_with_vision.py
```

**仅测试视觉分析功能：**
```bash
python example_with_vision.py --test-vision
```

## 使用说明

### 使用视觉分析功能

视觉分析功能使用 **GPT-4o Vision API** 来识别搜索结果页面中的笔记信息：

```python
from core.vision_analyzer import VisionAnalyzer

# 1. 初始化分析器
analyzer = VisionAnalyzer()

# 2. 分析当前页面（截图 + 分析）
result = await analyzer.analyze_page(page)

# 3. 获取结果
notes = result.get("notes", [])
for note in notes:
    print(f"标题: {note['title']}")
    print(f"作者: {note['author']}")
    print(f"点赞: {note['likes']}")
    print(f"标签: {note['tags']}")
```

**提取字段说明：**
- `title`: 笔记标题
- `author`: 作者名
- `likes`: 点赞数（保留原始格式，如 "1.2万"）
- `tags`: 基于图片内容生成的 3 个视觉标签

### 修改搜索关键词

编辑 `main.py` 中的 `initial_state`：

```python
initial_state = {
    "search_keyword": "你的关键词",  # 修改这里
    ...
}
```

### 保存登录状态

1. 第一次运行时，程序会打开浏览器
2. 手动登录小红书
3. 在 `main.py` 中取消注释以下代码：

```python
if final_state.get("is_logged_in"):
    await browser_manager.save_cookies()
```

4. Cookie 会保存到项目根目录的 `auth.json`
5. 下次运行时自动加载 Cookie

### 扩展功能

在 `agent/graph.py` 中添加新节点：

```python
# 1. 在 nodes.py 中实现新节点函数
async def my_new_node(state: AgentState) -> dict:
    # 你的逻辑
    return {"step": "my_step_completed"}

# 2. 在 graph.py 中添加节点
workflow.add_node("my_node", my_new_node)
workflow.add_edge("search_keyword", "my_node")
workflow.add_edge("my_node", END)
```

## 配置说明

### config/settings.py

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `HEADLESS` | 无头模式 | `False` |
| `SLOW_MO` | 操作延迟（毫秒） | `500` |
| `USER_AGENT` | 浏览器标识 | Chrome 120 |
| `DEFAULT_TIMEOUT` | 默认超时（毫秒） | `10000` |
| `XHS_HOME_URL` | 小红书首页 | explore |

## 常见问题

### 1. 搜索失败：选择器失效

**原因**：小红书页面结构变化
**解决**：在 `config/settings.py` 中更新 `XHS_SEARCH_INPUT_SELECTORS`

### 2. 无法加载 Cookie

**原因**：`auth.json` 不存在或格式错误
**解决**：手动登录一次并保存 Cookie

### 3. 登录检测不准确

**原因**：小红书页面结构变化
**解决**：在 `agent/nodes.py` 的 `check_login_node` 中更新选择器

## 开发路线

- [x] 基础架构搭建
- [x] 浏览器管理器
- [x] 登录状态检测
- [x] 关键词搜索
- [ ] 搜索结果解析
- [ ] 视觉分析节点
- [ ] 图片下载功能
- [ ] 内容提取
- [ ] 数据持久化

## 依赖项

- Python >= 3.8
- Playwright >= 1.40.0
- LangGraph >= 0.0.30
- LangChain >= 0.1.0

## 许可证

MIT License
