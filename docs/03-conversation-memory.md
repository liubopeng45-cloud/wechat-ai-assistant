# Phase 3：对话记忆——让 AI 记住上下文

## 做了什么

新增 `memory/` 模块，按用户（微信 OpenID）存储对话历史，每次调用 AI 时注入历史消息。

当前项目结构：
```
D:\work\wechat-ai-assistant\
├── app.py           ← 改：文本消息注入历史 + 保存记忆
├── ai/
│   └── client.py    ← 未改（天然支持 messages 传历史）
├── memory/          ← 新增：对话记忆模块
│   ├── __init__.py
│   ├── base.py      ← 记忆接口，方便后续替换为 Redis/SQLite
│   └── memory.py    ← 内存实现，重启丢失
└── docs/
    ├── 01-setup.md
    ├── 02-ai-integration.md
    └── 03-conversation-memory.md
```

## 原理：Chat Completion 的消息列表

大模型的对话本质是一次性传入**整个消息列表**，AI 根据列表理解上下文：

```python
# 第 1 轮：传入当前消息
messages = [
    {"role": "system", "content": "你是一个客服..."},
    {"role": "user", "content": "我喜欢吃火锅"},
]

# 第 2 轮：传入历史 + 新消息
messages = [
    {"role": "system", "content": "你是一个客服..."},
    {"role": "user", "content": "我喜欢吃火锅"},
    {"role": "assistant", "content": "火锅是中国传统美食..."},
    {"role": "user", "content": "我刚才说我喜欢吃什么？"},  ← 新消息
]
# AI 看到历史，知道你在说火锅
```

## 代码改动详解

### 1. 记忆模块结构

```
Memory (抽象接口)          ← 定义 get_history / add_message / clear
  └── InMemoryMemory      ← 具体实现：字典存储 + 滑动窗口
```

`InMemoryMemory` 的核心逻辑：

```python
def add_message(self, user_id, role, content):
    # 按用户分组存储
    self._storage[user_id].append({"role": role, "content": content})

    # 滑动窗口：最多保留 10 轮 = 20 条消息
    if len(self._storage[user_id]) > 20:
        self._storage[user_id] = self._storage[user_id][-20:]
```

### 2. app.py 的改动

```python
# 之前：每次对话独立
messages = [system, user]

# 之后：注入历史
history = memory.get_history(user_id)       # 读取历史
messages = [system] + history + [user]      # 拼入完整消息列表
ai_reply = ai_client.chat(messages)
memory.add_message(user_id, "user", msg)     # 保存用户消息
memory.add_message(user_id, "assistant", reply)  # 保存 AI 回复
```

## 局限与后续

当前用的是**内存存储**，有两个明显缺点：

| 问题 | 表现 | 后续方案 |
|------|------|----------|
| 重启丢失 | 服务重启后所有对话历史清零 | Phase 6：换 Redis / SQLite |
| 单机限制 | 部署多台服务器时记忆不同步 | Phase 6：换 Redis / 数据库 |

但对于学习和开发阶段，内存存储足够用了。

## 验证方式

配好 DeepSeek API Key 后，启动服务，用微信发送：

```
你：我喜欢吃火锅
AI：火锅是中国的传统美食，尤其在冬天很受欢迎...

你：我刚才说了什么？     ← AI 应该记得
AI：您刚才说您喜欢吃火锅。
```

## 下一步（Phase 4）

突破 5 秒超时限制。目前如果 AI 回复较慢（超过 5 秒），微信会显示「该公众号暂时无法提供服务」。

Phase 4 会引入**异步回复**机制：先同步返回「正在思考...」，再用微信客服消息 API 推送 AI 的完整回复。
