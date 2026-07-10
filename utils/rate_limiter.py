"""速率限制器 —— 基于滑动窗口的 per-user 请求频率限制

用法：
    limiter = RateLimiter(max_requests=20, window_seconds=60)
    if limiter.allow("user_openid"):
        # 处理请求
    else:
        # 返回"请求过于频繁"
"""

import time
import threading


class RateLimiter:
    """基于滑动窗口的速率限制器

    每个用户维护一个时间戳列表，记录该用户在窗口内的请求时间。
    超过 max_requests 后，最新请求会被拒绝，直到旧请求移出窗口。

    属性:
        max_requests:   窗口内允许的最大请求数
        window_seconds: 滑动窗口大小（秒）
        _buckets:       {user_id: [timestamp, ...]}
        _lock:          线程锁
    """

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, user_id: str) -> bool:
        """检查当前请求是否允许通过

        流程：
          1. 获取当前时间戳
          2. 从用户的时间戳列表中移除窗口外的时间戳
          3. 如果列表长度 >= max_requests，拒绝
          4. 否则添加当前时间戳，允许

        入参:
            user_id: 用户的唯一标识

        返回:
            bool — True 允许通过，False 请求过频
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            if user_id not in self._buckets:
                self._buckets[user_id] = []

            # 清理窗口外的时间戳
            timestamps = self._buckets[user_id]
            self._buckets[user_id] = [t for t in timestamps if t > window_start]

            if len(self._buckets[user_id]) >= self.max_requests:
                return False

            self._buckets[user_id].append(now)
            return True

    def remaining(self, user_id: str) -> int:
        """查询用户当前窗口内剩余的可用请求数"""
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            timestamps = [t for t in self._buckets.get(user_id, []) if t > window_start]
            return max(0, self.max_requests - len(timestamps))
