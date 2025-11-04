"""
健壮的JSON解析工具
支持多种解析策略和Pydantic验证
"""
import json
import re
from typing import Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from app.utils.logger import logger

T = TypeVar('T', bound=BaseModel)


class JSONParseError(Exception):
    """JSON解析错误"""
    pass


class RobustJSONParser:
    """健壮的JSON解析器"""

    @staticmethod
    def extract_json_from_text(text: str) -> Optional[str]:
        """
        从文本中提取JSON字符串

        支持多种场景：
        - 纯JSON
        - Markdown代码块中的JSON
        - 文本中嵌入的JSON

        Args:
            text: 输入文本

        Returns:
            提取的JSON字符串，未找到则返回None
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # 策略1: 尝试提取Markdown代码块中的JSON
        markdown_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        markdown_match = re.search(markdown_pattern, text)
        if markdown_match:
            logger.debug("从Markdown代码块中提取JSON")
            return markdown_match.group(1)

        # 策略2: 查找第一个完整的JSON对象
        brace_count = 0
        start_idx = text.find('{')

        if start_idx == -1:
            return None

        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    logger.debug(f"提取JSON对象: 位置 {start_idx}:{i+1}")
                    return text[start_idx:i+1]

        # 策略3: 使用简单的首尾定位（回退方案）
        end_idx = text.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            logger.debug("使用首尾定位提取JSON")
            return text[start_idx:end_idx]

        return None

    @staticmethod
    def fix_common_json_errors(json_str: str) -> str:
        """
        修复常见的JSON格式错误

        Args:
            json_str: JSON字符串

        Returns:
            修复后的JSON字符串
        """
        # 移除注释
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*[\s\S]*?\*/', '', json_str)

        # 修复单引号为双引号
        json_str = json_str.replace("'", '"')

        # 修复尾随逗号
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

        # 修复缺失的引号（简单情况）
        json_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)

        return json_str

    @classmethod
    def parse_with_validation(
        cls,
        text: str,
        model: Type[T],
        strict: bool = False
    ) -> T:
        """
        解析并验证JSON为Pydantic模型

        Args:
            text: 输入文本
            model: Pydantic模型类
            strict: 严格模式（不尝试修复错误）

        Returns:
            验证后的模型实例

        Raises:
            JSONParseError: 解析或验证失败
        """
        if not text or not text.strip():
            raise JSONParseError("输入文本为空")

        # 提取JSON字符串
        json_str = cls.extract_json_from_text(text)

        if not json_str:
            raise JSONParseError(f"无法从文本中提取JSON对象，文本长度: {len(text)}")

        # 尝试解析策略
        strategies = [
            ("标准解析", lambda s: json.loads(s)),
        ]

        if not strict:
            strategies.append(
                ("修复后解析", lambda s: json.loads(cls.fix_common_json_errors(s)))
            )

        last_error = None
        parsed_data = None

        for strategy_name, parse_func in strategies:
            try:
                logger.debug(f"尝试{strategy_name}")
                parsed_data = parse_func(json_str)
                logger.info(f"{strategy_name}成功")
                break
            except json.JSONDecodeError as e:
                last_error = e
                logger.debug(f"{strategy_name}失败: {e}")
                continue

        if parsed_data is None:
            error_context = json_str[:200] + '...' if len(json_str) > 200 else json_str
            raise JSONParseError(
                f"所有解析策略均失败。最后错误: {last_error}。"
                f"JSON片段: {error_context}"
            )

        # Pydantic验证
        try:
            return model(**parsed_data)
        except ValidationError as e:
            logger.error(f"Pydantic验证失败: {e}")
            raise JSONParseError(f"JSON验证失败: {e}")

    @classmethod
    def parse(
        cls,
        text: str,
        strict: bool = False,
        default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        解析JSON为字典（无验证）

        Args:
            text: 输入文本
            strict: 严格模式
            default: 解析失败时的默认值

        Returns:
            解析后的字典

        Raises:
            JSONParseError: 解析失败且未提供默认值
        """
        try:
            json_str = cls.extract_json_from_text(text)

            if not json_str:
                if default is not None:
                    logger.warning("未找到JSON，使用默认值")
                    return default
                raise JSONParseError("无法提取JSON对象")

            # 尝试标准解析
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                if not strict:
                    # 尝试修复后解析
                    fixed_json = cls.fix_common_json_errors(json_str)
                    return json.loads(fixed_json)
                raise

        except Exception as e:
            if default is not None:
                logger.warning(f"JSON解析失败，使用默认值: {e}")
                return default
            raise JSONParseError(f"JSON解析失败: {e}")


# 便捷函数
def parse_json_safely(
    text: str,
    default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    安全解析JSON（带默认值）

    Args:
        text: 输入文本
        default: 解析失败时的默认值

    Returns:
        解析后的字典
    """
    parser = RobustJSONParser()
    return parser.parse(text, default=default)


def parse_json_with_model(
    text: str,
    model: Type[T],
    strict: bool = False
) -> T:
    """
    解析并验证JSON为Pydantic模型

    Args:
        text: 输入文本
        model: Pydantic模型类
        strict: 严格模式

    Returns:
        验证后的模型实例
    """
    parser = RobustJSONParser()
    return parser.parse_with_validation(text, model, strict)
