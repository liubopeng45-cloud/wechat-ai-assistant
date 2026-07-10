"""测试：速率限制器"""

import time
from utils.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter 基本功能"""

    def test_allow_first_request(self):
        """第一个请求应被允许"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.allow("user_1") is True

    def test_allow_within_limit(self):
        """在限制范围内的请求应被允许"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.allow("user_1") is True
        assert limiter.allow("user_1") is True
        assert limiter.allow("user_1") is True

    def test_reject_when_over_limit(self):
        """超过限制的请求应被拒绝"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.allow("user_1") is True
        assert limiter.allow("user_1") is True
        assert limiter.allow("user_1") is False

    def test_users_isolated(self):
        """不同用户的限制互不影响"""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.allow("user_a") is True
        assert limiter.allow("user_a") is False
        assert limiter.allow("user_b") is True

    def test_remaining_count(self):
        """remaining() 返回剩余可用请求数"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.remaining("user_1") == 5
        limiter.allow("user_1")
        assert limiter.remaining("user_1") == 4
        limiter.allow("user_1")
        assert limiter.remaining("user_1") == 3

    def test_window_expiry(self):
        """窗口过期后请求应被重新允许"""
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)
        assert limiter.allow("user_1") is True
        assert limiter.allow("user_1") is False
        time.sleep(0.15)
        assert limiter.allow("user_1") is True
