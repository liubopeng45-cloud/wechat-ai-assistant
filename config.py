"""
配置文件

从 .env 文件和环境变量中读取所有配置项。
python-dotenv 负责加载 .env 文件中的变量到 os.environ。

用法：
    import config
    print(config.WECHAT_TOKEN)
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件（如果存在），将里面的 KEY=VALUE 注入 os.environ
# .env 已在 .gitignore 中排除，不会提交到仓库
load_dotenv()


# ---- 微信服务器配置 ----

# 微信服务器验证用的 Token，在公众号后台设置
# 类型: str, 默认值: 'wechat_ai_token_2026'
WECHAT_TOKEN = os.environ.get('WECHAT_TOKEN', 'wechat_ai_token_2026')

# Flask 服务器监听端口
# 类型: int, 默认值: 8888
PORT = int(os.environ.get('PORT', 8888))

# 是否开启 Flask 调试模式（开发时建议开启）
# 类型: bool, 默认值: True
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'


# ---- DeepSeek AI 配置 ----

# DeepSeek API 密钥，从 https://platform.deepseek.com 获取
# 类型: str
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# DeepSeek API 地址（兼容 OpenAI 协议）
# 换成下面任一项即可切换模型商：
#   https://api.openai.com/v1      (OpenAI)
#   http://localhost:11434/v1      (本地 Ollama)
# 类型: str
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# 使用的模型名
# DeepSeek: deepseek-chat
# Ollama:   deepseek-r1:8b, qwen2.5:7b 等
# 类型: str
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')


# ---- 微信公众平台 API 配置 ----

# 测试号 AppID：https://mp.weixin.qq.com/debug/cgi-bin/sandbox
# 正式号 AppID：设置与开发 -> 基本配置
# 类型: str
WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID', '')

# 测试号 AppSecret（页面直接展示）
# 正式号 AppSecret（生成后保存，丢失需重置）
# 类型: str
WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET', '')
