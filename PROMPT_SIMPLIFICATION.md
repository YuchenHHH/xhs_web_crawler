# Prompt 简化说明

## 修改内容

### 简化前的 Prompt 要求

原来的 prompt 要求大模型返回：
```json
{
  "notes": [
    {
      "index": 0,
      "click_x": 300,
      "click_y": 450,
      "bounding_box": {
        "x": 200,
        "y": 350,
        "width": 200,
        "height": 250
      },
      "title": "笔记标题",
      "note_id": "ID（如果能识别）"
    }
  ]
}
```

### 简化后的 Prompt 要求

现在只要求返回核心字段：
```json
{
  "notes": [
    {
      "index": 0,
      "click_x": 300,
      "click_y": 450
    }
  ]
}
```

**必需字段**：
- `click_x`: 点击的 x 坐标
- `click_y`: 点击的 y 坐标

**可选字段**（如果大模型仍然返回也没问题）：
- `bounding_box`: 边界框信息
- `title`: 笔记标题
- `note_id`: 笔记ID

## 代码兼容性

### ✅ 无需修改的部分

所有使用这些字段的代码都已经使用了 `.get()` 方法并提供了默认值，因此**完全向后兼容**：

1. **agent/click_nodes.py**:
   ```python
   title = coord.get("title", "N/A")[:30]  # 默认 "N/A"
   note_id = coord.get("note_id", "")      # 默认空字符串
   verification = await verifier.validate(
       page, click_x, click_y,
       coord.get("bounding_box")           # 默认 None
   )
   ```

2. **core/click_verifier.py**:
   ```python
   async def validate(
       self, page: Page, x: int, y: int,
       bounding_box: Optional[Dict] = None  # 可选参数
   ):
       # bounding_box 为 None 时会跳过这个检查
       if bounding_box and self._point_in_bbox(x, y, bounding_box):
           ...
   ```

### ✅ 已优化的部分

**core/vision_locator.py** - `_parse_response` 方法：

```python
# 验证和清理数据（现在只需要坐标）
for note in notes:
    # 必须有坐标才有效
    if "click_x" not in note or "click_y" not in note:
        continue

    cleaned_notes.append({
        "index": note.get("index", len(cleaned_notes)),
        "click_x": int(note["click_x"]),
        "click_y": int(note["click_y"]),
        # 以下字段可选，如果大模型返回就保留，否则为空
        "bounding_box": note.get("bounding_box", {}),
        "title": note.get("title", ""),
        "note_id": note.get("note_id", "")
    })
```

## 优势

### 1. **降低大模型负担**
- 减少输出字段，降低 token 消耗
- 提高识别速度
- 减少解析错误的可能性

### 2. **提高准确性**
- 只关注核心任务：找到可点击的坐标
- 减少因为提取标题/ID 失败导致的整体失败
- `bounding_box` 不准确时不会影响点击验证（会使用 DOM 查询）

### 3. **容错性更好**
- 即使大模型漏掉可选字段，坐标识别仍然有效
- 验证逻辑自动使用 DOM 方法作为兜底

## 验证逻辑层级

现在的点击验证有多层保障（从高到低）：

1. **坐标直接命中**（`_element_from_point`）
   - 检查坐标位置的 DOM 元素是否是笔记卡片

2. **DOM 笔记卡片包含**（`_collect_note_rects`）
   - 查询所有笔记卡片的边界框
   - 检查坐标是否在某个卡片内
   - 如果是，调整到卡片中心

3. **Vision 边界框验证**（`bounding_box` - 可选）
   - 如果大模型提供了边界框，验证坐标是否在内
   - **这一层现在是可选的**

4. **最近卡片中心兜底**（`_find_nearest`）
   - 找到离坐标最近的笔记卡片中心
   - 建议使用该中心坐标

## 测试建议

运行测试，确认：

1. ✅ 大模型能正确返回只包含 `click_x` 和 `click_y` 的 JSON
2. ✅ 点击验证逻辑正常工作
3. ✅ 即使没有 `title`，日志输出也正常（显示 "N/A"）
4. ✅ 即使没有 `bounding_box`，验证仍然能通过 DOM 方法成功

## 示例输出

### 简化后的 JSON 响应

```json
{
  "notes": [
    {"index": 0, "click_x": 450, "click_y": 380},
    {"index": 1, "click_x": 750, "click_y": 380},
    {"index": 2, "click_x": 1050, "click_y": 380},
    {"index": 3, "click_x": 450, "click_y": 720},
    {"index": 4, "click_x": 750, "click_y": 720}
  ]
}
```

### 控制台输出

```
✅ 成功识别 5 个笔记位置（原始: 5）
   1. 坐标: (450, 380) - N/A
   2. 坐标: (750, 380) - N/A
   3. 坐标: (1050, 380) - N/A
```

## 回滚方案

如果需要恢复原来的 prompt，只需：

1. 在 `_build_prompt` 中恢复完整的输出格式要求
2. 代码无需修改（已兼容两种情况）
