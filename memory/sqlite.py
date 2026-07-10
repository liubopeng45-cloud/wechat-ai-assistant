"""记忆模块 —— SQLite 持久化实现

把对话历史存储在 SQLite 数据库文件中，特点：
  + 服务重启后数据不丢失
  + 零额外依赖（Python 内置 sqlite3）
  + 数据库级别的并发安全
  + 适合单机部署的生产环境

用法：
    from memory.sqlite import SQLiteMemory

    memory = SQLiteMemory(max_turns=10, db_path="data/conversations.db")
    history = memory.get_history("user_openid")

设计说明：
    使用 SQLite 的 Write-Ahead Logging (WAL) 模式提高并发性能。
    max_turns 滑动窗口策略保留最近 N 轮对话，防止消息列表超出模型 token 限制。
"""

import sqlite3
import os
import threading
import time
from memory.base import Memory


class SQLiteMemory(Memory):
    """基于 SQLite 的对话记忆持久化实现

    属性:
        db_path:    SQLite 数据库文件路径
        max_turns:  保留的最大对话轮数（每轮=user1条+AI1条）
        _lock:      线程锁，防止并发写操作
    """

    def __init__(self, max_turns: int = 10, db_path: str = None):
        """初始化 SQLite 记忆存储

        入参:
            max_turns: 最多保留多少轮对话（int），默认 10
            db_path:   数据库文件路径（str），默认 data/conversations.db
                      路径相对于项目根目录，或提供绝对路径
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data', 'conversations.db',
            )
        self.db_path = db_path
        self.max_turns = max_turns
        self._lock = threading.Lock()

        # 确保 data 目录存在
        if db_path != ":memory:" and db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化数据库表
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """创建并返回数据库连接

        每次调用创建新连接（sqlite3 连接不是线程安全的）。
        启用 WAL 模式提高并发性能。
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """创建 conversations 表（如果不存在）

        表结构:
            id:         自增主键
            user_id:    用户 OpenID（索引字段）
            role:       消息角色（user 或 assistant）
            content:    消息文本内容
            created_at: 消息创建时间（Unix 时间戳）
        """
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_time
                ON conversations (user_id, created_at DESC)
            """)
            conn.commit()
        finally:
            conn.close()

    def get_history(self, user_id: str) -> list[dict]:
        """获取用户的历史对话消息

        从数据库查询最近 N 条消息，按时间正序排列。

        入参:
            user_id: 用户的唯一标识（微信 OpenID）

        返回:
            list[dict] — 消息列表，按时间正序
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT role, content FROM conversations
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, self.max_turns * 2))

            # 查询结果是逆序的（最新的在最前），需要反转
            rows = cursor.fetchall()
            messages = [{"role": r["role"], "content": r["content"]} for r in rows]
            messages.reverse()
            return messages
        finally:
            conn.close()

    def add_message(self, user_id: str, role: str, content: str):
        """向用户的对话历史中添加一条新消息

        使用线程锁保证并发安全。添加后清理超出 max_turns 的旧消息。

        入参:
            user_id: 用户 OpenID
            role:    角色（"user" 或 "assistant"）
            content: 消息文本
        """
        with self._lock:
            conn = self._get_conn()
            try:
                # 插入新消息
                conn.execute("""
                    INSERT INTO conversations (user_id, role, content, created_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, role, content, time.time()))

                # 清理超出 max_turns 的旧消息
                # 先查出最新的 max_turns*2 条消息的最早时间戳
                cursor = conn.execute("""
                    SELECT created_at FROM conversations
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1 OFFSET ?
                """, (user_id, self.max_turns * 2 - 1))

                row = cursor.fetchone()
                if row is not None:
                    # 删除比这个时间戳更早的消息
                    conn.execute("""
                        DELETE FROM conversations
                        WHERE user_id = ? AND created_at < ?
                    """, (user_id, row["created_at"]))

                conn.commit()
            finally:
                conn.close()

    def clear(self, user_id: str):
        """清除某个用户的所有对话历史

        入参:
            user_id: 要清除的用户 OpenID
        """
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM conversations WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()

    @property
    def stats(self) -> dict:
        """获取记忆存储的统计信息

        返回:
            dict — 包含 total_users 和 total_messages
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT user_id) as users,
                       COUNT(*) as total
                FROM conversations
            """)
            row = cursor.fetchone()
            return {
                "total_users": row["users"],
                "total_messages": row["total"],
            }
        finally:
            conn.close()
