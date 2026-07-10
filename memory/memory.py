"""
记忆模块 —— 内存实现

把对话历史存在 Python 字典里，特点：
  + 简单零依赖，无需安装 Redis 或数据库
  + 服务重启后数据丢失（仅适合开发阶段）
  - 加锁支持多线程，但多进程/分布式部署会冲突

使用滑动窗口策略，只保留最近 N 轮对话，防止消息列表
超过模型的 token 限制（太长会被截断或报错）。

后续替换为 Redis 时，实现 Memory 接口即可无缝切换。
"""

import threading
from memory.base import Memory


class InMemoryMemory(Memory):
    """基于内存的对话记忆

    用 Python 字典存储，key=用户 OpenID，value=消息列表。
    使用 threading.Lock 保证多线程并发安全。

    属性:
        _storage:   存储字典，{user_id: [msg1, msg2, ...]}
        _lock:      线程锁，防止并发读写导致数据错乱
        max_turns:  保留的最大对话轮数（每轮=user1条+AI1条）
    """

    def __init__(self, max_turns: int = 10):
        """初始化记忆存储

        入参:
            max_turns: 最多保留多少轮对话（int），默认 10。
              每轮对话包含用户消息和 AI 回复各 1 条。
              10 轮 = 20 条消息，大约占用 2000-3000 tokens。
              调大可以让 AI 记住更多历史，但会消耗更多 tokens。
        """
        self._storage: dict[str, list[dict]] = {}
        # 线程锁：所有公共方法都需先获取锁再操作 _storage
        # 防止两个用户同时发消息时发生数据竞争
        self._lock = threading.Lock()
        self.max_turns = max_turns

    def get_history(self, user_id: str) -> list[dict]:
        """获取用户的历史对话消息

        入参:
            user_id: 用户的唯一标识（微信 OpenID）

        实现逻辑:
            1. 获取线程锁，防止并发读取时数据被修改
            2. 从 _storage 中读取，不存在则返回空列表
            3. 返回列表的**副本**，避免调用方意外修改内部数据

        返回:
            list[dict] — 用户的历史消息列表
            如果用户没有历史，返回 []
        """
        with self._lock:
            # .get(user_id, []) : 如果用户不存在，返回空列表
            # list(...) : 复制一份返回，防止外部修改内部数据
            return list(self._storage.get(user_id, []))

    def add_message(self, user_id: str, role: str, content: str):
        """向用户的对话历史中添加一条新消息

        入参:
            user_id: 用户 OpenID，用作存储的 key
            role:    角色，必须为 "user" 或 "assistant"
            content: 消息文本

        实现逻辑:
            1. 获取线程锁
            2. 如果用户是新用户，先创建空列表
            3. 添加新消息
            4. 滑动窗口截断：超过 max_turns*2 条时删掉最早的

        滑动窗口算法:
            [msg1, msg2, msg3, ..., msg20]  ← 20 条（10 轮）
            [msg3, msg4, ..., msg20]         ← 新消息来时，掐掉前 2 条
            始终保留最近的 N 轮对话，避免消息列表无限增长。
        """
        with self._lock:
            # 如果是新用户，初始化空列表
            if user_id not in self._storage:
                self._storage[user_id] = []

            # 追加新消息
            self._storage[user_id].append({
                "role": role,
                "content": content,
            })

            # 滑动窗口截断：保留最近的 max_turns * 2 条消息
            # 每轮 = user 消息 + assistant 回复 = 2 条
            max_msgs = self.max_turns * 2
            if len(self._storage[user_id]) > max_msgs:
                # 只保留末尾的 max_msgs 条（删掉最早的）
                self._storage[user_id] = self._storage[user_id][-max_msgs:]

    def clear(self, user_id: str):
        """清除某个用户的所有对话历史

        入参:
            user_id: 要清除的用户 OpenID

        用途:
            当用户发送"重置对话"等指令时调用。
        """
        with self._lock:
            # dict.pop(key, None) : 如果存在则删除并返回值，不存在返回 None
            self._storage.pop(user_id, None)

    @property
    def stats(self) -> dict:
        """获取记忆存储的统计信息（调试用）

        返回:
            dict — 包含：
            - total_users: 有多少用户有对话记录
            - total_messages: 总共存储了多少条消息
        """
        with self._lock:
            return {
                "total_users": len(self._storage),
                "total_messages": sum(
                    len(msgs) for msgs in self._storage.values()
                ),
            }
