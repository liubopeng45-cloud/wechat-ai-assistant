"""生产环境启动入口

使用 waitress WSGI 服务器替代 Flask 开发服务器。
特点：
  - 多线程并发处理请求
  - 关闭 debug 模式（避免安全隐患）
  - 适合部署到内网服务器

用法：
    python run_prod.py

也可传递端口参数：
    python run_prod.py --port 80
"""

import sys
import argparse
from app import _check_config
from app import app


def main():
    _check_config()
    parser = argparse.ArgumentParser(description='启动生产服务器')
    parser.add_argument('--port', type=int, default=None,
                        help='监听端口（默认从 config 读取）')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='监听地址（默认 0.0.0.0）')
    args = parser.parse_args()

    port = args.port or app.config.get('PORT', 8888)
    host = args.host

    print(f'  Server:   waitress')
    print(f'  Address:  {host}:{port}')
    print(f'  Async:    {"ON" if app.config.get("WECHAT_APP_ID") else "OFF"}')
    print(f'  AI model: {app.config.get("DEEPSEEK_MODEL")}')
    print(f'  Mode:     production')
    print(f'  Waiting for WeChat messages...')
    print()

    from waitress import serve
    serve(app, host=host, port=port)


if __name__ == '__main__':
    main()
