# Phase 4：异步回复——突破 5 秒超时限制

## 问题

微信限制服务器必须在 **5 秒内** 回复。如果 AI 处理时间超过 5 秒，用户会看到「该公众号暂时无法提供服务」。

## 方案

利用微信的 **客服消息接口** 做异步推送：

1. 用户发消息 → 服务器在 1 秒内返回「正在思考中，请稍候...」
2. 后台线程异步调用 DeepSeek API
3. AI 回复完成后，通过客服消息接口主动推送给用户

## 新增文件

| 文件 | 作用 |
|------|------|
| `wechat/api.py` | 微信 API 封装（access_token 管理 + 客服消息推送） |
| `wechat/__init__.py` | 导出 WeChatAPI 类 |

`app.py` **重构**：将文本处理逻辑拆分为 `_handle_text()`，支持两种模式自动切换。

## 两种模式

### 异步模式（推荐，永不超时）

需要配置 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`：

```
用户发消息 → 立即回复"正在思考..."（<1秒）
          → 后台调 AI（无时间限制）
          → 客服消息推送真正回复
```

### 同步模式（回退，有超时风险）

未配置 AppID/AppSecret 时自动使用：

```
用户发消息 → 直接调 AI → 返回回复（可能 >5 秒）
```

## 配置异步模式

### 1. 获取 AppID 和 AppSecret

**测试号**（推荐，无需注册公众号）：

1. 打开 https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login
2. 微信扫码登录
3. 页面顶部直接显示 **appID** 和 **appsecret**

**正式号**：

1. 登录微信公众平台 → 设置与开发 → 基本配置
2. 查看 AppID，生成 AppSecret

### 2. 配置 `.env`

修改 `D:\work\wechat-ai-assistant\.env`，填入：

```ini
WECHAT_APP_ID=wx123456789abcdef
WECHAT_APP_SECRET=your_app_secret_here
```

### 3. 验证

启动服务：

```bash
cd D:\work\wechat-ai-assistant
venv\Scripts\python app.py
```

控制台输出 `Async mode: ON` 表示异步模式已生效。

## 核心概念

### access_token

微信 API 的访问凭证：

- 有效期 **7200 秒**（2 小时）
- 获取 API：`GET /cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET`
- 代码中自动缓存，过期前 5 分钟刷新

### 客服消息 vs 被动回复

| 特性 | 被动回复 | 客服消息 |
|------|----------|----------|
| 时限 | 5 秒内 | 无限制 |
| 触发方式 | 用户消息触发 | 服务器主动推送 |
| 频率限制 | 无 | 免费订阅号每天 20 条 |
| API | 回复 XML | POST `/cgi-bin/message/custom/send` |

### 线程池

`ThreadPoolExecutor(max_workers=4)` 控制并发数：

- 同时最多 4 个 AI 请求在后台处理
- 超出队列的消息依次等待
- 对于学习阶段完全够用

## 验证方式

1. 配置 AppID/AppSecret
2. 启动服务
3. 用微信发送消息
4. 应该先收到「正在思考中，请稍候...」
5. 几秒后收到 AI 的真正回复

## 下一步（Phase 5+）

- 本地模型部署（Ollama + 本地 DeepSeek/Qwen）
- 知识库（RAG）
- Docker 化部署到 VPS
