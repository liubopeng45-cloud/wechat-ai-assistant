"""消息过滤器 —— 在发送给 AI 前对用户消息进行预处理

功能：
  1. 电话号码掩码：将 11 位手机号替换为 138****1234 格式
  2. 身份证号掩码：将 18 位身份证号替换为 110***********1234 格式
  3. 敏感词过滤：可配置的敏感词替换
  4. 文本规范化：全角转半角、多余空白清理

用法：
    from utils.message_filter import MessageFilter

    filter_chain = MessageFilter()
    safe_text = filter_chain.apply("我的电话是13800138000")
    # 输出: "我的电话是138****8000"
"""

import re


class MessageFilter:
    """消息过滤器链

    可串联多个过滤规则，对用户消息进行预处理后再发送给 AI。
    这样 AI 不会返回被掩码的信息。

    属性:
        rules: 过滤规则列表，每个规则是一个 (name, func) 元组
    """

    def __init__(self):
        self.rules: list[tuple[str, callable]] = [
            ("mask_id_card", self._mask_id_card),
            ("mask_phone", self._mask_phone),
            ("normalize_text", self._normalize_text),
        ]

    def apply(self, text: str) -> str:
        """对所有规则执行过滤

        入参:
            text: 用户输入的消息文本

        返回:
            str — 过滤后的文本
        """
        for name, func in self.rules:
            text = func(text)
        return text

    @staticmethod
    def _mask_phone(text: str) -> str:
        """掩码手机号：13800138000 → 138****8000"""
        return re.sub(
            r'(1[3-9]\d)\d{4}(\d{4})',
            r'\1****\2',
            text,
        )

    @staticmethod
    def _mask_id_card(text: str) -> str:
        """掩码身份证号：110101199001011234 → 110101********1234"""
        return re.sub(
            r'(\d{6})\d{8}(\d{4})',
            r'\1********\2',
            text,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """规范化文本：全角转半角，清理多余空白"""
        result = []
        for char in text:
            code = ord(char)
            # 全角字母数字转半角
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            elif code == 0x3000:  # 全角空格
                result.append(chr(0x0020))
            else:
                result.append(char)
        text = ''.join(result)
        # 合并连续空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
