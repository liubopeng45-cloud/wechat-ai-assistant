import os, base64, sys, requests

OWNER = "liubopeng45-cloud"
REPO = "wechat-ai-assistant"
PROJECT_DIR = r"D:\work\wechat-ai-assistant"
BRANCH = "代码优化"

TOKEN = os.environ.get("GITHUB_PAT_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github.v3+json"}

def log(m):
    print(m)
    sys.stdout.flush()

# Collect files
EXCLUDE_DIRS = {"venv", "__pycache__", ".git", ".idea", ".pytest_cache", ".agents"}
EXCLUDE_FILES = {".env"}
files = []
for root, dirs, fnames in os.walk(PROJECT_DIR):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in fnames:
        if f in EXCLUDE_FILES or f.endswith(".log") or f.endswith(".pyc"):
            continue
        full = os.path.join(root, f)
        rel = os.path.relpath(full, PROJECT_DIR).replace("\\", "/")
        files.append((rel, full))

log(f"Found {len(files)} files")

# Step 1: Create blobs for all files
log("Step 1: Creating blobs...")
blob_items = []
for rel, full in files:
    with open(full, "rb") as fh:
        content_b64 = base64.b64encode(fh.read()).decode("utf-8")
    r = requests.post(f"https://api.github.com/repos/{OWNER}/{REPO}/git/blobs",
        headers=HEADERS, json={"content": content_b64, "encoding": "base64"}, timeout=30)
    r.raise_for_status()
    blob_sha = r.json()["sha"]
    blob_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob_sha})

log(f"  Created {len(blob_items)} blobs")

# Step 2: Create tree with all blobs
log("Step 2: Creating tree...")
r = requests.post(f"https://api.github.com/repos/{OWNER}/{REPO}/git/trees",
    headers=HEADERS, json={"tree": blob_items}, timeout=30)
r.raise_for_status()
tree_sha = r.json()["sha"]
log(f"  Tree SHA: {tree_sha}")

# Step 3: Create commit
log("Step 3: Creating commit...")
r = requests.post(f"https://api.github.com/repos/{OWNER}/{REPO}/git/commits",
    headers=HEADERS, json={
        "message": f"代码优化 - 增加生产部署、异常处理、持久化、速率限制、消息过滤、测试体系等",
        "tree": tree_sha,
    }, timeout=30)
r.raise_for_status()
commit_sha = r.json()["sha"]
log(f"  Commit SHA: {commit_sha}")

# Step 4: Create or update branch ref
log(f"Step 4: Setting branch \"{BRANCH}\"...")
r = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}", headers=HEADERS, timeout=30)
if r.status_code == 200:
    log("  Branch exists, updating...")
    r = requests.patch(f"https://api.github.com/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
        headers=HEADERS, json={"sha": commit_sha, "force": True}, timeout=30)
else:
    log("  Creating new branch...")
    r = requests.post(f"https://api.github.com/repos/{OWNER}/{REPO}/git/refs",
        headers=HEADERS, json={"ref": f"refs/heads/{BRANCH}", "sha": commit_sha}, timeout=30)
r.raise_for_status()
log("  Branch updated!")

log(f"\nDone! https://github.com/{OWNER}/{REPO}/tree/{BRANCH}")
