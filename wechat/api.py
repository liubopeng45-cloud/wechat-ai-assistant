"""
微信模块 —— 公众平台 API 封装

封装微信公众平台的几个核心 API，用于异步回复消息。
核心功能：
  1. access_token 管理：自动获取、缓存、过期刷新
  2. 客服消息发送：突破被动回复的 5 秒时限

用法：
    from wechat import WeChatAPI
    api = WeChatAPI(app_id="wx...", app_secret="...")
    api.send_text("用户OpenID", "你好")
"""

import time
import json
import requests
import logging

logger = logging.getLogger(__name__)


class WeChatAPI:
    """微信公众平台 API 客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_expires: float = 0

    def _get_access_token(self) -> str:
        """获取 access_token（自动缓存 + 提前 5 分钟刷新）"""
        if self._token and time.time() < self._token_expires:
            return self._token
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(
                f"获取 access_token 失败: {data.get('errmsg', '未知错误')}"
            )
        self._token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"] - 300
        logger.info("access_token 已刷新")
        return self._token

    def send_text(self, to_user: str, content: str) -> dict:
        """发送客服文本消息"""
        token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
        payload = {
            "touser": to_user,
            "msgtype": "text",
            "text": {"content": content},
        }
        body = json.dumps(payload, ensure_ascii=False)
        resp = requests.post(
            url,
            data=body.encode('utf-8'),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            timeout=10,
        )
        data = resp.json()
        if data.get("errcode", -1) != 0:
            raise RuntimeError(
                f"发送客服消息失败: {data.get('errmsg', '未知错误')}"
            )
        logger.info(f"客服消息已发送给 {to_user}")
        return data

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)
