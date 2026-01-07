# Cover Generator - 封面生成器

一个基于 Python 的图形化封面生成工具，支持模板化设计、批量处理和可视化编辑。

## 📋 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [安装与运行](#安装与运行)
- [项目结构](#项目结构)
- [核心概念](#核心概念)
- [使用指南](#使用指南)
- [代码架构](#代码架构)
- [API 文档](#api-文档)
- [模板格式](#模板格式)
- [常见问题](#常见问题)

## 项目简介

Cover Generator 是一个用于快速生成图片封面的桌面应用程序。它通过模板系统定义封面布局，支持图片插槽、文本块、多种背景样式，并提供可视化的模板编辑器。适用于批量生成应用截图封面、产品宣传图等场景。

## 功能特性

### 核心功能

- **模板化设计**：通过 JSON 文件定义可复用的封面模板
- **可视化编辑**：内置模板编辑器，支持拖拽调整元素位置
- **多种背景**：支持纯色、图片、线性/径向渐变背景
- **图片插槽**：支持多个图片插槽，自动适配（cover/contain）、圆角处理、对齐方式控制，并支持旋转整个插槽
- **文本渲染**：支持任意文本块（由模板 `texts[].key` 定义），包含字体、颜色、对齐、阴影等样式
- **批量处理**：通过 CSV 文件批量生成封面
- **实时预览**：生成前可预览效果

### 界面功能

- **表单模式**：根据模板的 `texts/slots` 动态输入文本与图片
- **CSV 批量模式**：从 CSV 文件读取数据批量生成
- **模板管理**：导入、编辑、保存模板
- **输出管理**：自定义输出目录和文件名

## 技术栈

- **Python 3.11+**
- **Pillow (PIL)**：图像处理和渲染
- **NumPy**：高效的渐变计算
- **Tkinter**：图形用户界面（Python 标准库）

## 安装与运行

### 环境要求

- Python 3.11 或更高版本
- macOS / Windows / Linux

### 安装步骤

1. **克隆或下载项目**

```bash
cd "assembly line"
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

依赖包：
- `Pillow>=10.0.0` - 图像处理库
- `numpy>=1.26.0` - 数值计算库

3. **运行应用**

```bash
python3 -m app.main
```

推荐使用 `python -m app.main` 启动（导入路径更稳定）。同时，程序也已兼容 `python app/main.py` 直接运行（内部会自动处理包导入），两种方式均可用。

### 首次运行

首次运行时会自动在 `app/templates/` 目录下创建默认模板（`default.json`）。

## 项目结构

```
assembly line/
├── app/                    # 主应用目录
│   ├── __init__.py        # 包初始化文件
│   ├── main.py            # 主程序入口，GUI 界面
│   ├── models.py          # 数据模型定义
│   ├── render.py          # 渲染引擎
│   ├── templates.py       # 模板管理
│   └── templates/         # 模板文件目录
│       ├── default.json   # 默认模板
│       └── template.json  # 示例模板
├── output/                 # 输出目录（自动创建）
│   └── cover.png          # 生成的封面示例
├── requirements.txt       # Python 依赖
├── 模板封面.json          # 示例模板文件
└── README.md              # 本文档
```

## 核心概念

### 1. 模板 (Template)

模板定义了封面的布局和样式，包括：
- **尺寸**：画布大小（宽 × 高）
- **背景**：颜色、图片或渐变
- **插槽 (Slots)**：图片放置区域
- **文本块 (Texts)**：任意文本区域（key 由模板定义）

### 2. 渲染输入 (RenderInput)

渲染输入包含生成封面所需的数据：
- `template_key`: 使用的模板键名
- `output_name`: 输出文件名
- `background_path`: 背景图片路径（可选，覆盖模板背景）
- `texts`: 文本映射（`textKey -> 文本内容`）
- `slot_paths`: 图片映射（`slotKey -> 图片路径`）

### 3. 插槽 (Slot)

图片插槽定义了图片在封面中的位置和样式：
- `key`: 唯一标识符
- `box`: 位置和大小 `[x, y, width, height]`
- `radius`: 圆角半径
- `fit`: 适配方式（`cover` 或 `contain`）
- `padding`: 内边距
- `align_x`: 水平对齐方式（`left` / `center` / `right`）
- `align_y`: 垂直对齐方式（`top` / `center` / `bottom`）

### 4. 文本块 (TextBlock)

文本块定义了文本的位置和样式：
- `key`: 标识符（自定义 key）
- `box`: 位置和大小
- `style`: 字体、大小、颜色、对齐等样式

## 使用指南

### 基本使用流程

1. **启动应用**
   ```bash
   python -m app.main
   ```

2. **选择模板**
   - 在顶部下拉框选择要使用的模板
   - 点击 "Reload" 重新加载模板
   - 点击 "Import JSON" 导入新模板

3. **表单模式生成**
   - 切换到 "表单" 标签页
   - 根据当前模板的 `texts/slots` 动态填写：
     - 文本：对应 `text.<key>`
     - 文本颜色（可选）：对应 `text.<key>.color`，留空则使用模板默认色
     - 图片：对应 `slot.<key>`
   - 选择背景图片（可选，覆盖模板背景）
   - 设置输出文件名
   - 确认顶部 **Output Dir**（默认输出到项目根目录的 `output/`）
   - 点击 "预览" 查看效果
   - 点击 "导出" 生成封面

4. **CSV 批量生成**
   - 切换到 "CSV 批量" 标签页
   - 选择 CSV 文件
   - 可先点击 "导出 CSV 模板" 生成当前模板对应的表头（推荐）
   - 点击 "批量生成"

### CSV 文件格式

CSV 文件 **仅支持按 key 显式映射的新 schema**。旧 schema（如 `title/subtitle/screenshots/template/output/background`）已不再支持。

> 重要：列名大小写规则
> - `template_key` / `output_name` / `background_path`：**列名大小写不敏感**
> - `text.<textKey>` / `slot.<slotKey>`：`text.` / `slot.` 前缀大小写不敏感，但 **`.` 后面的 `<textKey>/<slotKey>` 必须与模板中的 key 完全一致**（建议统一使用小写 key）
> 提示：从 Excel/WPS 导出的 CSV 可能带 BOM/零宽字符，程序已做兼容，无需手动处理。

#### 新 schema

| 列名 | 说明 | 示例 |
|------|------|------|
| `template_key` | 模板键名 | `left-right-green` |
| `output_name` | 输出文件名 | `case-001.png` |
| `background_path` | 覆盖模板背景图（可选） | `/path/to/bg.png` |
| `text.<textKey>` | 填充任意文本块（按模板 `texts[].key`） | `text.title`、`text.body` |
| `text.<textKey>.color` | 覆盖对应文本块的颜色（可选，十六进制） | `text.title.color` |
| `slot.<slotKey>` | 填充任意图片插槽（按模板 `slots[].key`） | `slot.main`、`slot.overlay`、`slot.background` |

**示例：**

```csv
template_key,output_name,background_path,text.title,text.title.color,text.subtitle,text.subtitle.color,slot.main
default,case-001.png,,一张表管公司,#111111,让业务流转起来,#444444,/abs/main.png

template_key,output_name,background_path,text.title,text.title.color,text.subtitle,text.subtitle.color,slot.background,slot.overlay,slot.main
left-right-green,case-002.png,,一张表管公司,#111111,让业务流转起来,#444444,/abs/bg.png,/abs/overlay.png,/abs/main.png
```

### 模板编辑器使用

1. **打开编辑器**
   - 点击主界面 "Template Editor" 按钮

2. **编辑模板**
   - **左侧面板**：全局设置（键名、名称、尺寸、背景）
   - **中间画布**：可视化预览，可点击选择元素，拖拽调整位置
   - **右侧面板**：选中元素的详细属性

3. **添加元素**
   - 点击 "+ Slot" 添加图片插槽
   - 点击 "+ Text" 添加文本块
   - 建议为元素设置**稳定且语义化的 key**（CSV 列名直接取决于 key）
   - key 约束：
     - 不允许为空
     - **不允许包含 `.`**
     - **大小写不敏感去重**（例如 `Title` 与 `title` 会被视为重复）

4. **调整元素**
   - 在画布上点击选择元素
   - 在右侧面板修改属性（位置、大小、样式等）
   - **插槽对齐**：对于图片插槽，可以设置水平和垂直对齐方式
     - 水平对齐：`left`（左对齐）、`center`（居中）、`right`（右对齐）
     - 垂直对齐：`top`（顶部）、`center`（居中）、`bottom`（底部）
   - 点击 "Apply Changes" 应用更改
   - **旋转插槽交互说明**：
     - 当 slot 设置了 `rotation/rotate_x/rotate_y` 时，画布上的预览会显示为旋转后的多边形
     - 点击命中与拖拽会按该多边形进行（不再按原 `box` 矩形范围）
     - 预览斜边已做抗锯齿处理（超采样绘制），视觉效果更接近最终导出

5. **保存模板**
   - 点击 "Save Template" 保存
   - 模板将保存到 `app/templates/` 目录

> 提示：编辑器字段覆盖范围
>
> 目前编辑器 UI 只支持一部分字段的可视化编辑，其他高级排版/效果需手动编辑模板 JSON。
>
> | 模块 | 编辑器 UI 支持 | 仅 JSON 支持（需手改） |
> |------|----------------|------------------------|
> | Background | `kind` / `value` / `opacity` / `gradient_type` / `gradient_angle` / `gradient_center` / `gradient_stops` | - |
> | Slot | `key` / `box` / `radius` / `fit` / `padding` / `align_x` / `align_y` / `rotation` / `rotate_x` / `rotate_y` | - |
> | Text | `key` / `box` / `style.font` / `style.size` / `style.color` / `style.align` | `style.max_width` / `style.line_spacing` / `style.stroke_width` / `style.stroke_fill` / `style.shadow` |

> 建议：团队协作/跨机器使用模板时，尽量避免在模板 JSON 中写死绝对路径（如 `/Users/...`）。推荐把字体/背景等资源放到项目目录（例如 `assets/`）并使用相对路径，或在运行时通过表单/CSV 的 `background_path` 与 `slot.<key>` 传入图片路径覆盖模板值。

## 代码架构

### 模块职责

#### `app/main.py` - 主程序

- **CoverApp**: 主应用窗口类
  - 管理 GUI 界面
  - 处理用户交互
  - 协调模板、渲染和文件操作

- **TemplateEditor**: 模板编辑器窗口类
  - 可视化编辑模板
  - 实时预览模板布局
  - 保存模板到文件

#### `app/models.py` - 数据模型

定义了所有数据结构：

- **BackgroundConfig**: 背景配置
  - `kind`: 类型（`color` / `image` / `gradient`）
  - `value`: 颜色值或图片路径
  - `opacity`: 透明度
  - `gradient_type`: 渐变类型（`linear` / `radial`）
  - `gradient_stops`: 渐变色标
  - `gradient_angle`: 线性渐变角度
  - `gradient_center`: 径向渐变中心点

- **Slot**: 图片插槽
  - `key`: 唯一标识
  - `box`: 位置和大小 `[x, y, width, height]`
  - `radius`: 圆角半径
  - `fit`: 适配方式（`cover` 或 `contain`）
  - `padding`: 内边距
  - `align_x`: 水平对齐方式（`left` / `center` / `right`），默认 `center`
  - `align_y`: 垂直对齐方式（`top` / `center` / `bottom`），默认 `center`

- **TextStyle**: 文本样式
  - `font`: 字体文件路径
  - `size`: 字体大小
  - `color`: 颜色（十六进制）
  - `align`: 对齐方式
  - `max_width`: 最大宽度
  - `line_spacing`: 行间距
  - `stroke_width`: 描边宽度
  - `stroke_fill`: 描边颜色
  - `shadow`: 阴影配置

- **TextBlock**: 文本块
  - `key`: 标识符
  - `box`: 位置和大小
  - `style`: 文本样式

- **TemplateDefinition**: 模板定义
  - `key`: 模板键名
  - `name`: 模板名称
  - `size`: 画布尺寸
  - `background`: 背景配置
  - `slots`: 插槽列表
  - `texts`: 文本块列表

- **RenderInput**: 渲染输入
  - `template_key`: 模板键名
  - `output_name`: 输出文件名
  - `background_path`: 背景图片路径（可选）
  - `texts`: 文本映射（`textKey -> 文本内容`）
  - `slot_paths`: 图片映射（`slotKey -> 图片路径`）

#### `app/render.py` - 渲染引擎

核心渲染函数：

- **`apply_background()`**: 应用背景（颜色/图片/渐变）
- **`place_slot()`**: 放置图片到插槽
- **`draw_text_block()`**: 绘制文本块
- **`compose_cover()`**: 组合所有元素生成封面
- **`render_to_file()`**: 渲染并保存到文件
- **`build_preview()`**: 生成预览图

辅助函数：

- **`_resize_fit()`**: 图片适配（cover/contain），支持水平和垂直对齐
- **`_round_corners()`**: 圆角处理
- **`_draw_gradient()`**: 渐变绘制（使用 NumPy 优化）

**对齐功能实现**：
- `_resize_fit()` 函数接受 `align_x` 和 `align_y` 参数
- 在 `contain` 模式下，根据对齐方式计算图片在画布中的位置
- 在 `cover` 模式下，根据对齐方式计算裁剪的起始位置
- `place_slot()` 函数从插槽配置中读取对齐方式并传递给 `_resize_fit()`

#### `app/templates.py` - 模板管理

- **TemplateRegistry**: 模板注册表
  - 加载、保存、管理模板
  - 从目录加载模板文件
  - 导入/导出 JSON

- **`default_template()`**: 创建默认模板
- **`template_to_dict()`**: 模板转字典（用于 JSON 序列化）

### 数据流

```
用户输入 (表单/CSV)
    ↓
RenderInput (数据模型)
    ↓
TemplateDefinition (模板定义)
    ↓
render.py (渲染引擎)
    ↓
PIL Image (图像对象)
    ↓
保存为 PNG 文件
```

## API 文档

### 模板加载

```python
from app.models import load_template_from_file, load_template_from_json
from pathlib import Path

# 从文件加载
template = load_template_from_file(Path("template.json"))

# 从字典加载
data = {...}  # JSON 数据
template = load_template_from_json(data)
```

### 模板管理

```python
from app.templates import TemplateRegistry
from pathlib import Path

registry = TemplateRegistry()
registry.load_with_default(Path("app/templates"))

# 获取模板
template = registry.get("default")

# 保存模板
registry.save_template(template, Path("app/templates/my_template.json"))

# 创建带对齐的插槽
from app.models import Slot, TemplateDefinition, BackgroundConfig

slot = Slot(
    key="screenshot-1",
    box=(90, 420, 900, 1080),
    radius=32,
    fit="cover",
    padding=0,
    align_x="left",   # 水平左对齐
    align_y="top"    # 垂直顶部对齐
)

template = TemplateDefinition(
    key="my-template",
    name="My Template",
    size=(1080, 1920),
    background=BackgroundConfig(kind="color", value="#f5f5f5"),
    slots=[slot],
    texts=[]
)
```

### 渲染

```python
from app.models import RenderInput
from app.render import render_to_file, build_preview
from pathlib import Path

# 创建渲染输入
render_input = RenderInput(
    template_key="default",
    output_name="cover.png",
    background_path="/path/to/bg.png",
    texts={"title": "我的标题", "subtitle": "副标题"},
    slot_paths={"main": "/path/to/screenshot.png"},
)

# 获取模板
template = registry.get("default")

# 渲染到文件
output_path = render_to_file(render_input, template, Path("output/cover.png"))

# 生成预览（返回 PIL Image）
preview_img = build_preview(render_input, template, max_size=480)
```

### CSV 批量处理

```python
from app.models import render_input_from_row
import csv

with open("data.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        render_input = render_input_from_row(row)
        # ... 渲染处理
```

## 模板格式

模板是 JSON 格式的文件，结构如下：

```json
{
  "key": "template-key",
  "name": "Template Name",
  "size": [1080, 1920],
  "background": {
    "kind": "color",
    "value": "#f5f5f5",
    "opacity": 1.0,
    "gradient_type": "linear",
    "gradient_angle": 90.0,
    "gradient_center": [0.5, 0.5],
    "gradient_stops": [
      {"color": "#ff0000", "position": 0.0},
      {"color": "#0000ff", "position": 1.0}
    ]
  },
  "slots": [
    {
      "key": "screenshot-1",
      "box": [90, 420, 900, 1080],
      "radius": 32,
      "fit": "cover",
      "padding": 0,
      "align_x": "center",
      "align_y": "center",
      "rotation": 0
    }
  ],
  "texts": [
    {
      "key": "title",
      "box": [90, 120, 900, 180],
      "style": {
        "font": null,
        "size": 64,
        "color": "#111111",
        "align": "left",
        "max_width": null,
        "line_spacing": 1.2,
        "stroke_width": 0,
        "stroke_fill": null,
        "shadow": {
          "offset": [2, 2],
          "color": "#00000088",
          "blur": 4
        }
      }
    }
  ]
}
```

### 背景类型

#### 1. 纯色背景

```json
{
  "kind": "color",
  "value": "#ffffff",
  "opacity": 1.0
}
```

#### 2. 图片背景

```json
{
  "kind": "image",
  "value": "/path/to/background.png",
  "opacity": 1.0
}
```

#### 3. 线性渐变

```json
{
  "kind": "gradient",
  "gradient_type": "linear",
  "gradient_angle": 90.0,
  "gradient_stops": [
    {"color": "#ff0000", "position": 0.0},
    {"color": "#0000ff", "position": 1.0}
  ],
  "opacity": 1.0
}
```

#### 4. 径向渐变

```json
{
  "kind": "gradient",
  "gradient_type": "radial",
  "gradient_center": [0.5, 0.5],
  "gradient_stops": [
    {"color": "#ff0000", "position": 0.0},
    {"color": "#0000ff", "position": 1.0}
  ],
  "opacity": 1.0
}
```

### 插槽配置

- `box`: `[x, y, width, height]` - 位置和大小（像素）
- `radius`: 圆角半径（像素），0 表示无圆角
- `fit`: `"cover"` 或 `"contain"`
  - `cover`: 填充整个区域，可能裁剪
  - `contain`: 完整显示，可能有空白
- `padding`: 内边距（像素）
- `align_x`: 水平对齐方式（`"left"` / `"center"` / `"right"`），默认 `"center"`
  - 在 `cover` 模式下，控制裁剪的起始位置
  - 在 `contain` 模式下，控制图片在插槽中的水平位置
- `align_y`: 垂直对齐方式（`"top"` / `"center"` / `"bottom"`），默认 `"center"`
  - 在 `cover` 模式下，控制裁剪的起始位置
  - 在 `contain` 模式下，控制图片在插槽中的垂直位置
- `rotation`: 旋转角度（度），默认 `0`
  - **正角度 = 顺时针**
  - 旋转的是**整个插槽图层**（包含 padding + 圆角）
- `rotate_x`: 绕 X 轴旋转角度（度），默认 `0`
- `rotate_y`: 绕 Y 轴旋转角度（度），默认 `0`
  - `rotate_x/rotate_y/rotation(rotate_z)` 会触发 3D 投影渲染（使用固定相机距离产生透视效果）
  - 渲染时会按变换后的四边形计算实际包围盒并扩展输出图层，**不会被原始 `box` 裁剪**；`box.x/y` 仍作为定位锚点
  - 斜边已做抗锯齿优化：编辑器预览使用超采样绘制，导出渲染对 warp 做超采样后再缩小

> 注意：模板不支持 `perspective` 字段（已移除），透视效果使用内部固定参数（对模板作者透明）。

### 文本样式

- `font`: 字体文件路径（`.ttf` 或 `.otf`），`null` 使用系统默认字体
- `size`: 字体大小（像素）
- `color`: 颜色（十六进制，如 `"#111111"`）
- `align`: 对齐方式（`"left"` / `"center"` / `"right"`）
- `max_width`: 最大宽度（像素），`null` 使用 `box` 的宽度
- `line_spacing`: 行间距倍数（默认 1.2）
- `stroke_width`: 描边宽度（像素），0 表示无描边
- `stroke_fill`: 描边颜色（十六进制）
- `shadow`: 阴影配置
  - `offset`: `[x, y]` - 阴影偏移（像素）
  - `color`: 阴影颜色（支持透明度，如 `"#00000088"`）
  - `blur`: 模糊半径（像素）

## 常见问题

### Q: 如何添加自定义字体？

A: 在模板编辑器中，选择文本块，点击 "Pick" 按钮选择字体文件（`.ttf` 或 `.otf`），或在模板 JSON 的 `style.font` 字段中指定字体文件路径。

### Q: 支持哪些图片格式？

A: 支持 PNG、JPG、JPEG、WebP 格式。

### Q: 如何调整图片在插槽中的显示方式？

A: 在插槽配置中设置 `fit` 字段：
- `"cover"`: 填充整个区域（推荐用于截图）
- `"contain"`: 完整显示图片（可能有空白）

### Q: 如何控制图片在插槽中的对齐方式？

A: 使用 `align_x` 和 `align_y` 字段控制图片对齐：

**水平对齐 (`align_x`)**：
- `"left"`: 图片靠左对齐
- `"center"`: 图片居中（默认）
- `"right"`: 图片靠右对齐

**垂直对齐 (`align_y`)**：
- `"top"`: 图片靠上对齐
- `"center"`: 图片居中（默认）
- `"bottom"`: 图片靠下对齐

**对齐效果**：
- 在 `cover` 模式下：对齐方式控制裁剪的起始位置
  - 例如 `align_x: "left"` 会保留图片左侧内容，裁剪右侧
- 在 `contain` 模式下：对齐方式控制图片在插槽中的位置
  - 例如 `align_y: "top"` 会将图片放在插槽顶部，下方留白

在模板编辑器中，选择插槽后可以在右侧面板的 "Slot" 区域设置对齐方式。

### Q: CSV 批量生成时，如何指定多个图片？

A: 使用多个 `slot.<slotKey>` 列分别指定，例如：

```csv
template_key,output_name,slot.main,slot.overlay
left-right-green,case-001.png,/path/to/main.png,/path/to/overlay.png
```

### Q: 如何创建渐变背景？

A: 在模板编辑器中：
1. 选择背景类型为 "Gradient"
2. 选择渐变类型（Linear 或 Radial）
3. 设置渐变角度（Linear）或中心点（Radial）
4. 编辑渐变色标（JSON 格式）

注意：
- 渐变色标 `gradient_stops[].color` **仅支持 `#RRGGBB`**（不支持 `#RRGGBBAA` 这种 8 位带透明度写法）
- 透明度请使用 `background.opacity` 控制（会作用于整张渐变层）

### Q: 文本换行如何处理？

A: 当前版本的自动换行是**按空白分词**（空格/制表符/换行等都会被当作分隔符）后再根据 `max_width` 或 `box` 宽度进行换行：
- 对英文/有空格的文本效果较好
- 对中文（无空格）通常不会自动断行；建议适当插入空格、缩短文本、调大 `box`，或拆成多个 TextBlock
- 由于按空白分词，输入中的手动换行（`\n`）会被当成分隔符，**不会保留为强制换行**

### Q: 如何导出高质量图片？

A: 当前版本固定输出 PNG 格式。可以通过调整模板的 `size` 来生成更高分辨率的图片。

### Q: 模板文件保存在哪里？

A: 模板文件保存在 `app/templates/` 目录下，每个模板一个 JSON 文件，文件名为 `{key}.json`。

### Q: 批量/导出生成的图片保存在哪里？

A: 保存到主界面顶部的 **Output Dir** 指定目录（默认是项目根目录的 `output/`）。`app/assets/` 目录不会自动写入。

### Q: 如何调试渲染问题？

A: 查看应用底部的日志窗口，错误信息会显示在那里。也可以使用预览功能先查看效果。

## 开发说明

### 扩展功能

如需扩展功能，可以：

1. **添加新的背景类型**：在 `render.py` 的 `apply_background()` 函数中添加处理逻辑
2. **添加新的文本样式**：在 `models.py` 的 `TextStyle` 类中添加字段，在 `render.py` 的 `draw_text_block()` 中实现
3. **添加新的插槽效果**：在 `render.py` 的 `place_slot()` 函数中添加变换逻辑

### 代码规范

- 使用类型提示（Type Hints）
- 遵循 PEP 8 代码风格
- 使用 dataclass 定义数据模型
- 函数文档字符串说明参数和返回值

## 许可证

本项目为内部工具，仅供团队使用。

## 更新日志

### v1.1.0
- **新增**：插槽对齐功能
  - 支持水平和垂直对齐方式（`align_x` / `align_y`）
  - 在 `cover` 模式下控制裁剪位置
  - 在 `contain` 模式下控制图片位置
  - 模板编辑器 UI 支持对齐方式设置

### v1.0.0
- 初始版本
- 支持模板化封面生成
- 可视化模板编辑器
- CSV 批量处理
- 多种背景类型（颜色、图片、渐变）
- 文本样式支持（字体、颜色、对齐、阴影）

---

**维护者**: 开发团队  
**最后更新**: 2024

