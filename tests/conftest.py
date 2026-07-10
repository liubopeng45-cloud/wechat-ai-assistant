import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app import app as flask_app


@pytest.fixture
def app():
    """提供 Flask 测试应用实例"""
    flask_app.config['TESTING'] = True
    flask_app.config['WECHAT_TOKEN'] = 'test_token_2026'
    flask_app.config['DEEPSEEK_API_KEY'] = 'sk-test-key'
    flask_app.config['DEEPSEEK_BASE_URL'] = 'https://api.deepseek.com'
    flask_app.config['DEEPSEEK_MODEL'] = 'deepseek-chat'
    flask_app.config['WECHAT_APP_ID'] = ''
    flask_app.config['WECHAT_APP_SECRET'] = ''
    yield flask_app


@pytest.fixture
def client(app):
    """提供 Flask 测试客户端"""
    return app.test_client()
