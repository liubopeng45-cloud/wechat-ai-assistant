"""
启动入口

简单的启动脚本，加载 app 模块后启动 Flask 开发服务器。
开发和调试阶段使用；生产环境建议用 gunicorn 或 waitress 部署。

用法：
    python run.py

等价于：
    python -m flask run --host=0.0.0.0 --port=8888
"""

from app import app

if __name__ == '__main__':
    """
    启动 Flask 开发服务器。

    参数来源：
      host:  监听所有网卡（0.0.0.0），方便 ngrok 和内网访问
      port:  从 config.py 读取，默认 8888
      debug: 开发模式，修改代码后自动重启
    """
    app.run(
        host='0.0.0.0',
        port=app.config.get('PORT', 8888),
        debug=app.config.get('DEBUG', True),
    )
