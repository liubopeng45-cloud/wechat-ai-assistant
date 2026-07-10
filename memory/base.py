"""
记忆模块 —— 抽象接口

定义对话记忆的通用接口。
任何记忆存储实现（内存、Redis、数据库等）都必须实现这三个方法。

为什么用抽象类？
  1. 明确契约：实现方知道必须实现哪些方法
  2. 可替换性：从内存切到 Redis 只改一行 import
  3. 可测试性：可以 Mock 接口来测试
"""

from abc import ABC, abstractmethod


class Memory(ABC):
    """对话记忆抽象基类

    所有记忆存储实现都必须继承这个类并实现三个抽象方法。
    """

    @abstractmethod
    def get_history(self, user_id: str) -> list:
        """获取某个用户的对话历史

        入参:
            user_id: 用户的唯一标识（微信 OpenID）

        返回:
            list of dict — 消息列表，格式与 AI API 兼容：
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！"},
            ]
            如果用户没有历史记录，返回空列表 []。
        """
        ...

    @abstractmethod
    def add_message(self, user_id: str, role: str, content: str):
        """向用户的对话历史中添加一条新消息

        入参:
            user_id: 用户的唯一标识（微信 OpenID）
            role:    消息角色（"user" 或 "assistant"）
            content: 消息文本内容
        """
        ...

    @abstractmethod
    def clear(self, user_id: str):
        """清除某个用户的所有对话历史

        入参:
            user_id: 用户的唯一标识（微信 OpenID）

        用途: 用户主动要求"重置对话"时调用。
        """
        ...
