"""测试：对话记忆模块"""

from memory import InMemoryMemory
from memory.base import Memory
import os
import tempfile
from memory.sqlite import SQLiteMemory


def _make_sqlite():
    """创建临时文件 SQLiteMemory 实例"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return SQLiteMemory(max_turns=10, db_path=tmp.name), tmp.name


# ======================== InMemoryMemory 测试 ========================

class TestInMemoryMemory:
    def test_implements_interface(self):
        memory = InMemoryMemory()
        assert isinstance(memory, Memory)

    def test_get_history_empty(self):
        memory = InMemoryMemory()
        assert memory.get_history("user_1") == []

    def test_add_and_get_message(self):
        memory = InMemoryMemory()
        memory.add_message("user_1", "user", "你好")
        history = memory.get_history("user_1")
        assert len(history) == 1
        assert history[0] == {"role": "user", "content": "你好"}

    def test_multiple_users_isolated(self):
        memory = InMemoryMemory()
        memory.add_message("user_a", "user", "A的消息")
        memory.add_message("user_b", "user", "B的消息")
        assert len(memory.get_history("user_a")) == 1
        assert len(memory.get_history("user_b")) == 1
        assert memory.get_history("user_a")[0]["content"] == "A的消息"
        assert memory.get_history("user_b")[0]["content"] == "B的消息"

    def test_clear_history(self):
        memory = InMemoryMemory()
        memory.add_message("user_1", "user", "你好")
        memory.clear("user_1")
        assert memory.get_history("user_1") == []

    def test_get_history_returns_copy(self):
        memory = InMemoryMemory()
        memory.add_message("user_1", "user", "你好")
        history = memory.get_history("user_1")
        history.append({"role": "assistant", "content": "注入"})
        assert len(memory.get_history("user_1")) == 1


class TestSlidingWindow:
    def test_sliding_window_trims_old_messages(self):
        memory = InMemoryMemory(max_turns=2)
        for i in range(5):
            memory.add_message("user_1", "user", f"消息{i}")
            memory.add_message("user_1", "assistant", f"回复{i}")
        history = memory.get_history("user_1")
        assert len(history) == 4
        assert history[0]["content"] == "消息3"


class TestStats:
    def test_stats_empty(self):
        memory = InMemoryMemory()
        stats = memory.stats
        assert stats["total_users"] == 0
        assert stats["total_messages"] == 0

    def test_stats_with_data(self):
        memory = InMemoryMemory()
        memory.add_message("u1", "user", "你好")
        memory.add_message("u1", "assistant", "嗨")
        memory.add_message("u2", "user", "在吗")
        stats = memory.stats
        assert stats["total_users"] == 2
        assert stats["total_messages"] == 3


# ======================== SQLiteMemory 测试 ========================

class TestSQLiteMemory:
    def test_implements_interface(self):
        mem, path = _make_sqlite()
        assert isinstance(mem, Memory)
        os.unlink(path)

    def test_get_history_empty(self):
        mem, path = _make_sqlite()
        assert mem.get_history("user_1") == []
        os.unlink(path)

    def test_add_and_get_message(self):
        mem, path = _make_sqlite()
        mem.add_message("user_1", "user", "你好")
        history = mem.get_history("user_1")
        assert len(history) == 1
        assert history[0] == {"role": "user", "content": "你好"}
        os.unlink(path)

    def test_multiple_users_isolated(self):
        mem, path = _make_sqlite()
        mem.add_message("user_a", "user", "A的消息")
        mem.add_message("user_b", "user", "B的消息")
        assert len(mem.get_history("user_a")) == 1
        assert len(mem.get_history("user_b")) == 1
        assert mem.get_history("user_a")[0]["content"] == "A的消息"
        os.unlink(path)

    def test_clear_history(self):
        mem, path = _make_sqlite()
        mem.add_message("user_1", "user", "你好")
        mem.clear("user_1")
        assert mem.get_history("user_1") == []
        os.unlink(path)

    def test_sliding_window(self):
        mem, path = _make_sqlite()
        mem.max_turns = 2
        for i in range(5):
            mem.add_message("user_1", "user", f"消息{i}")
            mem.add_message("user_1", "assistant", f"回复{i}")
        history = mem.get_history("user_1")
        assert len(history) == 4
        assert history[0]["content"] == "消息3"
        os.unlink(path)

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "test.db")
            mem = SQLiteMemory(max_turns=10, db_path=db_path)
            mem.add_message("user_1", "user", "你好")
            mem.add_message("user_1", "assistant", "嗨")
            del mem
            mem2 = SQLiteMemory(max_turns=10, db_path=db_path)
            history = mem2.get_history("user_1")
            assert len(history) == 2
            assert history[0] == {"role": "user", "content": "你好"}
            assert history[1] == {"role": "assistant", "content": "嗨"}
