#!/usr/bin/env python3
"""
调试 API 响应
"""

import requests
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "deepseek_login.json"

with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)

token = config.get("token")
print(f"Token: {token}")

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "x-app-version": "20241129.1",
    "x-client-locale": "zh_CN",
    "x-client-platform": "web",
})

print("\n测试 create_pow_challenge...")

url = "https://chat.deepseek.com/api/v0/chat/create_pow_challenge"
data = {"target_path": "/api/v0/chat/completion"}

response = session.post(url, json=data)

print(f"状态码: {response.status_code}")
print(f"响应头: {json.dumps(dict(response.headers), indent=2)}")
print(f"响应长度: {len(response.content)}")
print(f"响应内容: {response.content}")
print(f"响应文本: '{response.text}'")

if response.text:
    try:
        result = response.json()
        print(f"\n解析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"解析错误: {e}")