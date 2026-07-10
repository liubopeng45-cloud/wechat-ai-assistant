import hashlib
import requests

TOKEN = 'wechat_ai_token_2026'
BASE_URL = 'http://127.0.0.1:8888/wechat'


def test_verification():
    """Test 1: server verification (GET)"""
    print('=' * 50)
    print('Test 1: Server Verification')
    print('=' * 50)

    timestamp = '1234567890'
    nonce = 'nonce123'

    tmp_list = sorted([TOKEN, timestamp, nonce])
    signature = hashlib.sha1(''.join(tmp_list).encode('utf-8')).hexdigest()

    resp = requests.get(BASE_URL, params={
        'signature': signature,
        'timestamp': timestamp,
        'nonce': nonce,
        'echostr': 'hello_world_123',
    })

    print(f'  status: {resp.status_code}')
    print(f'  body: {resp.text}')

    if resp.status_code == 200 and resp.text == 'hello_world_123':
        print('  [OK] verification passed')
    else:
        print('  [FAIL] verification failed')
    print()


def test_text_message():
    """Test 2: text message reply (POST)"""
    print('=' * 50)
    print('Test 2: Text Message Reply')
    print('=' * 50)

    xml_body = '''<xml>
  <ToUserName><![CDATA[gh_xxx]]></ToUserName>
  <FromUserName><![CDATA[o_test_user]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[你好，请问这个项目是做什么的？]]></Content>
</xml>'''

    resp = requests.post(
        BASE_URL,
        data=xml_body.encode('utf-8'),
        headers={'Content-Type': 'text/xml'},
    )

    print(f'  status: {resp.status_code}')
    print(f'  body:')
    print(f'  {resp.text}')

    if resp.status_code == 200 and '你说的是' in resp.text:
        print('  [OK] text reply works')
    else:
        print('  [FAIL] text reply failed')
    print()


def test_subscribe_event():
    """Test 3: subscribe event"""
    print('=' * 50)
    print('Test 3: Subscribe Event Reply')
    print('=' * 50)

    xml_body = '''<xml>
  <ToUserName><![CDATA[gh_xxx]]></ToUserName>
  <FromUserName><![CDATA[o_test_user]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[subscribe]]></Event>
</xml>'''

    resp = requests.post(
        BASE_URL,
        data=xml_body.encode('utf-8'),
        headers={'Content-Type': 'text/xml'},
    )

    print(f'  status: {resp.status_code}')
    print(f'  body:')
    print(f'  {resp.text}')

    if resp.status_code == 200 and '欢迎关注' in resp.text:
        print('  [OK] subscribe reply works')
    else:
        print('  [FAIL] subscribe reply failed')
    print()


if __name__ == '__main__':
    test_verification()
    test_text_message()
    test_subscribe_event()

    print('All tests completed!')
    print('If the server is not running, first run: python run.py')
    print('If port is not 8888, update BASE_URL in this file.')
