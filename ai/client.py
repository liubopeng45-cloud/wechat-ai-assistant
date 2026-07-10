"""
AI 模块

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


# ---- 系统提示词（System Prompt） ----
# AI 客服的"人格设定"，每次对话消息列表的第一条。
# 决定了 AI 的语气、角色边界、回答风格。
# 你可以自由修改来定制机器人的性格。
# 注意：修改后需要重启服务才能生效。

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

    属性:
        client: OpenAI SDK 客户端实例
        model:  使用的模型标识符
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 30,
    ):
        """初始化 AI 客户端

        入参:
            api_key:  API 密钥（str）
            base_url: API 服务地址（str），默认 DeepSeek
            model:    模型名（str），默认 deepseek-chat
            timeout:  API 请求超时秒数（int），默认 30 秒

        说明:
            timeout 参数防止 AI API 长时间无响应时服务卡死。
            如果 AI 回复超过 30 秒未返回，请求会抛出超时异常。
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.model = model

    def chat(self, messages: list, max_tokens: int = 2000) -> str:
        """发送对话消息，获取 AI 回复

        这是本模块的核心方法，所有 AI 对话都通过它完成。
        它接收消息列表（含系统提示词和历史），返回 AI 的文本回复。

        入参:
            messages: 消息列表（list of dict），格式：
                [
                    {"role": "system",   "content": "你是一个客服助手"},
                    {"role": "user",     "content": "你好"},
                    {"role": "assistant", "content": "你好！有什么可以帮你的？"},
                    {"role": "user",     "content": "什么是 Python？"},
                ]
                role 可选值：system（系统设定）, user（用户）, assistant（AI）
                content 是消息的文本内容。
            max_tokens: AI 回复最大长度（int），默认 2000。
                控制 AI 回复的字数上限。设为较小的值（如 500）
                可以让 AI 回复更简短。

        返回:
            str — AI 的回复文本。
            例如："你好！我是你的 AI 客服助手，有什么可以帮你的吗？"

        异常处理:
            任何 API 调用异常都会被捕获，返回包含错误信息的字符串。
            这样可以保证即使 API 出错了，用户也能看到友好的提示，
            而不是收到 500 错误或空白回复。
        """
        try:
            # 调用 OpenAI SDK 的 Chat Completion API
            # 这是标准的 LLM 对话接口
            response = self.client.chat.completions.create(
                model=self.model,          # 使用的模型名
                messages=messages,         # 消息列表（含历史）
                max_tokens=max_tokens,     # 回复长度上限
                temperature=0.7,           # 回答随机性（0~1），值越大越有创意
            )
            # 从 API 响应中提取 AI 的回复文本
            # response.choices[0] = 第一个（也是唯一一个）回复候选
            # .message.content = AI 回复的文本内容
            return response.choices[0].message.content

        except Exception as e:
            # 兜底：任何异常返回带 [] 的错误消息，不会让请求失败
            # 注意：这里不应该抛出异常，否则微信会收到 500
            return f"[AI 回复出错：{e}]"
