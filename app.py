"""
微信公众号 AI 客服 —— 主程序

整合四个 Phase 功能：
  Phase 1 — 微信服务器验证 + 消息解析
  Phase 2 — DeepSeek AI 智能回复
  Phase 3 — 对话上下文记忆
  Phase 4 — 异步回复（突破 5 秒超时）

请求处理流程概览：
  GET  /wechat  → 微信服务器验证（首次配置时调用）
  POST /wechat  → 处理用户消息
                   │
                   ├→ 文本消息 → _handle_text(msg)
                   │    ├→ 异步模式（配了 AppID）：立即返回"正在思考"，后台调 AI + 客服消息推送
                   │    └→ 同步模式（降级）：直接等 AI 回复后返回
                   │
                   ├→ 事件消息 → _handle_event(msg)
                   │    ├→ subscribe：关注欢迎语
                   │    └→ unsubscribe：取关日志
                   │
                   └→ 其他类型 → 暂不支持提示

启动方式：
  1. python run.py       # 通过入口文件启动
  2. python app.py       # 直接启动（推荐，会显示启动信息）
"""

import hashlib
from flask import Flask, request, make_response
from concurrent.futures import ThreadPoolExecutor

# wechatpy 处理微信消息的 XML 解析和回复生成
from wechatpy import parse_message          # 把微信的 XML 解析成 Python 对象
from wechatpy.replies import TextReply      # 组装文本回复的 XML

# 本项目的自定义模块
from ai import DeepSeekClient, SYSTEM_PROMPT    # AI 客户端和服务提示词
from memory import InMemoryMemory               # 对话记忆
from wechat import WeChatAPI                    # 微信 API（客服消息）

# ============================================================
# Flask 应用初始化
# ============================================================

# 创建 Flask 应用实例
# __name__ 是 Python 内置变量，值为 "__main__"（直接运行）或模块名（被导入）
app = Flask(__name__)

# 从 config.py（不带 .py 后缀）加载配置项
# Flask 会把 config.py 中的大写变量加载到 app.config 字典中
# 之后通过 app.config['WECHAT_TOKEN'] 等访问
app.config.from_object('config')

# ============================================================
# 全局组件初始化
# 这些对象在模块加载时创建一次，所有请求共享同一个实例
# ============================================================

# ---- 1. AI 客户端 ----
# 用于调用 DeepSeek API
# 参数从 app.config 读取（app.config 的值来自 config.py/.env）
# timeout=30：API 调用超过 30 秒未返回则超时
ai_client = DeepSeekClient(
    api_key=app.config['DEEPSEEK_API_KEY'],       # API 密钥
    base_url=app.config['DEEPSEEK_BASE_URL'],      # API 地址
    model=app.config['DEEPSEEK_MODEL'],             # 模型名
    timeout=30,                                     # 超时秒数
)

# ---- 2. 对话记忆 ----
# 按用户（微信 OpenID）存储对话历史
# max_turns=10：保留最近 10 轮对话（约 2000 tokens）
memory = InMemoryMemory(max_turns=10)

# ---- 3. 微信 API 客户端 ----
# 用于客服消息推送（异步回复）
# 即使 AppID/AppSecret 未配置也能创建，通过 is_configured() 判断
wechat_api = WeChatAPI(
    app_id=app.config['WECHAT_APP_ID'],
    app_secret=app.config['WECHAT_APP_SECRET'],
)

# ---- 4. 线程池 ----
# 用于后台异步处理 AI 请求
# max_workers=4：同时最多 4 个并发请求处理
# 超出队列的消息排队等待，不会丢失
executor = ThreadPoolExecutor(max_workers=4)

# ============================================================
# 路由入口
# ============================================================

@app.route('/wechat', methods=['GET', 'POST'])
def wechat():
    """微信消息入口 —— 接收微信服务器发来的所有请求

    路由：/wechat
    方法：GET（验证）、POST（消息）

    GET 请求处理流程（首次配置时触发）：
      1. 微信发送 4 个参数：signature, timestamp, nonce, echostr
      2. 用 SHA1 计算签名，与微信传来的 signature 比对
      3. 比对成功 → 返回 echostr 完成验证
      4. 比对失败 → 返回 403

    POST 请求处理流程（用户发消息时触发）：
      1. 读取微信 POST 的原始 XML
      2. 用 wechatpy 解析 XML → Python 对象
      3. 判断消息类型（text/event/其他）
      4. 分派给对应的处理函数
      5. 将回复渲染为 XML 返回
    """
    # 从配置读取 Token，用于验证签名
    token = app.config['WECHAT_TOKEN']

    if request.method == 'GET':
        # 微信服务器验证请求
        return _verify_server(token)

    # POST 消息处理请求
    return _handle_message()

# ============================================================
# 微信服务器验证
# ============================================================

def _verify_server(token: str):
    """验证微信服务器配置

    微信配置服务器 URL 时，会发送 GET 请求来验证。
    验证通过后才能正式接收消息。

    验证算法：
      1. 将 token、timestamp、nonce 三个字符串按字典序排序
      2. 拼接成一个字符串
      3. 计算 SHA1 哈希
      4. 与微信传来的 signature 对比
      5. 一致则返回 echostr，完成验证

    入参:
        token: 你在微信后台设置的 Token（str）

    返回:
        str: 验证通过 → 返回 echostr
        tuple: 验证失败 → (错误信息, 403)
    """
    # 从 GET 参数中取微信传来的四个值
    signature = request.args.get('signature', '')   # 微信计算的签名
    timestamp = request.args.get('timestamp', '')   # 时间戳
    nonce = request.args.get('nonce', '')           # 随机数
    echostr = request.args.get('echostr', '')       # 随机字符串（验证通过后原样返回）

    # 验证算法
    # 1. 排序：[token, timestamp, nonce] → [nonce, timestamp, token]（示例）
    tmp_list = sorted([token, timestamp, nonce])
    # 2. 拼接："noncetimestamptoken"
    tmp_str = ''.join(tmp_list)
    # 3. SHA1 哈希 → 十六进制字符串
    tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()

    # 4. 与微信传来的 signature 对比
    if tmp_str == signature:
        # 验证通过，返回 echostr
        # 微信收到 echostr 后确认服务器可用，配置完成
        return echostr

    # 验证失败，记录日志
    app.logger.warning('签名验证失败')
    return 'verification failed', 403

# ============================================================
# 消息接收与分发
# ============================================================

def _handle_message():
    """处理微信 POST 来的用户消息

    微信将用户消息封装为 XML，通过 POST 请求发送。
    本函数负责：
      1. 读取原始 XML 数据
      2. 用 wechatpy 解析为 Python 对象
      3. 按消息类型（text/event/其他）分发给对应处理器
      4. 将回复渲染为 XML 返回给微信

    流程：
      POST XML → wechatpy 解析 → 类型判断 → 处理器 → XML 回复

    返回:
        str/Response: XML 格式的回复内容
            文本消息 → AI 回复或"正在思考"
            事件消息 → 欢迎消息或事件确认
            其他类型 → 暂不支持提示
    """
    # request.data 是 Flask 提供的原始请求体
    # 微信发来的就是 UTF-8 编码的 XML 字符串
    xml = request.data
    if not xml:
        # 空请求体，微信可能只是探测连通性
        # 返回 "success" 表示收到
        return 'success'

    # wechatpy 的 parse_message 函数
    # 输入：微信 XML 字符串
    # 输出：Python 消息对象，根据 MsgType 返回不同的子类型
    #   msg.type      → 'text', 'image', 'event' 等
    #   msg.source    → FromUserName（用户的 OpenID）
    #   msg.target    → ToUserName（公众号的 AppID）
    #   msg.content   → 文本消息内容（如果是 text 类型）
    #   msg.event     → 事件类型（如果是 event 类型，如 'subscribe'）
    msg = parse_message(xml)

    # 记录收到消息的日志
    # hasattr 判断：只有文本消息才有 content 属性
    app.logger.info(
        f'收到消息 [{msg.type}] from {msg.source}: '
        f'{msg.content if hasattr(msg, "content") else ""}'
    )

    # 根据消息类型分派给对应的处理函数
    if msg.type == 'text':
        # 文本消息 → AI 对话处理
        reply = _handle_text(msg)
    elif msg.type == 'event':
        # 事件消息 → 关注/取关等
        reply = _handle_event(msg)
    else:
        # 其他类型（图片/语音/视频等）暂不支持
        reply = TextReply(content='暂不支持该类型的消息', message=msg)

    # 将回复对象渲染为 XML 并返回
    return _render_reply(reply)

# ============================================================
# 文本消息处理（核心逻辑）
# ============================================================

def _handle_text(msg):
    """处理文本消息 —— 调用 AI 并回复用户

    支持两种回复模式，根据 AppID/AppSecret 是否配置自动切换：

    1. 异步模式（推荐）：
       条件：WECHAT_APP_ID 和 WECHAT_APP_SECRET 均已配置
       流程：立即返回"正在思考" → 后台调 AI → 客服消息推送
       优点：永不超时，用户先看到提示再看到真实回复
       缺点：依赖微信客服消息接口

    2. 同步模式（降级）：
       条件：未配置 AppID/AppSecret
       流程：直接调用 AI → 等待回复 → 返回给微信
       优点：无需额外配置
       缺点：可能超过 5 秒超时限

    入参:
        msg: wechatpy 解析后的消息对象
            msg.source  → 用户 OpenID（用于记忆存储）
            msg.content → 用户消息文本

    返回:
        TextReply: 微信 XML 回复对象
    """
    # 用户的唯一标识（微信 OpenID）
    # 在对话中用于区分不同用户，存储各自的对话历史
    user_id = msg.source

    # 从记忆模块读取该用户的历史对话
    # 返回消息列表（空列表表示无历史）
    history = memory.get_history(user_id)

    # ---- 判断是否启用异步模式 ----
    # is_configured() 检查 AppID 和 AppSecret 是否都已填写
    # 只有在两个都有值时才启用异步模式
    if wechat_api.is_configured():
        # ========== 异步路径（推荐） ==========

        # 第一步：立即返回"正在思考"提示
        # 这个回复必须在 5 秒内返回给微信，否则微信会提示用户
        # "该公众号暂时无法提供服务"
        quick_reply = TextReply(
            content="正在思考中，请稍候...",
            message=msg,
        )

        # 第二步：将 AI 处理任务提交到线程池
        # executor.submit() 是异步的，它立即返回，不阻塞主线程
        # _process_and_push 会在后台线程中执行：
        #   1. 调用 DeepSeek API
        #   2. 保存对话到记忆
        #   3. 通过微信客服消息 API 推送给用户
        executor.submit(_process_and_push, user_id, msg.content, history)

        # 立即返回"正在思考"给微信
        return quick_reply

    # ========== 同步路径（降级方案） ==========

    # 组装消息列表，发送给 AI
    # 消息列表的结构决定了 AI 知道哪些上下文
    # 顺序：系统提示词 → 历史对话 → 当前消息
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},   # AI 人格设定
    ] + history + [                                      # 历史对话
        {"role": "user", "content": msg.content},        # 当前消息
    ]

    # 调用 DeepSeek API，等待 AI 回复
    # 这里会阻塞主线程，如果 AI 处理时间超过 5 秒
    # 微信会断开连接，用户看到"服务暂时不可用"
    ai_reply = ai_client.chat(messages)

    # 将用户消息和 AI 回复保存到记忆
    # 用户在下一轮发消息时，就能看到这一段对话历史
    memory.add_message(user_id, "user", msg.content)
    memory.add_message(user_id, "assistant", ai_reply)

    # 构造文本回复并返回
    return TextReply(content=ai_reply, message=msg)

# ============================================================
# 异步 AI 处理 + 客服消息推送
# ============================================================

def _process_and_push(user_id: str, content: str, history: list):
    """后台处理 AI 回复，通过客服消息推送给用户

    这个函数在**独立线程**中运行，不阻塞微信的 5 秒回复限制。
    被 executor.submit() 调用，由 ThreadPoolExecutor 调度。

    执行流程：
      1. 组装 messages 列表（含历史）
      2. 调用 DeepSeek API
      3. 保存对话到记忆
      4. 通过微信客服消息 API 推送给用户
      5. 出错时尝试推送错误提示

    入参:
        user_id: 用户的微信 OpenID（str）
        content: 用户发送的消息文本（str）
        history: 用户的历史对话消息列表（list of dict）
    """
    try:
        # 组装完整的消息列表
        # 结构：系统提示词 + 历史对话 + 当前消息
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ] + history + [
            {"role": "user", "content": content},
        ]

        # 调用 DeepSeek API（带 30 秒超时）
        # 这里没有 5 秒限制，可以慢慢等
        ai_reply = ai_client.chat(messages)

        # 保存对话到记忆
        # 用户在下一轮就能看到这些历史
        memory.add_message(user_id, "user", content)
        memory.add_message(user_id, "assistant", ai_reply)

        # 通过微信客服消息 API 推送给用户
        # 这会向用户的微信发送一条新消息（不是回复）
        # 所以用户会先看到"正在思考"，然后看到这条真实回复
        wechat_api.send_text(user_id, ai_reply)

        app.logger.info(f'异步回复已推送给 {user_id}')

    except Exception as e:
        # 异步处理出错，记录日志
        app.logger.error(f'异步 AI 处理失败: {e}')
        try:
            # 尝试推送错误提示给用户
            # 让用户知道出错了，而不是干等
            wechat_api.send_text(
                user_id,
                '抱歉，AI 处理暂时遇到问题，请稍后再试。',
            )
        except Exception:
            # 连错误提示都发不出去（比如 access_token 获取失败）
            # 只能静默处理，至少主流程没有中断
            pass

# ============================================================
# 事件消息处理
# ============================================================

def _handle_event(msg):
    """处理微信事件消息

    当用户在微信中触发事件时，微信会推送事件消息。
    常见事件：
      subscribe   — 用户关注公众号
      unsubscribe — 用户取消关注
      CLICK       — 用户点击菜单
      SCAN        — 用户扫码

    入参:
        msg: wechatpy 解析后的事件消息对象
            msg.event → 事件类型字符串（'subscribe', 'unsubscribe' 等）
            msg.source → 用户 OpenID

    返回:
        TextReply: 回复给用户的 XML，或 None（无需回复）
    """
    # 事件类型全转小写，避免大小写不一致
    event = msg.event.lower()

    if event == 'subscribe':
        # 用户关注公众号时触发
        # 返回一段欢迎语
        return TextReply(
            content='欢迎关注！我是 AI 客服机器人，正在努力学习中。\n'
                    '有什么问题尽管问我，我会尽力回答。',
            message=msg,
        )

    elif event == 'unsubscribe':
        # 用户取消关注时触发
        # 不需要回复（微信不会展示给用户）
        # 记录日志，后续可用于用户流失分析
        app.logger.info(f'用户 {msg.source} 取消关注')
        return None

    else:
        # 其他事件（菜单点击、扫码等）
        # 回复事件确认
        return TextReply(content=f'收到事件：{event}', message=msg)

# ============================================================
# 回复渲染
# ============================================================

def _render_reply(reply):
    """将回复对象渲染为微信 XML 格式

    TextReply 等对象本身是 Python 对象，需要通过 render()
    方法转换为微信能识别的 XML 字符串。

    入参:
        reply: wechatpy 的 Reply 对象，或 None
            TextReply → 文本回复
            None      → 不需要回复（如取消关注）

    返回:
        str: 微信 XML 格式的回复
             或 "success"（当 reply 为 None 时）
    """
    if reply is None:
        # 不需要回复，返回"success"表示收到
        # 微信收到 "success" 后不会做任何操作
        return 'success'

    # reply.render() → wechatpy 将 Reply 对象转换为 XML
    # 例如 TextReply("你好").render() 输出：
    #   <xml>
    #     <MsgType><![CDATA[text]]></MsgType>
    #     <Content><![CDATA[你好]]></Content>
    #     ...
    #   </xml>
    response = make_response(reply.render())

    # 设置正确的内容类型
    # 微信要求 application/xml，不是 text/xml
    response.content_type = 'application/xml'

    return response

# ============================================================
# 启动入口
# ============================================================

if __name__ == '__main__':
    """
    直接运行 `python app.py` 时的入口。

    启动信息：
      - Async mode: 异步模式是否启用
      - AI model:   当前使用的 AI 模型
      - Port:       监听端口
    """
    print(f'  Async mode: {"ON" if wechat_api.is_configured() else "OFF (未配 WECHAT_APP_ID/AppSecret)"}')
    print(f'  AI model:   {app.config.get("DEEPSEEK_MODEL")}')
    print(f'  Port:       {app.config.get("PORT", 8888)}')
    print(f'  Waiting for WeChat messages...')

    # 启动 Flask 开发服务器
    # host='0.0.0.0'：监听所有网卡
    # port：从配置读取
    # debug：调试模式，代码修改后自动重启
    app.run(
        host="0.0.0.0",
        port=app.config.get("PORT", 8888),
        debug=app.config.get("DEBUG", True),
    )
