"""
OCR JSON结果转Markdown转换器
支持有道智云OCR API返回的JSON格式转换为Markdown文档
"""

import json
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class TextDirection(Enum):
    """文本方向枚举"""
    HORIZONTAL = 'h'  # 水平
    VERTICAL = 'v'    # 垂直


@dataclass
class BoundingBox:
    """边界框信息"""
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_string(cls, bbox_str: str) -> 'BoundingBox':
        """从字符串解析边界框信息"""
        try:
            # 格式: "x,y,width,height"
            parts = bbox_str.split(',')
            if len(parts) == 4:
                return cls(
                    x=int(parts[0]),
                    y=int(parts[1]),
                    width=int(parts[2]),
                    height=int(parts[3])
                )
        except (ValueError, IndexError):
            pass
        return cls(0, 0, 0, 0)


@dataclass
class Word:
    """单词信息"""
    word: str
    boundingBox: BoundingBox

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Word':
        return cls(
            word=data.get('word', ''),
            boundingBox=BoundingBox.from_string(data.get('boundingBox', '0,0,0,0'))
        )


@dataclass
class Line:
    """行信息"""
    text: str
    words: List[Word]
    boundingBox: BoundingBox

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Line':
        words = [Word.from_dict(word_data) for word_data in data.get('words', [])]
        return cls(
            text=data.get('text', ''),
            words=words,
            boundingBox=BoundingBox.from_string(data.get('boundingBox', '0,0,0,0'))
        )


@dataclass
class Region:
    """区域信息"""
    lang: str
    dir: str
    lines: List[Line]
    boundingBox: BoundingBox

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Region':
        lines = [Line.from_dict(line_data) for line_data in data.get('lines', [])]
        return cls(
            lang=data.get('lang', ''),
            dir=data.get('dir', 'h'),
            lines=lines,
            boundingBox=BoundingBox.from_string(data.get('boundingBox', '0,0,0,0'))
        )


class OCRToMarkdownConverter:
    """OCR JSON结果转Markdown转换器"""

    def __init__(self):
        self.title_patterns = [
            r'^第[一二三四五六七八九十\d]+[章节篇]',
            r'^[一二三四五六七八九十\d]+[、\.]',
            r'^[A-Z][A-Z\s]*$',  # 全大写英文标题
            r'^[A-Z][a-z\s]+$',  # 首字母大写英文标题
        ]
        self.subtitle_patterns = [
            r'^[一二三四五六七八九十\d]+[、\.]',
            r'^[A-Z][a-z\s]+$',
        ]

    def is_title(self, text: str) -> bool:
        """判断是否为标题"""
        text = text.strip()
        if len(text) < 2 or len(text) > 50:
            return False

        for pattern in self.title_patterns:
            if re.match(pattern, text):
                return True
        return False

    def is_subtitle(self, text: str) -> bool:
        """判断是否为副标题"""
        text = text.strip()
        if len(text) < 2 or len(text) > 30:
            return False

        for pattern in self.subtitle_patterns:
            if re.match(pattern, text):
                return True
        return False

    def is_list_item(self, text: str) -> bool:
        """判断是否为列表项"""
        text = text.strip()
        list_patterns = [
            r'^[•·▪▫◦‣⁃]\s*',
            r'^[\d]+[\.\)]\s*',
            r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*',
            r'^[a-z][\.\)]\s*',
            r'^[A-Z][\.\)]\s*',
        ]

        for pattern in list_patterns:
            if re.match(pattern, text):
                return True
        return False

    def is_emphasis(self, text: str) -> bool:
        """判断是否为强调文本（粗体）"""
        # 检查是否包含特殊格式标记或全大写
        if text.isupper() and len(text) > 1:
            return True
        # 检查是否包含书名号、引号等
        if re.search(r'[《》""''【】]', text):
            return True
        return False

    def format_text(self, text: str) -> str:
        """格式化文本"""
        text = text.strip()
        if not text:
            return ""

        # 处理强调文本
        if self.is_emphasis(text):
            return f"**{text}**"

        return text

    def convert_regions_to_markdown(self, regions: List[Region]) -> str:
        """将区域列表转换为Markdown"""
        markdown_lines = []
        current_list_level = 0

        # 按垂直位置排序区域
        sorted_regions = sorted(regions, key=lambda r: r.boundingBox.y)

        for region in sorted_regions:
            # 处理垂直文本
            if region.dir == TextDirection.VERTICAL.value:
                markdown_lines.extend(self._process_vertical_text(region))
            else:
                markdown_lines.extend(self._process_horizontal_text(region))

        # 后处理：合并连续的列表项
        markdown_lines = self._merge_list_items(markdown_lines)

        return '\n'.join(markdown_lines)

    def _process_horizontal_text(self, region: Region) -> List[str]:
        """处理水平文本"""
        lines = []

        # 按垂直位置排序行
        sorted_lines = sorted(region.lines, key=lambda l: l.boundingBox.y)

        for line in sorted_lines:
            text = line.text.strip()
            if not text:
                continue

            # 判断文本类型并格式化
            if self.is_title(text):
                lines.append(f"# {text}")
            elif self.is_subtitle(text):
                lines.append(f"## {text}")
            elif self.is_list_item(text):
                lines.append(f"- {text}")
            else:
                formatted_text = self.format_text(text)
                if formatted_text:
                    lines.append(formatted_text)

        return lines

    def _process_vertical_text(self, region: Region) -> List[str]:
        """处理垂直文本"""
        lines = []

        # 按水平位置排序行（垂直文本）
        sorted_lines = sorted(region.lines, key=lambda l: l.boundingBox.x)

        for line in sorted_lines:
            text = line.text.strip()
            if not text:
                continue

            # 垂直文本通常作为引用或特殊格式处理
            formatted_text = self.format_text(text)
            if formatted_text:
                lines.append(f"> {formatted_text}")

        return lines

    def _merge_list_items(self, lines: List[str]) -> List[str]:
        """合并连续的列表项"""
        if not lines:
            return lines

        merged_lines = []
        i = 0

        while i < len(lines):
            current_line = lines[i]

            # 检查是否为列表项
            if current_line.startswith('- '):
                # 收集连续的列表项
                list_items = [current_line[2:]]  # 去掉 "- " 前缀
                i += 1

                # 查找连续的列表项
                while i < len(lines) and lines[i].startswith('- '):
                    list_items.append(lines[i][2:])
                    i += 1

                # 合并列表项
                if len(list_items) > 1:
                    merged_lines.append('- ' + '\n- '.join(list_items))
                else:
                    merged_lines.append(current_line)
            else:
                merged_lines.append(current_line)
                i += 1

        return merged_lines

    def convert_json_to_markdown(self, json_data: Dict[str, Any]) -> str:
        """将OCR JSON结果转换为Markdown"""
        try:
            # 解析JSON数据
            if 'Result' not in json_data:
                raise ValueError("JSON数据中缺少'Result'字段")

            result = json_data['Result']
            regions_data = result.get('regions', [])

            # 转换为Region对象
            regions = [Region.from_dict(region_data) for region_data in regions_data]

            # 转换为Markdown
            markdown_content = self.convert_regions_to_markdown(regions)

            return markdown_content

        except Exception as e:
            return f"转换失败: {str(e)}"


def demo_usage():
    """演示用法"""
    # 示例JSON数据（根据有道OCR API返回格式）
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
                            "text": "第一章 引言",
                            "boundingBox": "10,10,200,30",
                            "words": [
                                {"word": "第", "boundingBox": "10,10,20,30"},
                                {"word": "一", "boundingBox": "20,10,30,30"},
                                {"word": "章", "boundingBox": "30,10,40,30"},
                                {"word": "引", "boundingBox": "50,10,60,30"},
                                {"word": "言", "boundingBox": "60,10,70,30"}
                            ]
                        }
                    ]
                },
                {
                    "lang": "zh-CHS",
                    "dir": "h",
                    "boundingBox": "10,50,300,80",
                    "lines": [
                        {
                            "text": "这是一个示例文档，用于演示OCR转Markdown的功能。",
                            "boundingBox": "10,50,300,80",
                            "words": [
                                {"word": "这", "boundingBox": "10,50,20,80"},
                                {"word": "是", "boundingBox": "20,50,30,80"},
                                # ... 更多单词
                            ]
                        }
                    ]
                }
            ]
        }
    }

    # 创建转换器
    converter = OCRToMarkdownConverter()

    # 转换为Markdown
    markdown_content = converter.convert_json_to_markdown(sample_json)

    print("转换结果:")
    print(markdown_content)


if __name__ == "__main__":
    demo_usage()