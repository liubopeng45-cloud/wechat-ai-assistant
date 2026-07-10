# Phase 2：接入 DeepSeek AI 智能回复

## 改动概览

把「你说的是：xxx」回显，替换为 DeepSeek AI 的真实回答。

当前项目文件：
```
D:\work\wechat-ai-assistant\
├── app.py           ← 改：文本消息改为调用 AI
├── config.py        ← 改：加 AI 配置项
├── .env             ← 改：加 API Key 占位符
├── ai/              ← 新增：AI 客户端模块
│   ├── __init__.py
│   └── client.py    ← DeepSeek API 封装
└── requirements.txt ← 改：加 openai 包
```

## 你需要做的

### 1. 获取 DeepSeek API Key

1. 打开 https://platform.deepseek.com，注册账号
2. 登录后进入 API Keys 页面
3. 创建一个新的 API Key，复制
4. 打开项目中的 `.env` 文件，把 `sk-your-api-key-here` 替换为你的真实 Key

```ini
# .env 修改后
DEEPSEEK_API_KEY=sk-这里放你复制的那一串
```

### 2. 重启服务

修改 `.env` 后需要重启服务才能生效：

```bash
cd D:\work\wechat-ai-assistant
venv\Scripts\python run.py
```

### 3. 测试

用微信给测试号发消息，应该收到 AI 的真正的回复了。

也可以本地模拟发消息：

```bash
venv\Scripts\python test_wechat.py
```

会看到返回内容变成 AI 生成的文本（如果没有配 API Key 会返回错误提示）。

## 核心概念

### Chat Completion API

大模型的对话接口本质上是一个「消息列表 → 回复」的映射：

```
输入：
  [
    {"role": "system",    "content": "你是一个客服助手"},
    {"role": "user",      "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮你？"},
    {"role": "user",      "content": "什么是 Python？"},
  ]

输出：
  {"role": "assistant", "content": "Python 是一种编程语言..."}
```

三种角色：
| 角色 | 作用 |
|------|------|
| `system` | 设定 AI 的人格和回答规则 |
| `user` | 用户的消息 |
| `assistant` | AI 的回复（历史对话中保存的） |

### DeepSeek vs OpenAI

DeepSeek 的 API 和 OpenAI 完全兼容，所以可以用 OpenAI 的 Python SDK 来调用，只需改 `base_url`：

```
OpenAI:   https://api.openai.com/v1
DeepSeek: https://api.deepseek.com
```

这意味着将来你想换回 OpenAI 或其他兼容 API，只需改 `.env` 里的 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_API_KEY`。

### System Prompt

在 `ai/client.py` 里有 `SYSTEM_PROMPT` 常量，你可以自由修改来改变机器人的性格和回答风格。这是目前的设计：

```python
SYSTEM_PROMPT = """你是一个专业的 AI 客服助手，目前正在学习阶段。
你的职责是回答用户的各种问题，展现专业、耐心、友好的态度。

回答原则：
1. 保持简洁明了，避免过于冗长
2. 用中文回答
3. 如果遇到不知道的问题，坦诚说明
4. 涉及技术问题时，尽量给出具体的示例或代码"""
```

修改后重启服务即可生效。

## 代码数据流

```
用户发消息 "Python是什么？"
  → 微信服务器 POST XML 到 /wechat
  → wechatpy 解析 XML → msg.content = "Python是什么？"
  → ai_client.chat([
      {"role": "system", "content": SYSTEM_PROMPT},
      {"role": "user", "content": "Python是什么？"},
    ])
  → DeepSeek API 返回 "Python 是一种..."
  → TextReply(content="Python 是一种...") 组装 XML
  → 返回给微信服务器
  → 用户看到 AI 回复
```

## 下一步（Phase 3）

加入对话记忆，让 AI 记得上下文。比如你问完「Python 是什么」后问「它难学吗」，AI 应该知道你在说 Python。

Phase 3 会引入用户会话管理 + 消息历史存储。
