# Phase 1：搭建微信服务器验证与自动回复

## 目标

完成微信公众号服务器配置，实现：
- 微信服务器签名验证（GET `/wechat`）
- 关注自动回复
- 文本消息自动回复

## 项目结构

```
D:\work\wechat-ai-assistant\        # 项目代码
D:\wechat-ai-assistant_deps\        # 外部依赖（Python venv）
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `app.py` | Flask 主程序，处理微信验证和消息 |
| `config.py` | 配置项（Token、端口等） |
| `run.py` | 启动入口 |
| `.env` | 环境变量（已加入 .gitignore） |
| `test_wechat.py` | 本地测试脚本 |
| `.gitignore` | Git 忽略规则 |
| `venv/` | Python 虚拟环境（Junction 链接到 _deps 目录） |

## 启动步骤

### 1. 启动服务

```bash
cd D:\work\wechat-ai-assistant
venv\Scripts\python run.py
```

服务运行在 `http://0.0.0.0:8888`。

### 2. 本地测试（可选）

```bash
venv\Scripts\python test_wechat.py
```

### 3. 内网穿透（使用 ngrok）

微信服务器需要能够访问到你的电脑，使用 ngrok 把本地端口暴露到公网：

```bash
ngrok http 8888
```

记下 ngrok 给你的 URL，比如 `https://abc123.ngrok.io`。

### 4. 配置微信公众平台

#### 方案 A：使用微信测试号（推荐，无需注册公众号）

1. 打开 https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login
2. 用微信扫码登录
3. 在「接口配置信息」中填写：
   - **URL**: `https://你的ngrok地址/wechat`
   - **Token**: `wechat_ai_token_2026`（与 `.env` 文件一致）
4. 点击提交，如果显示「配置成功」就完成了
5. 在「测试号二维码」处，用手机微信扫码关注
6. 发消息测试

#### 方案 B：使用正式公众号

1. 登录微信公众平台 https://mp.weixin.qq.com
2. 设置与开发 → 服务器配置
3. 启用服务器配置，填写 URL 和 Token
4. 提交验证

## 验证结果

关注测试号后，会收到自动欢迎消息。
发送任何文本消息，会得到回显回复。

## 核心概念

### 微信服务器验证原理

微信为了防止别人伪造你的服务器，在配置 URL 时会做一次验证：

1. 微信发送 GET 请求，带 `signature`、`timestamp`、`nonce`、`echostr` 四个参数
2. 你的服务器用同样的 Token 计算签名：`SHA1(sort(token, timestamp, nonce))`
3. 如果计算结果与微信传来的 `signature` 一致，返回 `echostr` 完成验证

### 消息格式

微信使用 XML 格式传递消息：

```xml
<xml>
  <ToUserName><![CDATA[公众号ID]]></ToUserName>
  <FromUserName><![CDATA[用户OpenID]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[用户消息内容]]></Content>
</xml>
```

### 回复时效

微信要求 **5 秒内** 回复，否则用户会看到「该公众号暂时无法提供服务」。
这个限制在 Phase 4 会解决。

## 下一步（Phase 2）

接入 AI 大模型 API，让机器人说人话而不是回显。
