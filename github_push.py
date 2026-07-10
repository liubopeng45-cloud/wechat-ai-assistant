import os
import base64
import requests

OWNER = "liubopeng45-cloud"
REPO = "wechat-ai-assistant"
PROJECT_DIR = r"D:\work\wechat-ai-assistant"
BRANCH = "main"

# 从环境变量读取 token
TOKEN = os.environ.get("GITHUB_PAT_TOKEN", "")
if not TOKEN:
    print("[FAIL] GITHUB_PAT_TOKEN 未设置")
    exit(1)

# 需要排除的目录名和文件名
EXCLUDE_DIRS = {".venv", "__pycache__", ".git", ".idea"}
EXCLUDE_FILES = {".env", "server.log"}

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# 收集要上传的文件
files_to_upload = []
for root, dirs, files in os.walk(PROJECT_DIR):
    # 排除目录
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if f in EXCLUDE_FILES or f.endswith(".log"):
            continue
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, PROJECT_DIR)
        # 统一用正斜杠
        rel_path = rel_path.replace("\\", "/")
        files_to_upload.append((rel_path, full_path))

print(f"找到 {len(files_to_upload)} 个文件待上传")
print()

for i, (rel_path, full_path) in enumerate(files_to_upload, 1):
    # 读取文件内容
    with open(full_path, "rb") as fh:
        content = fh.read()
    
    # Base64 编码
    b64_content = base64.b64encode(content).decode("utf-8")
    
    # 构建 API 请求
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{rel_path}"
    payload = {
        "message": f"上传 {rel_path}",
        "content": b64_content,
        "branch": BRANCH,
    }
    
    print(f"[{i}/{len(files_to_upload)}] 上传 {rel_path}...", end=" ")
    
    resp = requests.put(url, json=payload, headers=HEADERS)
    
    if resp.status_code in (200, 201):
        print("OK")
    else:
        data = resp.json()
        print(f"失败: {data.get('message', resp.status_code)}")

print()
print("上传完成！")
print(f"仓库地址: https://github.com/{OWNER}/{REPO}")
