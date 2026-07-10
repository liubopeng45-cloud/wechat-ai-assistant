import os
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')
from openai import OpenAI

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')


def test_api():
    print('Test: DeepSeek API Connection')
    if not API_KEY or API_KEY == 'sk-your-api-key-here':
        print('[FAIL] API Key not set')
        return False
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=100,
        )
        reply = resp.choices[0].message.content
        print(f'AI: {reply}')
        print('[OK]')
        return True
    except Exception as e:
        print(f'[FAIL] {e}')
        return False


def test_memory():
    print('\nTest: Conversation Memory')
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [{"role": "system", "content": "请简短回答"}]
    messages.append({"role": "user", "content": "我喜欢吃火锅"})
    r1 = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=100)
    reply1 = r1.choices[0].message.content
    messages.append({"role": "assistant", "content": reply1})
    print(f'User: 我喜欢吃火锅')
    print(f'AI:   {reply1}')
    messages.append({"role": "user", "content": "我刚才说了什么？"})
    r2 = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=100)
    reply2 = r2.choices[0].message.content
    print(f'User: 我刚才说了什么？')
    print(f'AI:   {reply2}')
    if '火锅' in reply2:
        print('[OK] Memory works')
    else:
        print('[INFO] Normal, AI may not mention directly')


if __name__ == '__main__':
    if test_api():
        test_memory()
    print('Done.')
