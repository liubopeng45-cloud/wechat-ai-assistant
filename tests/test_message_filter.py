"""测试：消息过滤器"""

from utils.message_filter import MessageFilter


class TestPhoneMask:
    """手机号掩码测试"""

    def test_mask_11_digit_phone(self):
        """11 位手机号被掩码为 138****8000 格式"""
        f = MessageFilter()
        result = f.apply("我的电话是13800138000")
        assert "138****8000" in result
        # 原始号不应存在
        assert "13800138000" not in result

    def test_no_false_positive_short_number(self):
        """非手机号的数字不应被错误掩码"""
        f = MessageFilter()
        result = f.apply("编号是12345")
        assert "12345" in result

    def test_multiple_phones(self):
        """多个手机号同时掩码"""
        f = MessageFilter()
        result = f.apply("号码A:13912345678, 号码B:13698765432")
        assert "139****5678" in result
        assert "136****5432" in result


class TestIdCardMask:
    """身份证号掩码测试"""

    def test_mask_18_digit_id(self):
        """18 位身份证号被掩码"""
        f = MessageFilter()
        result = f.apply("我的身份证是110101199001011234")
        assert "110101********1234" in result
        assert "110101199001011234" not in result


class TestTextNormalize:
    """文本规范化测试"""

    def test_fullwidth_to_halfwidth(self):
        """全角字母数字转半角"""
        f = MessageFilter()
        result = f.apply("ｔｅｓｔ１２３")
        assert "test123" in result

    def test_strip_extra_whitespace(self):
        """多余空白被清理"""
        f = MessageFilter()
        result = f.apply("  hello   world  ")
        assert result == "hello world"
