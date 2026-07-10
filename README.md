# WeChat AI Assistant

微信公众号 AI 客服机器人，基于 Flask + DeepSeek API。

## 功能

- 微信服务器验证
- AI 智能回复（DeepSeek API）
- 对话上下文记忆（滑动窗口，10轮）
- 异步回复（突破 5 秒超时限制）

## 启动

```bash
cd wechat-ai-assistant
pip install -r requirements.txt
python app.py
```

## 配置

复制 `.env` 文件，填入：

- `DEEPSEEK_API_KEY` - DeepSeek API 密钥
- `WECHAT_APP_ID` - 微信 AppID
- `WECHAT_APP_SECRET` - 微信 AppSecret
