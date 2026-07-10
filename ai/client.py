"""AI 模块

提供统一的 AI 对话客户端接口。
目前通过 DeepSeek API 实现，但设计上支持无缝切换：
  - 改 base_url 就能换到 OpenAI、本地 Ollama 等兼容 API
  - 改 model 名就能换不同的模型

用法：
    from ai import DeepSeekClient, SYSTEM_PROMPT

    client = DeepSeekClient(api_key="sk-xxx")
    reply = client.chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "你好"},
    ])
"""

from openai import OpenAI
from openai import (
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APIStatusError,
)
import time
import logging

logger = logging.getLogger(__name__)


# ---- 核心提示词（System Prompt） ----

SYSTEM_PROMPT = """你是一个专业的 AI 客服助手，目前正在学习阶段。
你的职责是回答用户的各种问题，展现专业、耐心、友好的态度。

回答原则：
1. 保持简洁明了，避免过于冗长
2. 用中文回答
3. 如果遇到不知道的问题，坦诚说明
4. 涉及技术问题时，尽量给出具体的示例或代码"""


class DeepSeekClient:
    """DeepSeek AI 对话客户端

    封装 OpenAI 兼容的 Chat Completion API 调用。
    使用 DeepSeek 时只需改 base_url，接口与 OpenAI 完全一致。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 30,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.model = model

    def chat(self, messages: list, max_tokens: int = 2000) -> str:
        """发送对话消息，获取 AI 回复

        入参:
            messages: 消息列表（list of dict），格式同 OpenAI API
            max_tokens: AI 回复最大长度（int），默认 2000

        返回:
            str — AI 的回复文本，或带 [] 的错误提示（保证不抛异常）

        重试策略：
            - APITimeoutError, RateLimitError, APIConnectionError → 指数退避重试（1s/2s/4s/8s）
            - 5xx 服务端错误 → 同上重试
            - 4xx 客户端错误 / AuthenticationError → 不重试，直接返回错误
        """
        retry_delays = [1, 2, 4, 8]

        for attempt in range(len(retry_delays) + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                return response.choices[0].message.content

            except APITimeoutError:
                logger.warning(f'AI API 超时（第{attempt+1}次）')
                if attempt < len(retry_delays):
                    time.sleep(retry_delays[attempt])
                    continue
                return '[AI 回复超时，请稍后重试]'

            except RateLimitError:
                logger.warning(f'AI API 频率限制（第{attempt+1}次）')
                if attempt < len(retry_delays):
                    time.sleep(retry_delays[attempt])
                    continue
                return '[AI 服务繁忙，请稍后重试]'

            except APIConnectionError:
                logger.warning(f'AI API 连接失败（第{attempt+1}次）')
                if attempt < len(retry_delays):
                    time.sleep(retry_delays[attempt])
                    continue
                return '[AI 服务连接失败，请稍后重试]'

            except AuthenticationError:
                logger.error('AI API 认证失败，请检查 API Key')
                return '[AI 服务配置异常，请联系管理员]'

            except APIStatusError as e:
                if e.status_code >= 500:
                    logger.warning(f'AI API 服务错误 {e.status_code}（第{attempt+1}次）')
                    if attempt < len(retry_delays):
                        time.sleep(retry_delays[attempt])
                        continue
                    return f'[AI 服务暂时异常（{e.status_code}），请稍后重试]'
                logger.error(f'AI API 请求错误 {e.status_code}: {e.message}')
                return '[AI 请求参数错误，请联系管理员]'

            except Exception as e:
                logger.error(f'AI API 未知错误: {e}', exc_info=True)
                return '[AI 服务异常，请稍后重试]'
