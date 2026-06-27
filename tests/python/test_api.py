#!/usr/bin/env python3
"""
DeepSeek API 测试 - 详细调试
"""

import requests
import json
import time
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "deepseek_login.json"

# 加载配置
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)

token = config.get("token")
print(f"Token: {token[:20]}...")

# 基本请求测试
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "x-app-version": "20241129.1",
    "x-client-locale": "zh_CN",
    "x-client-platform": "web",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})

print("\n测试 API 调用...")

# 1. 测试 create_pow_challenge
print("\n1. create_pow_challenge:")
url = "https://chat.deepseek.com/api/v0/chat/create_pow_challenge"
data = {"target_path": "/api/v0/chat/completion"}

response = session.post(url, json=data)
print(f"  状态码: {response.status_code}")
print(f"  响应头: {dict(response.headers)}")
print(f"  响应内容: {response.text[:500] if response.text else '(空)'}")

# 2. 测试用户信息
print("\n2. 用户信息:")
url = "https://chat.deepseek.com/api/v0/user/info"
response = session.get(url)
print(f"  状态码: {response.status_code}")
print(f"  响应内容: {response.text[:500] if response.text else '(空)'}")

# 3. 测试会话列表
print("\n3. 会话列表:")
url = "https://chat.deepseek.com/api/v0/chat/session/list"
response = session.post(url, json={"page": 1})
print(f"  状态码: {response.status_code}")
print(f"  响应内容: {response.text[:500] if response.text else '(空)'}")

# 4. 测试不同端点
print("\n4. 其他测试:")
urls_to_test = [
    "https://chat.deepseek.com/api/v0/user/profile",
    "https://chat.deepseek.com/api/v0/chat/history",
]

for url in urls_to_test:
    try:
        response = session.get(url)
        print(f"  {url}: {response.status_code}")
    except Exception as e:
        print(f"  {url}: 错误 - {e}")

# 检查是否需要重新登录
print("\n\n分析:")
if response.status_code == 401 or "Unauthorized" in response.text:
    print("Token 可能已过期，需要重新登录")
elif response.status_code == 403:
    print("可能需要 x-hif headers")
elif response.status_code == 200 and not response.text:
    print("API 返回空响应，可能需要特定参数")