# 小红书爬虫 Agent

基于 **GPT-4o Vision + Playwright + LangGraph** 的智能小红书自动化爬虫系统。

使用 **Set-of-Marks (SoM)** 视觉定位技术，通过 GPT-4o 智能识别和筛选笔记内容，自动浏览、截图并保存小红书笔记。

## ✨ 核心特性

### 🎯 智能内容识别

- **Set-of-Marks (SoM) 视觉定位**：在页面元素上标注数字标记，让 GPT-4o 准确识别目标
- **智能内容过滤**：根据自然语言描述（如"与菜肴相关的内容"）自动筛选笔记
- **自动去重**：使用感知哈希 (dhash) 算法检测重复图片，避免重复浏览

### 🤖 全自动化流程

- 自动登录检测与 Cookie 持久化
- 关键词搜索与结果页滚动加载
- 智能点击笔记卡片并进入详情页
- 自动浏览图片轮播（按右键键）并截图保存
- 多轮执行支持（滚动加载更多内容）

### 🛡️ 反爬虫优化

- User-Agent 伪装
- Stealth JS 注入（隐藏 webdriver 特征）
- 模拟人类操作速度（可配置延迟）
- GPT-4o 调用失败自动重试机制

### 🔧 高度可配置

- 全局配置文件统一管理
- 支持自定义搜索关键词和内容描述
- 可调整点击数量、执行轮次、图片浏览次数
- 灵活的视口大小和超时设置

## 📁 项目结构

```text
xhs_crawler_agent/
├── config/                          # 配置层
│   ├── __init__.py
│   └── settings.py                  # 全局配置（浏览器、OpenAI、超时等）
├── core/                            # 核心能力层
│   ├── __init__.py
│   ├── browser_manager.py           # 浏览器管理（启动/Cookie/Stealth）
│   ├── som_marker.py                # SoM 标记注入器
│   ├── som_vision_locator.py        # SoM 视觉定位器（GPT-4o）
│   ├── vision_analyzer.py           # 通用视觉分析器
│   ├── vision_locator.py            # 传统视觉定位器
│   ├── note_extractor.py            # 笔记内容提取器
│   ├── file_manager.py              # 文件管理工具
│   └── click_verifier.py            # 点击验证器
├── agent/                           # 业务逻辑层（LangGraph）
│   ├── __init__.py
│   ├── state.py                     # Agent 状态定义
│   ├── nodes.py                     # 基础节点（登录/搜索等）
│   ├── click_nodes.py               # 点击相关节点
│   └── graph.py                     # LangGraph 流程编排
├── scripts/                         # 工具脚本
│   ├── batch_filter_images.py       # 批量图片过滤
│   └── download_xhs_video.py        # 视频下载工具
├── output/                          # 输出目录（自动创建）
│   └── {关键词}_{时间戳}/          # 每次执行的输出
│       ├── note_1/                 # 单个笔记的截图
│       ├── note_2/
│       └── ...
├── main.py                          # 程序主入口
├── requirements.txt                 # Python 依赖
├── .env                            # 环境变量（需自行创建）
├── auth.json                        # Cookie 存储（自动生成）
└── README.md                        # 项目说明
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd xhs_crawler_agent
```

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器驱动
playwright install chromium
```

### 3. 配置 OpenAI API Key

创建 `.env` 文件并添加你的 API Key：

```bash
echo "OPENAI_API_KEY='your-api-key-here'" > .env
```

或者在环境变量中设置：

```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 4. 配置爬虫参数

编辑 `main.py` 中的配置参数（第 44-48 行）：

```python
keyword = "番茄炒蛋"  # 搜索关键词
description = "挑选其中 与菜肴相关的内容"  # 内容过滤描述
max_notes = 20  # 每轮最多点击的笔记数量
total_rounds = 10  # 总共执行的轮次
browse_images_count = 20  # 每个笔记浏览图片的次数
```

### 5. 运行程序

```bash
python main.py
```

首次运行时，程序会：

1. 打开浏览器并访问小红书
2. 检测登录状态（如果未登录，会暂停等待手动登录）
3. 手动登录后，Cookie 会自动保存到 `auth.json`
4. 下次运行时会自动加载 Cookie，无需再次登录

## 📖 详细使用说明

### 工作流程

1. **初始化浏览器**：启动 Chromium 浏览器并配置反爬虫参数
2. **登录检测**：检查是否已登录，如未登录则等待手动操作
3. **关键词搜索**：输入搜索关键词并等待结果加载
4. **智能识别笔记**：
   - 使用 SoM 技术在笔记卡片上注入数字标记
   - GPT-4o Vision 识别标记并根据内容描述过滤
   - 返回符合条件的笔记列表
5. **点击并浏览**：
   - 依次点击识别到的笔记
   - 进入详情页后按右键浏览图片轮播
   - 对每张图片截图并保存
   - 检测到重复图片时自动停止
6. **返回并继续**：返回搜索结果页，继续下一个笔记
7. **多轮执行**：完成一轮后滚动页面加载更多内容，继续下一轮

### 核心功能模块

#### 1. Set-of-Marks (SoM) 视觉定位

SoM 是一种创新的视觉定位技术，通过在页面元素上叠加数字标记，让 GPT-4o 更准确地识别目标。

```python
from core.som_vision_locator import SoMVisionLocator

locator = SoMVisionLocator()
notes = await locator.locate_note_cards(
    page=page,
    max_notes=20,
    content_description="与菜肴相关的内容"
)
```

**优势**：

- 比坐标定位更准确（不受页面滚动影响）
- 支持自然语言内容过滤
- 自动排除搜索推荐、导航栏等干扰元素

#### 2. 智能内容过滤

通过自然语言描述过滤笔记内容：

```python
description = "挑选其中 与菜肴相关的内容"
# GPT-4o 会分析笔记的封面图和标题，只返回与菜肴相关的笔记
```

支持的过滤类型：

- 内容主题（"美食"、"穿搭"、"旅游"等）
- 视觉风格（"极简风格"、"色彩丰富"等）
- 特定对象（"包含人物"、"室内场景"等）

#### 3. 图片去重检测

使用 dhash（差分哈希）算法自动检测重复图片：

```python
# 在 config/settings.py 中配置
# 或在 agent/click_nodes.py:305 中修改阈值

if distance <= 4:  # 阈值越小越严格
    print("检测到图片高度相似，结束浏览")
    break
```

**阈值说明**：

- `0`: 图片完全相同
- `1-4`: 图片非常相似（推荐，当前设置）
- `5-8`: 图片较相似
- `>8`: 图片差异较大

#### 4. GPT-4o 自动重试机制

当 GPT-4o 调用失败或返回空响应时，自动重试：

```python
# 在 config/settings.py 中配置
OPENAI_MAX_RETRIES = 3  # 最大重试次数
OPENAI_RETRY_DELAY = 2  # 重试延迟（秒）
```

会自动处理以下错误：

- 空响应
- JSON 解析失败
- 网络超时
- API 限流

## ⚙️ 配置说明

### 全局配置 (config/settings.py)

#### 浏览器配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `HEADLESS` | 无头模式（True=后台运行） | `False` |
| `SLOW_MO` | 操作延迟（毫秒） | `500` |
| `VIEWPORT` | 浏览器窗口大小 | `{"width": 1440, "height": 900}` |
| `USER_AGENT` | 浏览器标识 | Chrome 120 |
| `DEFAULT_TIMEOUT` | 默认超时（毫秒） | `10000` |

#### OpenAI 配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_MODEL` | 使用的模型 | `gpt-4o` |
| `OPENAI_TEMPERATURE` | 模型温度 | `0.2` |
| `OPENAI_MAX_TOKENS` | 最大 token 数 | `2000` |
| `OPENAI_MAX_RETRIES` | 最大重试次数 | `3` |
| `OPENAI_RETRY_DELAY` | 重试延迟（秒） | `2` |

#### 小红书相关配置

| 配置项 | 说明 |
|--------|------|
| `XHS_HOME_URL` | 小红书首页 URL |
| `XHS_SEARCH_INPUT_SELECTORS` | 搜索框选择器列表 |
| `XHS_NOTE_CARD_SELECTORS` | 笔记卡片选择器列表 |
| `SCROLL_PAUSE_TIME` | 滚动后等待时间（秒） |
| `MAX_SCROLL_ATTEMPTS` | 最大滚动尝试次数 |

### 运行参数配置 (main.py)

```python
# 搜索配置
keyword = "番茄炒蛋"           # 搜索关键词
description = "与菜肴相关"      # 内容过滤描述

# 执行配置
max_notes = 20                 # 每轮点击的笔记数
total_rounds = 10              # 执行轮次
browse_images_count = 20       # 每个笔记浏览图片次数
```

## 🔧 高级用法

### 1. 自定义内容过滤逻辑

编辑 `core/som_vision_locator.py` 中的 Prompt（第 178-274 行）：

```python
def _build_som_prompt(self, max_notes, total_marks, content_description):
    prompt = f"""你是一个网页元素识别专家...

    **内容过滤要求**：
    {content_description}

    **你必须**：
    1. 仔细观察每个标记对应的笔记封面图和标题
    2. 只选择符合描述的笔记
    3. 宁可少选，不要选错
    """
```

### 2. 调整图片相似度阈值

编辑 `agent/click_nodes.py` 第 305 行：

```python
if distance <= 4:  # 修改这个数值
    print("检测到图片高度相似")
    break
```

### 3. 添加自定义节点

在 `agent/nodes.py` 中添加新节点：

```python
async def my_custom_node(state: dict) -> dict:
    """自定义节点功能"""
    page = state["page"]

    # 你的逻辑
    await page.click("...")

    return {"step": "my_step_completed"}
```

然后在 `agent/graph.py` 中注册节点：

```python
from agent.nodes import my_custom_node

# 在 run_click_graph 中添加
await my_custom_node(state)
```

### 4. 批量处理多个关键词

创建一个循环脚本：

```python
keywords = ["番茄炒蛋", "宫保鸡丁", "麻婆豆腐"]

for keyword in keywords:
    # 修改 state 中的 search_keyword
    # 运行爬虫流程
    await run_crawler(keyword)
```

## 📊 输出说明

### 文件结构

```text
output/
└── {关键词}_{时间戳}/
    ├── note_1/
    │   ├── image_1.png
    │   ├── image_2.png
    │   └── ...
    ├── note_2/
    │   ├── image_1.png
    │   └── ...
    └── ...
```

### 控制台输出示例

```text
🤖 小红书爬虫 Agent 启动
📁 输出目录: output/番茄炒蛋_20250112_143022

📋 初始配置:
   - 搜索关键词: 番茄炒蛋
   - 内容描述: 挑选其中 与菜肴相关的内容
   - 每轮点击数: 20
   - 执行轮次: 10

🚀 [BrowserManager] 正在启动浏览器...
✅ [BrowserManager] 浏览器启动成功

🔍 开始搜索关键词: 番茄炒蛋
🎯 使用 SoM 方案识别笔记（最多 20 个）
   - 正在调用 GPT-4o Vision 识别标记...
✅ GPT-4o 识别到 15 个标记: [1, 2, 3, 4, 5, ...]
🧹 已清除 SoM 标记
🎯 成功定位 15 个笔记元素

📍 开始点击第 1 个笔记...
   - 正在浏览图片轮播...
   - 💾 保存: image_1.png
   - 💾 保存: image_2.png
   - 📸 检测到图片高度相似（dhash 距离=3），结束浏览（共 2 张）
   - ⏪ 返回搜索结果页

✅ 程序执行完毕
```

## 🛠️ 工具脚本

### 批量图片过滤

使用 GPT-4o Vision 批量过滤已下载的图片：

```bash
python scripts/batch_filter_images.py
```

功能：

- 分析图片内容
- 根据自定义描述过滤
- 输出过滤结果到 JSON

### 视频下载

下载小红书视频：

```bash
python scripts/download_xhs_video.py
```

## ❓ 常见问题

### 1. GPT-4o 返回空响应或解析失败

**现象**：

```text
⚠️  JSON 解析失败: Expecting value: line 1 column 1 (char 0)
原始响应:
```

**解决方案**：

- 程序已内置自动重试机制（默认重试 3 次）
- 检查网络连接是否稳定
- 确认 OpenAI API Key 是否有效
- 可以在 `config/settings.py` 中增加重试次数

### 2. 搜索框定位失败

**现象**：

```text
❌ 所有选择器都失败，无法定位搜索框
```

**解决方案**：

- 小红书页面结构可能已更新
- 打开浏览器开发者工具，找到搜索框的新选择器
- 在 `config/settings.py` 中更新 `XHS_SEARCH_INPUT_SELECTORS`

### 3. Cookie 加载失败

**现象**：

```text
⚠️  未找到 Cookie 文件: auth.json
```

**解决方案**：

- 首次运行需要手动登录
- 登录后 Cookie 会自动保存
- 确保项目根目录有写入权限

### 4. 浏览器窗口太小/太大

**解决方案**：
在 `config/settings.py` 中修改视口大小：

```python
VIEWPORT = {
    "width": 1920,   # 修改宽度
    "height": 1080   # 修改高度
}
```

常见分辨率：

- 1440x900 (MacBook Air 13")
- 1920x1080 (Full HD)
- 2560x1440 (2K)

### 5. 笔记识别不准确

**解决方案**：

- 优化内容描述，使其更具体
- 调整 `max_notes` 参数，减少单次识别数量
- 检查 SoM 标记是否正确注入（查看浏览器截图）

### 6. 图片重复检测太敏感/不敏感

**解决方案**：
在 `agent/click_nodes.py:305` 调整阈值：

```python
# 更严格（容易判定为重复）
if distance <= 2:

# 更宽松（不易判定为重复）
if distance <= 8:
```

## 🔐 安全与隐私

- 本项目仅供学习和研究使用
- 请遵守小红书的服务条款和 robots.txt
- 不要用于商业目的或大规模爬取
- 建议设置合理的延迟时间，避免对服务器造成压力
- Cookie 和 API Key 等敏感信息请妥善保管

## 📝 开发路线

- [x] 基础架构搭建（LangGraph + Playwright）
- [x] 浏览器管理与反爬虫优化
- [x] 登录检测与 Cookie 持久化
- [x] 关键词搜索与结果加载
- [x] Set-of-Marks (SoM) 视觉定位
- [x] GPT-4o Vision 智能识别
- [x] 智能内容过滤
- [x] 图片浏览与截图保存
- [x] 图片去重检测
- [x] 多轮滚动加载
- [x] GPT-4o 自动重试机制
- [ ] 笔记详情提取（标题、作者、点赞数等）
- [ ] 数据持久化（数据库存储）
- [ ] 并发爬取支持
- [ ] Web UI 管理界面

## 🛡️ 技术栈

- **Python 3.8+**
- **Playwright** - 浏览器自动化
- **LangGraph** - 工作流编排
- **OpenAI GPT-4o** - 视觉识别与内容理解
- **Pillow (PIL)** - 图片处理与哈希计算
- **asyncio** - 异步编程

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请提交 Issue。

---

**⚠️ 免责声明**：本项目仅供学习和研究使用，请勿用于违反小红书服务条款的行为。使用本项目产生的任何后果由使用者自行承担。
