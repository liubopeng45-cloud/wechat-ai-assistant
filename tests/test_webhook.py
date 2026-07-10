"""测试：微信服务器验证和消息处理"""

import hashlib


class TestVerification:
    """微信服务器验证（GET /wechat）"""

    def test_verification_success(self, client):
        """签名校验成功时返回 echostr"""
        timestamp = '1234567890'
        nonce = 'nonce123'
        echostr = 'hello_world_123'
        token = 'test_token_2026'

        tmp_list = sorted([token, timestamp, nonce])
        signature = hashlib.sha1(''.join(tmp_list).encode()).hexdigest()

        resp = client.get('/wechat', query_string={
            'signature': signature,
            'timestamp': timestamp,
            'nonce': nonce,
            'echostr': echostr,
        })
        assert resp.status_code == 200
        assert resp.data.decode() == echostr

    def test_verification_failure(self, client):
        """签名校验失败时返回 403"""
        resp = client.get('/wechat', query_string={
            'signature': 'invalid',
            'timestamp': '0',
            'nonce': 'x',
            'echostr': 'x',
        })
        assert resp.status_code == 403

    def test_verification_missing_params(self, client):
        """缺少参数时返回 403"""
        resp = client.get('/wechat')
        assert resp.status_code == 403


class TestTextMessage:
    """文本消息处理（POST /wechat）"""

    def test_text_reply_sync_mode(self, client):
        """同步模式返回 AI 回复（降级路径）"""
        xml = '''<xml>
  <ToUserName><![CDATA[gh_test]]></ToUserName>
  <FromUserName><![CDATA[o_test_user]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[你好]]></Content>
</xml>'''
        resp = client.post(
            '/wechat',
            data=xml.encode('utf-8'),
            content_type='text/xml',
        )
        # 同步模式下应返回 XML 格式回复
        assert resp.status_code == 200
        assert resp.content_type == 'application/xml'

    def test_empty_body(self, client):
        """空请求体返回 success"""
        resp = client.post('/wechat', data='', content_type='text/xml')
        assert resp.status_code == 200
        assert resp.data.decode() == 'success'


class TestEventMessage:
    """事件消息处理"""

    def test_subscribe(self, client):
        """关注事件返回欢迎语"""
        xml = '''<xml>
  <ToUserName><![CDATA[gh_test]]></ToUserName>
  <FromUserName><![CDATA[o_test_user]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[subscribe]]></Event>
</xml>'''
        resp = client.post(
            '/wechat',
            data=xml.encode('utf-8'),
            content_type='text/xml',
        )
        assert resp.status_code == 200
        assert '欢迎关注' in resp.data.decode()

    def test_unsubscribe(self, client):
        """取消关注返回 success"""
        xml = '''<xml>
  <ToUserName><![CDATA[gh_test]]></ToUserName>
  <FromUserName><![CDATA[o_test_user]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[unsubscribe]]></Event>
</xml>'''
        resp = client.post(
            '/wechat',
            data=xml.encode('utf-8'),
            content_type='text/xml',
        )
        assert resp.status_code == 200
        assert resp.data.decode() == 'success'

    def test_unknown_event(self, client):
        """未知事件返回事件确认"""
        xml = '''<xml>
  <ToUserName><![CDATA[gh_test]]></ToUserName>
  <FromUserName><![CDATA[o_test_user]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[CLICK]]></Event>
</xml>'''
        resp = client.post(
            '/wechat',
            data=xml.encode('utf-8'),
            content_type='text/xml',
        )
        assert resp.status_code == 200
        assert '收到事件' in resp.data.decode()


class TestHealthCheck:
    """健康检查端点"""

    def test_health_endpoint(self, client):
        """GET /health 返回服务状态"""
        resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'up'
        assert 'async_mode' in data
        assert 'ai_model' in data
        assert 'total_users' in data
        assert 'timestamp' in data
