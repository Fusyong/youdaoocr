"""
OCR JSON结果转Markdown转换器
支持有道智云OCR API返回的JSON格式转换为Markdown文档
"""

import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import os
import statistics
import time


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
        """从字符串解析边界框信息

        兼容两类格式：
        - "x,y,width,height"
        - "x1,y1,x2,y2,x3,y3,x4,y4"（四角点坐标，多边形）
        """
        try:
            parts = [p.strip() for p in bbox_str.split(',') if p.strip()]
            # 宽高格式
            if len(parts) == 4:
                x, y, w, h = map(int, parts)
                return cls(x=x, y=y, width=w, height=h)

            # 四点格式（取外接矩形）
            if len(parts) == 8:
                xs = list(map(int, [parts[0], parts[2], parts[4], parts[6]]))
                ys = list(map(int, [parts[1], parts[3], parts[5], parts[7]]))
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                return cls(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y)
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
    text_height: int = 0
    style: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Line':
        words = [Word.from_dict(word_data) for word_data in data.get('words', [])]
        return cls(
            text=data.get('text', ''),
            words=words,
            boundingBox=BoundingBox.from_string(data.get('boundingBox', '0,0,0,0')),
            text_height=int(data.get('text_height', 0) or 0),
            style=str(data.get('style', '') or '')
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


class OCRJsonToTextLine:
    """OCR JSON → 纯文本行（含版面空格/空行）转换器"""

    def __init__(self):
        # 常量持久化文件
        self.constants_file = 'ocr_layout_constants.json'
        # 同行判定阈值（占行距比例）
        self.same_line_threshold_ratio = 0.4

    # ====== 布局常量估计与持久化 ======
    def _contains_cjk(self, s: str) -> bool:
        """是否包含中日韩统一表意文字（用于估计正文汉字高度）"""
        for ch in s:
            code = ord(ch)
            if (
                0x4E00 <= code <= 0x9FFF or
                0x3400 <= code <= 0x4DBF or
                0x20000 <= code <= 0x2A6DF or
                0x2A700 <= code <= 0x2B73F or
                0x2B740 <= code <= 0x2B81F or
                0x2B820 <= code <= 0x2CEAF
            ):
                return True
        return False

    def _robust_median(self, values: List[float]) -> float:
        if not values:
            return 0.0
        try:
            return float(statistics.median(values))
        except statistics.StatisticsError:
            return float(values[0])

    def _load_constants(self) -> Dict[str, Any]:
        if not os.path.exists(self.constants_file):
            return {}
        try:
            with open(self.constants_file, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        except (OSError, json.JSONDecodeError, ValueError):
            return {}

    def _save_constants(self, constants: Dict[str, Any]) -> None:
        try:
            with open(self.constants_file, 'w', encoding='utf-8') as fp:
                json.dump(constants, fp, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def estimate_layout_constants(self, regions: List['Region']) -> Tuple[float, float, Dict[str, int]]:
        """遍历所有 box，估计正文汉字高度与行高倍数，并结合历史常量进行微调/回落

        返回: (char_height_px, line_height_multiplier, sample_counts)
        """
        char_heights: List[float] = []
        line_heights: List[float] = []

        # 收集样本
        for region in regions:
            for line in region.lines:
                # 行高样本优先用行 bbox，其次 text_height
                if line.boundingBox and line.boundingBox.height > 0:
                    line_heights.append(float(line.boundingBox.height))
                elif line.text_height:
                    line_heights.append(float(line.text_height))

                for w in line.words:
                    if not w or not w.word:
                        continue
                    if self._contains_cjk(w.word) and w.boundingBox and w.boundingBox.height > 0:
                        char_heights.append(float(w.boundingBox.height))

        current_char_height = self._robust_median(char_heights) if len(char_heights) >= 5 else 0.0
        current_line_height = self._robust_median(line_heights) if len(line_heights) >= 3 else 0.0

        # 计算倍数（以正文汉字高度为基准）
        current_multiplier = 0.0
        if current_char_height > 0 and current_line_height > 0:
            ratios = [lh / current_char_height for lh in line_heights if lh > 0]
            current_multiplier = self._robust_median(ratios)

        # 载入历史常量
        loaded = self._load_constants()
        prev_char_height = float(loaded.get('char_height', 0) or 0)
        prev_multiplier = float(loaded.get('line_height_multiplier', 0) or 0)
        prev_counts = loaded.get('sample_counts', {}) if isinstance(loaded.get('sample_counts', {}), dict) else {}
        prev_char_n = int(prev_counts.get('char', 0))
        prev_line_n = int(prev_counts.get('line', 0))

        # 样本量
        char_n = len(char_heights)
        line_n = len(line_heights)

        # 稀疏判定：字样本<5 或 行样本<3 则较少
        sparse_char = char_n < 5
        sparse_line = line_n < 3

        # 合成结果
        final_char_height = current_char_height
        final_multiplier = current_multiplier

        # 如果当前样本过少，回落历史；否则按样本量加权微调
        if prev_char_height > 0:
            if sparse_char or current_char_height <= 0:
                final_char_height = prev_char_height
            else:
                alpha_char = min(0.7, char_n / float(char_n + prev_char_n + 1e-6))
                final_char_height = alpha_char * current_char_height + (1 - alpha_char) * prev_char_height

        if prev_multiplier > 0:
            if sparse_line or current_multiplier <= 0:
                final_multiplier = prev_multiplier
            else:
                alpha_line = min(0.7, line_n / float(line_n + prev_line_n + 1e-6))
                final_multiplier = alpha_line * current_multiplier + (1 - alpha_line) * prev_multiplier

        # 如仍无有效数值，给出保守默认
        if final_char_height <= 0:
            final_char_height = 32.0  # 经验默认值
        if final_multiplier <= 0:
            final_multiplier = 1.5

        # 夹制行高倍数在合理区间（通常 1.2 ~ 2.0）
        final_multiplier = max(1.2, min(2.0, final_multiplier))

        # 更新计数，限制上限避免惯性过大
        new_char_n = min(1000, prev_char_n + char_n)
        new_line_n = min(1000, prev_line_n + line_n)

        # 持久化
        self._save_constants({
            'char_height': round(final_char_height, 2),
            'line_height_multiplier': round(final_multiplier, 3),
            'sample_counts': {'char': new_char_n, 'line': new_line_n},
            'updated_at': int(time.time())
        })

        return final_char_height, final_multiplier, {'char': char_n, 'line': line_n}

    def convert_regions_to_text_lines(self, regions: List[Region], char_height: float, line_multiplier: float) -> List[str]:
        """将区域列表转换为纯文本行（跨 region 同行合并、行首缩进与行间空行）"""
        text_lines: List[str] = []

        # 1) 处理水平文本：收集所有行分片
        fragments = self._collect_horizontal_fragments(regions)
        if fragments:
            line_spacing = max(1.0, char_height * line_multiplier)
            grouped = self._group_fragments_by_line(fragments, line_spacing, self.same_line_threshold_ratio)
            # 文字区域左边界（全局最小 x）
            base_left = min((f['x'] for f in fragments), default=0)
            # 合并每一行的分片，按像素间距 → 空格数（两个空格≈一个正文汉字高度）
            prev_row: Optional[List[Dict[str, Any]]] = None
            for row in grouped:
                # 行间距 → 空行
                if prev_row is not None:
                    blanks = self._compute_blank_lines_between(prev_row, row, line_spacing)
                    if blanks > 0:
                        text_lines.extend([''] * blanks)
                # 行首缩进：行头到文字区域左边界的距离以空格填充
                indent_spaces = self._compute_row_indent_spaces(row, base_left, char_height)
                joined = self._join_fragments_with_spacing(row, char_height)
                stripped = joined.strip()
                if not stripped:
                    continue
                text_lines.append((' ' * indent_spaces) + stripped)
                prev_row = row

        # 2) 垂直文本：保持原有处理，作为引用
        vertical_regions = [r for r in regions if r.dir == TextDirection.VERTICAL.value]
        if vertical_regions:
            vertical_regions = sorted(vertical_regions, key=lambda r: r.boundingBox.x)
            for region in vertical_regions:
                # 将垂直文本直接按普通文本输出（不加 markdown 引用符号）
                sorted_lines = sorted(region.lines, key=lambda l: l.boundingBox.x)
                for line in sorted_lines:
                    text = (line.text or '').strip()
                    if text:
                        text_lines.append(text)

        return text_lines

    def _compute_row_indent_spaces(self, row: List[Dict[str, Any]], base_left: int, char_height: float) -> int:
        """计算一行行头相对文字区域左边界的空格数（两个空格≈一个汉字高度）"""
        if not row:
            return 0
        if char_height <= 0:
            char_height = 32.0
        left_x = min(item['x'] for item in row)
        indent_px = max(0, left_x - int(base_left or 0))
        spaces = int(round((indent_px / char_height) * 2))
        return max(0, spaces)

    def _compute_blank_lines_between(self, prev_row: List[Dict[str, Any]], curr_row: List[Dict[str, Any]], line_spacing: float) -> int:
        """根据两行的垂直间距，折算为空行数量并返回。
        以上一行的下边界与下一行的上边界的像素差为基准：
        blanks = floor(gap_px / line_spacing)
        """
        if not prev_row or not curr_row or line_spacing <= 0:
            return 0
        prev_bottom = max(item['y'] + item['height'] for item in prev_row)
        curr_top = min(item['y'] for item in curr_row)
        gap_px = max(0.0, float(curr_top - prev_bottom))
        blanks = int(gap_px // line_spacing)
        return max(0, blanks)

    def _collect_horizontal_fragments(self, regions: List[Region]) -> List[Dict[str, Any]]:
        """从所有 region 收集水平文本分片（以行 bbox 为准）。
        返回的分片包含: text, x, y, width, height
        """
        fragments: List[Dict[str, Any]] = []
        for region in regions:
            if region.dir != TextDirection.HORIZONTAL.value:
                continue
            for line in region.lines:
                if not line or not line.text:
                    continue
                bbox = line.boundingBox or region.boundingBox
                if not bbox:
                    continue
                fragments.append({
                    'text': line.text.strip(),
                    'x': int(bbox.x),
                    'y': int(bbox.y),
                    'width': int(bbox.width),
                    'height': int(bbox.height),
                })
        return fragments

    def _group_fragments_by_line(self, fragments: List[Dict[str, Any]], line_spacing: float, ratio: float) -> List[List[Dict[str, Any]]]:
        """按 y 中心与行距的比例阈值聚类为同一行。"""
        if not fragments:
            return []
        # 以 y 中心排序，便于顺序聚类
        for frag in fragments:
            frag['y_mid'] = frag['y'] + frag['height'] / 2.0
        fragments.sort(key=lambda frag: frag['y_mid'])

        threshold = max(1.0, ratio * line_spacing)
        groups: List[List[Dict[str, Any]]] = []
        current_group: List[Dict[str, Any]] = []
        current_mid: Optional[float] = None

        for item in fragments:
            if current_group and current_mid is not None:
                if abs(item['y_mid'] - current_mid) <= threshold:
                    current_group.append(item)
                    # 更新组中心（滚动平均）
                    current_mid = (current_mid * (len(current_group) - 1) + item['y_mid']) / len(current_group)
                else:
                    # 关闭当前组
                    groups.append(sorted(current_group, key=lambda frag: frag['x']))
                    current_group = [item]
                    current_mid = item['y_mid']
            else:
                current_group = [item]
                current_mid = item['y_mid']

        if current_group:
            groups.append(sorted(current_group, key=lambda frag: frag['x']))

        return groups

    def _join_fragments_with_spacing(self, row: List[Dict[str, Any]], char_height: float) -> str:
        """按片段的左右间距，以“两个空格≈一个汉字高度”的换算插入空格"""
        if not row:
            return ''
        if char_height <= 0:
            char_height = 32.0
        parts: List[str] = []
        prev_right = None
        for frag in row:
            if prev_right is None:
                parts.append(frag['text'])
                prev_right = frag['x'] + frag['width']
                continue
            gap_px = max(0, frag['x'] - prev_right)
            # 两个空格折算为一个正文汉字高度
            spaces = int(round((gap_px / char_height) * 2))
            if spaces > 0:
                parts.append(' ' * spaces)
            parts.append(frag['text'])
            prev_right = frag['x'] + frag['width']
        return ''.join(parts)


    def convert_json_to_text(self, ocr_json: Dict[str, Any]) -> str:
        """将OCR JSON结果转换为纯文本（带空格/空行）"""
        try:
            # 解析JSON数据
            if 'Result' not in ocr_json:
                raise ValueError("JSON数据中缺少'Result'字段")

            result = ocr_json['Result']
            regions_data = result.get('regions', [])

            # 转换为Region对象
            regions = [Region.from_dict(region_data) for region_data in regions_data]

            # 估计布局常量
            char_h, line_mul, _ = self.estimate_layout_constants(regions)

            # 转换为纯文本行
            lines = self.convert_regions_to_text_lines(regions, char_h, line_mul)
            return '\n'.join(lines)

        except (KeyError, TypeError, ValueError) as e:
            return f"转换失败: {str(e)}"

if __name__ == "__main__":
    with open('o_ocr.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        tl_conv = OCRJsonToTextLine()
        text_with_layout = tl_conv.convert_json_to_text(json_data)
        with open('o_ocr.txt', 'w', encoding='utf-8') as f:
            f.write(text_with_layout)

    print(text_with_layout)