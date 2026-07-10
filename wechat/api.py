"""
微信模块 —— 公众平台 API 封装

封装微信公众平台的几个核心 API，用于异步回复消息。
主要解决微信 5 秒回复超时的限制：先用被动回复返回"正在思考"，
再用客服消息 API 异步推送 AI 的真正回复。

核心功能：
  1. access_token 管理：自动获取、缓存、过期刷新
  2. 客服消息发送：突破被动回复的 5 秒时限

参考资料：
  access_token API:
    https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
  客服消息 API:
    https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Service_Center_messages.html

用法：
    from wechat import WeChatAPI

    api = WeChatAPI(app_id="wx...", app_secret="...")
    api.send_text("用户OpenID", "你好")  # 向用户推送消息
"""

import time
import json
import requests
import logging

# 日志记录器，app.py 中配置的 Flask logger 会自动捕获这个 logger
logger = logging.getLogger(__name__)


class WeChatAPI:
    """微信公众平台 API 客户端

    管理 access_token 的自动获取和缓存，提供客服消息发送功能。

    属性:
        app_id:         微信公众平台 AppID
        app_secret:     微信公众平台 AppSecret
        _token:         当前缓存的 access_token（None 表示未获取）
        _token_expires: access_token 的过期时间戳（秒）
    """

    def __init__(self, app_id: str, app_secret: str):
        """初始化微信 API 客户端

        入参:
            app_id:     微信公众平台 AppID（str）
            app_secret: 微信公众平台 AppSecret（str）

        说明:
            即使没有配 AppID/AppSecret，也可以创建实例。
            通过 is_configured() 判断是否可用，配合降级使用。
        """
        self.app_id = app_id
        self.app_secret = app_secret
        # 当前缓存的 access_token，None 表示尚未获取
        self._token: str | None = None
        # access_token 的过期时间（Unix 时间戳），0 表示已过期
        self._token_expires: float = 0

    # ==================== access_token 管理 ====================

    def _get_access_token(self) -> str:
        """获取 access_token（自动缓存 + 提前刷新）

        access_token 是调用微信所有 API 的通行证。
        有效期 7200 秒（2 小时），过期后需要重新获取。
        本方法自动处理缓存和刷新，外部调用无需关心有效期。

        刷新策略：
          - 首次调用：向微信 API 请求
          - 非首次但未过期：返回缓存的 token
          - 已过期或将在 5 分钟内过期：重新请求

        返回:
            str — 有效的 access_token

        抛出:
            RuntimeError: 微信 API 返回错误时抛出，
              错误信息包含 errcode 和 errmsg，方便排查。

        API 文档:
            GET https://api.weixin.qq.com/cgi-bin/token
              ?grant_type=client_credential
              &appid=APPID
              &secret=APPSECRET
        """
        # 如果 token 存在且未过期，直接返回缓存
        if self._token and time.time() < self._token_expires:
            return self._token

        # 构造获取 access_token 的请求
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",  # 固定值
            "appid": self.app_id,               # 你的 AppID
            "secret": self.app_secret,          # 你的 AppSecret
        }

        # 发送 GET 请求
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        # 检查是否返回了 access_token
        # 成功响应: {"access_token": "xxx", "expires_in": 7200}
        # 失败响应: {"errcode": 40001, "errmsg": "invalid credential"}
        if "access_token" not in data:
            raise RuntimeError(
                f"获取 access_token 失败: {data.get('errmsg', '未知错误')} "
                f"(errcode: {data.get('errcode', 'unknown')})"
            )

        # 缓存 token 和过期时间
        self._token = data["access_token"]
        # expires_in 是 7200 秒，减去 300 秒（5 分钟）作为提前刷新窗口
        # 这样 token 在真正过期前 5 分钟就会刷新，避免边界情况
        self._token_expires = time.time() + data["expires_in"] - 300

        logger.info("access_token 已刷新（有效期 2 小时）")
        return self._token

    # ==================== 客服消息 ====================

    def send_text(self, to_user: str, content: str) -> dict:
        """发送客服文本消息给指定用户

        客服消息可以在 5 秒回复时限之外推送，是实现异步回复的关键。
        用户不需要主动发消息，服务器可以随时推送内容给用户。

        入参:
            to_user: 目标用户的 OpenID（str）
                即用户微信的 FromUserName，可从 msg.source 获取。
            content: 消息文本内容（str）
                支持中文，无需手动转码，ensure_ascii=False 确保中文正常。

        返回:
            dict — 微信 API 的响应 JSON。
            正常情况下返回 {"errcode": 0, "errmsg": "ok"}

        抛出:
            RuntimeError: 微信 API 返回 errcode != 0 时抛出。
            常见错误码：
              40001: access_token 无效（自动刷新机制会重试）
              40003: OpenID 无效（用户不存在或已取关）
              45015: 回复时间超限（超过 48 小时未互动）

        API 文档:
            POST https://api.weixin.qq.com/cgi-bin/message/custom/send
              ?access_token=ACCESS_TOKEN
            Body (JSON):
            {
                "touser": "OPENID",
                "msgtype": "text",
                "text": {"content": "Hello World"}
            }
        """
        # 先获取有效的 access_token（自动处理缓存和刷新）
        token = self._get_access_token()

        # 拼接完整的 API URL
        url = (f"https://api.weixin.qq.com/cgi-bin/message/custom/send"
               f"?access_token={token}")

        # 构建请求体
        payload = {
            "touser": to_user,       # 目标用户的 OpenID
            "msgtype": "text",        # 消息类型：文本
            "text": {
                "content": content,   # 消息内容
            },
        }

        # 使用 json.dumps 并设置 ensure_ascii=False
        # Python 默认将非 ASCII 字符转义为 \uXXXX，微信收到后原样展示
        # ensure_ascii=False 让中文字符原样写入 JSON
        body = json.dumps(payload, ensure_ascii=False)

        # 发送 POST 请求
        # 注意：用 data 参数 + 手动 Content-Type 替代 json 参数
        # 因为 requests 的 json= 参数内部用的是 ensure_ascii=True
        resp = requests.post(
            url,
            data=body.encode('utf-8'),                     # UTF-8 编码的 JSON 字符串
            headers={'Content-Type': 'application/json; charset=utf-8'},
            timeout=10,
        )
        data = resp.json()

        # 检查微信 API 返回的错误码
        # errcode=0 表示成功，非 0 表示失败
        if data.get("errcode", -1) != 0:
            raise RuntimeError(
                f"发送客服消息失败: {data.get('errmsg', '未知错误')} "
                f"(errcode: {data.get('errcode')})"
            )

        logger.info(f"客服消息已发送给 {to_user}")
        return data

    # ==================== 状态检查 ====================

    def is_configured(self) -> bool:
        """检查是否已配置 AppID 和 AppSecret

        返回:
            bool — True 表示配置完整，可以使用客服消息功能。
                  False 表示只能使用同步回复（有超时风险）。

        说明:
            这个方法用于决定走异步路径还是同步路径。
            如果未配置，服务会降级为同步回复（直接等 AI 返回，
            可能超过微信的 5 秒限制）。
        """
        return bool(self.app_id and self.app_secret)
