"""
记忆模块

负责存储和管理用户与 AI 的对话历史。
按用户（微信 OpenID）隔离存储，每个用户有独立的对话上下文。

设计为接口 + 实现分离：
  Memory (抽象基类) —— 定义操作契约
  InMemoryMemory (实现) —— 当前使用内存字典存储

后续替换为 Redis/SQLite 时，只需实现 Memory 接口即可。
"""

from .base import Memory
from .memory import InMemoryMemory
from .sqlite import SQLiteMemory
