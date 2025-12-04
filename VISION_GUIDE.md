# GPT-4o Vision 分析功能使用指南

本文档详细介绍如何使用项目中的视觉分析功能。

## 功能概述

视觉分析模块 ([core/vision_analyzer.py](core/vision_analyzer.py)) 使用 **OpenAI GPT-4o Vision API** 来分析小红书搜索结果页面的截图，自动识别并提取：

- 📝 **笔记标题**
- 👤 **作者名**
- ❤️  **点赞数**（保留原始格式，如 "1.2万"）
- 🏷️ **视觉标签**（基于封面图片内容生成）

## 架构设计

### 核心组件

```
VisionAnalyzer 类
├── capture_screenshot()   # 截取当前页面
├── analyze_image()        # 调用 GPT-4o 分析
└── analyze_page()         # 便捷方法：截图 + 分析
```

### 工作流程

```
1. 截图 → 2. Base64 编码 → 3. GPT-4o Vision API → 4. JSON 清洗 → 5. 返回结构化数据
```

## 快速开始

### 1. 安装依赖

```bash
pip install openai>=1.12.0
```

### 2. 配置 API Key

**方法一：环境变量（推荐）**
```bash
export OPENAI_API_KEY='sk-xxxxxxxxxxxxxxxxxxxxxxxx'
```

**方法二：代码中设置**
```python
import os
os.environ['OPENAI_API_KEY'] = 'sk-xxxxxxxxxxxxxxxxxxxxxxxx'
```

### 3. 使用示例

#### 方式 A：独立使用

```python
from core.vision_analyzer import VisionAnalyzer
from playwright.async_api import async_playwright

async def demo():
    # 初始化分析器
    analyzer = VisionAnalyzer()

    # 启动浏览器（你的现有代码）
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    page = await browser.new_page()

    # 导航到搜索结果页
    await page.goto("https://www.xiaohongshu.com/search_result?keyword=穿搭")
    await page.wait_for_load_state("load")

    # 执行视觉分析
    result = await analyzer.analyze_page(page)

    # 处理结果
    notes = result.get("notes", [])
    for note in notes:
        print(f"标题: {note['title']}")
        print(f"作者: {note['author']}")
        print(f"点赞: {note['likes']}")
        print(f"标签: {', '.join(note['tags'])}")
```

#### 方式 B：集成到 Agent 工作流

项目已经实现了 `vision_analysis_node`，可以直接集成：

```python
# 在 agent/graph.py 中取消注释
workflow.add_node("vision_analysis", vision_analysis_node)
workflow.add_edge("search_keyword", "vision_analysis")
workflow.add_edge("vision_analysis", END)
```

然后运行：
```bash
python example_with_vision.py
```

## API 参考

### VisionAnalyzer 类

#### `__init__(api_key: Optional[str] = None)`

初始化分析器。

**参数：**
- `api_key`: OpenAI API Key，默认从环境变量 `OPENAI_API_KEY` 读取

**示例：**
```python
# 从环境变量读取
analyzer = VisionAnalyzer()

# 手动指定
analyzer = VisionAnalyzer(api_key="sk-xxx")
```

#### `capture_screenshot(page: Page) -> str`

截取当前页面可视区域。

**参数：**
- `page`: Playwright Page 对象

**返回：**
- Base64 编码的 PNG 图片字符串

**注意事项：**
- 只截取当前窗口（`full_page=False`），保证清晰度
- 图片自动编码为 Base64

#### `analyze_image(base64_image: str, custom_prompt: Optional[str] = None) -> Dict`

使用 GPT-4o 分析截图。

**参数：**
- `base64_image`: Base64 编码的图片
- `custom_prompt`: 自定义 Prompt（可选）

**返回：**
```python
{
  "notes": [
    {
      "title": "笔记标题",
      "author": "作者名",
      "likes": "1.2万",
      "tags": ["标签1", "标签2", "标签3"]
    }
  ]
}
```

**自定义 Prompt 示例：**
```python
custom_prompt = """
请识别图片中的笔记，并提取：
1. 标题
2. 封面主色调
3. 是否为视频内容

返回 JSON 格式。
"""

result = await analyzer.analyze_image(base64_image, custom_prompt)
```

#### `analyze_page(page: Page) -> Dict`

便捷方法：截图 + 分析一步完成。

**参数：**
- `page`: Playwright Page 对象

**返回：**
- 同 `analyze_image()`

## 输出格式

### 标准输出

```json
{
  "notes": [
    {
      "title": "秋冬穿搭｜极简风格通勤搭配",
      "author": "小红书用户123",
      "likes": "1.2万",
      "tags": ["穿搭", "极简", "通勤"]
    },
    {
      "title": "日系家居｜治愈系卧室改造",
      "author": null,
      "likes": "8765",
      "tags": ["家居", "日系", "治愈"]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `title` | `str` | 笔记标题 | "秋冬穿搭指南" |
| `author` | `str \| null` | 作者名，如不可见则为 `null` | "用户ABC" |
| `likes` | `str \| null` | 点赞数，保留原始字符串 | "1.2万" |
| `tags` | `List[str]` | 3个视觉标签（基于封面图片） | `["穿搭", "极简", "秋季"]` |

## 高级用法

### 1. 批量处理多页

```python
async def crawl_multiple_pages(keyword: str, pages: int = 3):
    analyzer = VisionAnalyzer()
    all_notes = []

    # 启动浏览器
    page = await setup_browser()
    await page.goto(f"https://www.xiaohongshu.com/search_result?keyword={keyword}")

    for i in range(pages):
        # 分析当前页
        result = await analyzer.analyze_page(page)
        all_notes.extend(result.get("notes", []))

        # 滚动加载下一页
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    return all_notes
```

### 2. 保存截图（调试用）

```python
# 在 analyze_page 前先保存截图
base64_image = await analyzer.capture_screenshot(page)

# 解码并保存
import base64
with open("debug_screenshot.png", "wb") as f:
    f.write(base64.b64decode(base64_image))

# 再进行分析
result = await analyzer.analyze_image(base64_image)
```

### 3. 错误处理

```python
try:
    result = await analyzer.analyze_page(page)
except ValueError as e:
    # API Key 错误或未设置
    print(f"配置错误: {e}")
except Exception as e:
    # 其他错误（网络、超时等）
    print(f"分析失败: {e}")
```

## 常见问题

### Q1: 为什么识别不准确？

**可能原因：**
1. 页面未完全加载，建议增加等待时间
2. 小红书页面布局变化
3. 截图质量不足

**解决方案：**
```python
# 等待页面稳定
await page.wait_for_load_state("networkidle", timeout=10000)
await asyncio.sleep(2)

# 调整视口大小（增加可见内容）
await page.set_viewport_size({"width": 1920, "height": 1080})
```

### Q2: JSON 解析失败

**错误信息：** `ValueError: 无法解析 LLM 返回的 JSON`

**原因：** GPT-4o 返回了 Markdown 格式或非 JSON 内容

**解决方案：**
- 已内置 `_clean_and_parse_json()` 方法自动处理
- 如果仍然失败，检查 `custom_prompt` 是否明确要求纯 JSON 输出

### Q3: API 调用超时

**解决方案：**
```python
# 设置更长的超时时间（默认 60s）
client = AsyncOpenAI(api_key=api_key, timeout=120.0)
```

### Q4: 成本控制

每次分析约消耗：
- 输入 tokens: ~1000 (图片 + Prompt)
- 输出 tokens: ~500 (JSON 数据)
- 约 $0.01-0.02 / 次

**优化建议：**
- 使用 `temperature=0.2` 减少随机性
- 批量处理而非单条请求
- 缓存已分析的页面

## 测试命令

### 独立测试视觉分析

```bash
python example_with_vision.py --test-vision
```

此命令会：
1. 启动浏览器
2. 提示你手动导航到搜索结果页
3. 执行视觉分析
4. 输出结果并保存到 `vision_test_result.json`

### 完整流程测试

```bash
export OPENAI_API_KEY='your-key'
python example_with_vision.py
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `core/vision_analyzer.py` | VisionAnalyzer 核心实现 |
| `agent/nodes.py` | 包含 `vision_analysis_node` |
| `example_with_vision.py` | 完整使用示例 |
| `VISION_GUIDE.md` | 本文档 |

## 相关资源

- [OpenAI Vision API 文档](https://platform.openai.com/docs/guides/vision)
- [Playwright 截图文档](https://playwright.dev/python/docs/screenshots)
- [项目 README](README.md)
