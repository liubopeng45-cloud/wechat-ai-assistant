"""测试：AI 客户端模块"""

from unittest.mock import MagicMock, patch

import pytest

from ai import DeepSeekClient, SYSTEM_PROMPT


class TestSystemPrompt:
    """系统提示词基本验证"""

    def test_system_prompt_is_string(self):
        """SYSTEM_PROMPT 为非空字符串"""
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_chinese(self):
        """系统提示词包含中文"""
        assert any('\u4e00' <= c <= '\u9fff' for c in SYSTEM_PROMPT)


class TestDeepSeekClientInit:
    """DeepSeekClient 初始化测试"""

    def test_init_defaults(self):
        """默认参数初始化"""
        client = DeepSeekClient(api_key='sk-test')
        assert client.model == 'deepseek-chat'
        assert client.client.base_url == 'https://api.deepseek.com'

    def test_init_custom_values(self):
        """自定义参数初始化"""
        client = DeepSeekClient(
            api_key='sk-custom',
            base_url='https://example.com/v1',
            model='gpt-4',
            timeout=60,
        )
        assert client.model == 'gpt-4'
        assert 'example.com' in str(client.client.base_url)


class TestDeepSeekClientChat:
    """chat() 方法测试（mock OpenAI API）"""

    @patch('ai.client.OpenAI')
    def test_chat_success(self, mock_openai):
        """正常对话返回 AI 回复文本"""
        # 构造 mock 响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '你好，有什么可以帮你？'
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = DeepSeekClient(api_key='sk-test')
        reply = client.chat([{'role': 'user', 'content': '你好'}])

        assert reply == '你好，有什么可以帮你？'

    @patch('ai.client.OpenAI')
    def test_chat_api_timeout_retry_success(self, mock_openai):
        """API 超时后重试，最终成功"""
        from openai import APITimeoutError

        mock_instance = mock_openai.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '重试成功'

        # 第一次超时，第二次成功
        mock_instance.chat.completions.create.side_effect = [
            APITimeoutError('timeout'),
            mock_response,
        ]

        client = DeepSeekClient(api_key='sk-test', timeout=5)
        reply = client.chat([{'role': 'user', 'content': '你好'}])

        assert reply == '重试成功'

    @patch('ai.client.OpenAI')
    def test_chat_auth_error(self, mock_openai):
        """认证错误直接返回错误消息，不重试"""
        from openai import AuthenticationError

        mock_instance = mock_openai.return_value
        mock_instance.chat.completions.create.side_effect = AuthenticationError(
            'auth failed', response=MagicMock(), body=None
        )

        client = DeepSeekClient(api_key='sk-bad-key')
        reply = client.chat([{'role': 'user', 'content': '你好'}])

        assert '配置异常' in reply

    @patch('ai.client.OpenAI')
    def test_chat_unknown_exception(self, mock_openai):
        """未知异常返回通用错误提示"""
        mock_instance = mock_openai.return_value
        mock_instance.chat.completions.create.side_effect = RuntimeError('unexpected')

        client = DeepSeekClient(api_key='sk-test')
        reply = client.chat([{'role': 'user', 'content': '你好'}])

        assert '服务异常' in reply
