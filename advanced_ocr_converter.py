"""
高级OCR转Markdown转换器
支持更复杂的文档结构识别，包括表格、代码块、引用等
"""

import json
import re
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from ocr_to_markdown import OCRToMarkdownConverter, Region, Line, Word, BoundingBox


class DocumentElement(Enum):
    """文档元素类型"""
    TITLE = "title"
    SUBTITLE = "subtitle"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    QUOTE = "quote"
    EMPHASIS = "emphasis"
    HEADER = "header"


@dataclass
class TableCell:
    """表格单元格"""
    content: str
    row: int
    col: int
    boundingBox: BoundingBox


@dataclass
class Table:
    """表格结构"""
    cells: List[TableCell]
    rows: int
    cols: int

    def to_markdown(self) -> str:
        """转换为Markdown表格格式"""
        if not self.cells:
            return ""

        # 按行列排序单元格
        sorted_cells = sorted(self.cells, key=lambda c: (c.row, c.col))

        # 构建表格数据
        table_data = {}
        for cell in sorted_cells:
            if cell.row not in table_data:
                table_data[cell.row] = {}
            table_data[cell.row][cell.col] = cell.content

        # 生成Markdown表格
        markdown_lines = []

        # 表头
        if 0 in table_data:
            header_row = []
            for col in range(self.cols):
                header_row.append(table_data[0].get(col, ""))
            markdown_lines.append("| " + " | ".join(header_row) + " |")
            markdown_lines.append("| " + " | ".join(["---"] * self.cols) + " |")

        # 数据行
        for row in range(1, self.rows):
            if row in table_data:
                data_row = []
                for col in range(self.cols):
                    data_row.append(table_data[row].get(col, ""))
                markdown_lines.append("| " + " | ".join(data_row) + " |")

        return "\n".join(markdown_lines)


class AdvancedOCRConverter(OCRToMarkdownConverter):
    """高级OCR转换器"""

    def __init__(self):
        super().__init__()
        self.table_patterns = [
            r'^\|.*\|$',  # 包含竖线的行
            r'^[A-Z][A-Z\s]+$',  # 全大写表头
        ]
        self.code_patterns = [
            r'^```',
            r'^[a-zA-Z_][a-zA-Z0-9_]*\s*[=:]\s*',  # 变量定义
            r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(',  # 函数调用
        ]
        self.quote_patterns = [
            r'^["""''].*["""'']$',  # 引号包围
            r'^>.*',  # 引用符号
        ]

    def detect_table_structure(self, regions: List[Region]) -> List[Table]:
        """检测表格结构"""
        tables = []

        for region in regions:
            if region.dir == 'h':  # 只处理水平文本
                # 查找可能的表格行
                table_lines = []
                for line in region.lines:
                    if self._is_table_row(line.text):
                        table_lines.append(line)

                if len(table_lines) >= 2:  # 至少需要2行才能构成表格
                    table = self._build_table_from_lines(table_lines)
                    if table:
                        tables.append(table)

        return tables

    def _is_table_row(self, text: str) -> bool:
        """判断是否为表格行"""
        text = text.strip()

        # 检查是否包含分隔符
        if '|' in text or '\t' in text:
            return True

        # 检查是否符合表格模式
        for pattern in self.table_patterns:
            if re.match(pattern, text):
                return True

        return False

    def _build_table_from_lines(self, lines: List[Line]) -> Optional[Table]:
        """从行构建表格"""
        cells = []
        max_row = 0
        max_col = 0

        for row_idx, line in enumerate(lines):
            # 简单的表格解析：按空格或制表符分割
            parts = re.split(r'\s{2,}|\t', line.text.strip())

            for col_idx, part in enumerate(parts):
                if part.strip():
                    cell = TableCell(
                        content=part.strip(),
                        row=row_idx,
                        col=col_idx,
                        boundingBox=line.boundingBox
                    )
                    cells.append(cell)
                    max_row = max(max_row, row_idx)
                    max_col = max(max_col, col_idx)

        if cells:
            return Table(cells=cells, rows=max_row + 1, cols=max_col + 1)
        return None

    def detect_code_blocks(self, regions: List[Region]) -> List[Tuple[int, int]]:
        """检测代码块位置"""
        code_blocks = []

        for region in regions:
            for line in region.lines:
                if self._is_code_line(line.text):
                    # 记录代码块的行范围
                    start_line = line.boundingBox.y
                    end_line = start_line + line.boundingBox.height
                    code_blocks.append((start_line, end_line))

        return code_blocks

    def _is_code_line(self, text: str) -> bool:
        """判断是否为代码行"""
        text = text.strip()

        for pattern in self.code_patterns:
            if re.match(pattern, text):
                return True

        # 检查是否包含编程语言特征
        code_indicators = [
            'function', 'var', 'let', 'const', 'if', 'for', 'while',
            'def', 'class', 'import', 'from', 'return', 'print',
            'public', 'private', 'static', 'void', 'int', 'string'
        ]

        for indicator in code_indicators:
            if indicator in text.lower():
                return True

        return False

    def detect_quotes(self, regions: List[Region]) -> List[Tuple[int, int]]:
        """检测引用位置"""
        quotes = []

        for region in regions:
            for line in region.lines:
                if self._is_quote_line(line.text):
                    start_line = line.boundingBox.y
                    end_line = start_line + line.boundingBox.height
                    quotes.append((start_line, end_line))

        return quotes

    def _is_quote_line(self, text: str) -> bool:
        """判断是否为引用行"""
        text = text.strip()

        for pattern in self.quote_patterns:
            if re.match(pattern, text):
                return True

        return False

    def convert_json_to_markdown_advanced(self, json_data: Dict[str, Any]) -> str:
        """高级JSON转Markdown转换"""
        try:
            if 'Result' not in json_data:
                raise ValueError("JSON数据中缺少'Result'字段")

            result = json_data['Result']
            regions_data = result.get('regions', [])

            # 转换为Region对象
            regions = [Region.from_dict(region_data) for region_data in regions_data]

            # 检测特殊结构
            tables = self.detect_table_structure(regions)
            code_blocks = self.detect_code_blocks(regions)
            quotes = self.detect_quotes(regions)

            # 生成Markdown内容
            markdown_lines = []

            # 按垂直位置排序所有文本元素
            all_elements = []

            for region in regions:
                for line in region.lines:
                    element = {
                        'type': self._classify_element(line.text),
                        'text': line.text,
                        'y': line.boundingBox.y,
                        'region': region
                    }
                    all_elements.append(element)

            # 按位置排序
            all_elements.sort(key=lambda x: x['y'])

            # 处理表格
            table_positions = set()
            for table in tables:
                for cell in table.cells:
                    table_positions.add(cell.boundingBox.y)

            # 生成Markdown
            for element in all_elements:
                if element['y'] in table_positions:
                    # 跳过表格中的元素，表格会单独处理
                    continue

                markdown_line = self._format_element(element)
                if markdown_line:
                    markdown_lines.append(markdown_line)

            # 插入表格
            for table in tables:
                table_md = table.to_markdown()
                if table_md:
                    markdown_lines.append(table_md)
                    markdown_lines.append("")  # 空行分隔

            return '\n'.join(markdown_lines)

        except Exception as e:
            return f"转换失败: {str(e)}"

    def _classify_element(self, text: str) -> DocumentElement:
        """分类文档元素"""
        text = text.strip()

        if self.is_title(text):
            return DocumentElement.TITLE
        elif self.is_subtitle(text):
            return DocumentElement.SUBTITLE
        elif self.is_list_item(text):
            return DocumentElement.LIST_ITEM
        elif self._is_code_line(text):
            return DocumentElement.CODE_BLOCK
        elif self._is_quote_line(text):
            return DocumentElement.QUOTE
        elif self.is_emphasis(text):
            return DocumentElement.EMPHASIS
        else:
            return DocumentElement.PARAGRAPH

    def _format_element(self, element: Dict[str, Any]) -> str:
        """格式化文档元素"""
        text = element['text'].strip()
        element_type = element['type']

        if not text:
            return ""

        if element_type == DocumentElement.TITLE:
            return f"# {text}"
        elif element_type == DocumentElement.SUBTITLE:
            return f"## {text}"
        elif element_type == DocumentElement.LIST_ITEM:
            return f"- {text}"
        elif element_type == DocumentElement.CODE_BLOCK:
            return f"```\n{text}\n```"
        elif element_type == DocumentElement.QUOTE:
            return f"> {text}"
        elif element_type == DocumentElement.EMPHASIS:
            return f"**{text}**"
        else:
            return text


def demo_advanced_converter():
    """演示高级转换器"""
    # 示例JSON数据
    sample_json = {
        "errorCode": "0",
        "Result": {
            "orientation": "0",
            "regions": [
                {
                    "lang": "zh-CHS",
                    "dir": "h",
                    "boundingBox": "10,10,200,30",
                    "lines": [
                        {
                            "text": "第一章 编程基础",
                            "boundingBox": "10,10,200,30",
                            "words": []
                        }
                    ]
                },
                {
                    "lang": "zh-CHS",
                    "dir": "h",
                    "boundingBox": "10,50,300,80",
                    "lines": [
                        {
                            "text": "Python是一种高级编程语言",
                            "boundingBox": "10,50,300,80",
                            "words": []
                        }
                    ]
                },
                {
                    "lang": "zh-CHS",
                    "dir": "h",
                    "boundingBox": "10,90,400,120",
                    "lines": [
                        {
                            "text": "def hello_world():",
                            "boundingBox": "10,90,400,120",
                            "words": []
                        }
                    ]
                },
                {
                    "lang": "zh-CHS",
                    "dir": "h",
                    "boundingBox": "10,130,400,160",
                    "lines": [
                        {
                            "text": '    print("Hello, World!")',
                            "boundingBox": "10,130,400,160",
                            "words": []
                        }
                    ]
                }
            ]
        }
    }

    # 创建高级转换器
    converter = AdvancedOCRConverter()

    # 转换为Markdown
    markdown_content = converter.convert_json_to_markdown_advanced(sample_json)

    print("高级转换结果:")
    print(markdown_content)


if __name__ == "__main__":
    demo_advanced_converter()