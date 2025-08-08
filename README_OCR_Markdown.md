# OCR转Markdown工具使用说明

## 概述

本工具基于有道智云OCR API，将图片中的文字识别结果转换为结构化的Markdown文档。支持多种文档元素的智能识别和格式化。

## 功能特性

### 基础功能
- ✅ 文字识别和提取
- ✅ 标题和副标题识别
- ✅ 列表项识别
- ✅ 强调文本识别
- ✅ 垂直文本处理

### 高级功能
- ✅ 表格结构识别
- ✅ 代码块识别
- ✅ 引用文本识别
- ✅ 多语言支持
- ✅ 位置信息保留

## 文件结构

```
youdaoocr/
├── OcrDemo.py              # 主程序，集成OCR和Markdown转换
├── ocr_to_markdown.py      # 基础OCR转Markdown转换器
├── advanced_ocr_converter.py # 高级转换器，支持复杂文档结构
├── utils/
│   └── AuthV3Util.py       # 有道API认证工具
└── README_OCR_Markdown.md  # 本说明文档
```

## 使用方法

### 1. 基础使用

```python
from ocr_to_markdown import OCRToMarkdownConverter

# 创建转换器
converter = OCRToMarkdownConverter()

# 转换JSON结果
markdown_content = converter.convert_json_to_markdown(json_data)
```

### 2. 高级使用

```python
from advanced_ocr_converter import AdvancedOCRConverter

# 创建高级转换器
converter = AdvancedOCRConverter()

# 转换JSON结果（支持表格、代码块等）
markdown_content = converter.convert_json_to_markdown_advanced(json_data)
```

### 3. 完整流程

```bash
# 运行OCR识别并转换为Markdown
python OcrDemo.py
```

## 算法原理

### 1. 文本分类算法

#### 标题识别
- 正则表达式匹配：`^第[一二三四五六七八九十\d]+[章节篇]`
- 数字编号：`^[一二三四五六七八九十\d]+[、\.]`
- 英文标题：`^[A-Z][A-Z\s]*$` 或 `^[A-Z][a-z\s]+$`

#### 列表项识别
- 项目符号：`^[•·▪▫◦‣⁃]\s*`
- 数字编号：`^[\d]+[\.\)]\s*`
- 中文编号：`^[①②③④⑤⑥⑦⑧⑨⑩]\s*`
- 字母编号：`^[a-z][\.\)]\s*` 或 `^[A-Z][\.\)]\s*`

#### 强调文本识别
- 全大写文本
- 包含特殊符号：`[《》""''【】]`

### 2. 位置排序算法

```python
# 按垂直位置排序
sorted_regions = sorted(regions, key=lambda r: r.boundingBox.y)
sorted_lines = sorted(region.lines, key=lambda l: l.boundingBox.y)
```

### 3. 表格识别算法

1. **表格行检测**：查找包含分隔符或符合表格模式的行
2. **单元格分割**：按空格或制表符分割文本
3. **表格构建**：根据行列位置构建表格结构
4. **Markdown生成**：转换为标准Markdown表格格式

### 4. 代码块识别算法

- 关键字匹配：`function`, `def`, `class`, `import` 等
- 语法模式：变量定义、函数调用等
- 缩进检测：识别代码块的缩进结构

## 支持的文档结构

### 1. 标题层级
```markdown
# 一级标题
## 二级标题
### 三级标题
```

### 2. 列表
```markdown
- 无序列表项
1. 有序列表项
• 项目符号列表
```

### 3. 表格
```markdown
| 列1 | 列2 | 列3 |
| --- | --- | --- |
| 数据1 | 数据2 | 数据3 |
```

### 4. 代码块
```markdown
```python
def hello_world():
    print("Hello, World!")
```
```

### 5. 引用
```markdown
> 这是引用文本
```

### 6. 强调
```markdown
**粗体文本**
*斜体文本*
```

## 配置参数

### OCR API参数
```python
lang_type = 'zh-CHS'        # 语言类型
detect_type = '10012'       # 识别类型（按行识别）
angle = '0'                 # 角度识别
column = 'onecolumn'        # 列识别模式
rotate = 'donot_rotate'     # 旋转处理
```

### 转换器参数
```python
# 标题识别模式
title_patterns = [
    r'^第[一二三四五六七八九十\d]+[章节篇]',
    r'^[一二三四五六七八九十\d]+[、\.]',
    r'^[A-Z][A-Z\s]*$',
    r'^[A-Z][a-z\s]+$',
]

# 列表识别模式
list_patterns = [
    r'^[•·▪▫◦‣⁃]\s*',
    r'^[\d]+[\.\)]\s*',
    r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*',
]
```

## 输出示例

### 输入图片
包含以下内容的图片：
- 标题：第一章 引言
- 正文：这是一个示例文档
- 列表：1. 第一项 2. 第二项
- 表格：包含数据的表格

### 输出Markdown
```markdown
# 第一章 引言

这是一个示例文档，用于演示OCR转Markdown的功能。

1. 第一项
2. 第二项

| 列1 | 列2 | 列3 |
| --- | --- | --- |
| 数据1 | 数据2 | 数据3 |
```

## 错误处理

### 常见错误及解决方案

1. **API认证失败**
   - 检查APP_KEY和APP_SECRET是否正确
   - 确认IP地址是否在白名单中

2. **图片格式不支持**
   - 确保图片为JPG、PNG等常见格式
   - 检查图片大小是否在限制范围内

3. **转换结果不准确**
   - 调整识别参数（angle、column等）
   - 优化图片质量
   - 使用高级转换器

## 性能优化

### 1. 批量处理
```python
import os
from pathlib import Path

def batch_convert(image_dir: str):
    """批量转换图片"""
    image_files = Path(image_dir).glob("*.jpg")
    for image_file in image_files:
        # 处理单个文件
        process_single_image(image_file)
```

### 2. 缓存机制
```python
import json
import hashlib

def get_cache_key(image_path: str) -> str:
    """生成缓存键"""
    with open(image_path, 'rb') as f:
        content = f.read()
    return hashlib.md5(content).hexdigest()

def load_cached_result(cache_key: str) -> Optional[Dict]:
    """加载缓存结果"""
    cache_file = f"cache/{cache_key}.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None
```

## 扩展开发

### 1. 自定义识别规则
```python
class CustomOCRConverter(OCRToMarkdownConverter):
    def __init__(self):
        super().__init__()
        # 添加自定义模式
        self.custom_patterns = [
            r'^自定义模式',
        ]

    def is_custom_element(self, text: str) -> bool:
        """自定义元素识别"""
        for pattern in self.custom_patterns:
            if re.match(pattern, text):
                return True
        return False
```

### 2. 输出格式扩展
```python
def export_to_html(markdown_content: str) -> str:
    """导出为HTML格式"""
    import markdown
    return markdown.markdown(markdown_content)

def export_to_latex(markdown_content: str) -> str:
    """导出为LaTeX格式"""
    # 实现Markdown到LaTeX的转换
    pass
```

## 最佳实践

### 1. 图片预处理
- 确保图片清晰度足够
- 调整对比度和亮度
- 去除背景干扰

### 2. 参数调优
- 根据文档类型选择合适的识别参数
- 对于表格文档，使用`column='columns'`
- 对于多语言文档，设置正确的`lang_type`

### 3. 结果验证
- 检查转换结果的准确性
- 手动调整不正确的识别结果
- 保存原始JSON数据以备参考

## 技术支持

如有问题，请参考：
- [有道智云OCR API文档](https://ai.youdao.com/DOCSIRMA/html/ocr/api/tyocr/index.html)
- 项目GitHub仓库
- 技术交流群：654064748

## 更新日志

### v1.0.0 (2024-01-01)
- 基础OCR转Markdown功能
- 支持标题、列表、强调文本识别

### v1.1.0 (2024-01-15)
- 添加表格识别功能
- 支持代码块和引用识别
- 优化位置排序算法

### v1.2.0 (2024-02-01)
- 高级转换器支持复杂文档结构
- 添加批量处理功能
- 性能优化和错误处理改进