#!/usr/bin/env python3
"""
测试实时 PoW Challenge
"""

import requests
import hashlib
import json
import time
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "deepseek_login.json"

# 加载配置
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)

token = config.get("token")

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "x-app-version": "20241129.1",
    "x-client-locale": "zh_CN",
    "x-client-platform": "web",
})

# 获取 challenge
print("获取 PoW challenge...")
url = "https://chat.deepseek.com/api/v0/chat/create_pow_challenge"
response = session.post(url, json={"target_path": "/api/v0/chat/completion"})
result = response.json()

challenge_data = result["data"]["biz_data"]["challenge"]

challenge = challenge_data["challenge"]
salt = challenge_data["salt"]
expire_at = challenge_data["expire_at"]
difficulty = challenge_data["difficulty"]

print(f"\n实时 Challenge 数据:")
print(f"  algorithm: {challenge_data['algorithm']}")
print(f"  challenge: {challenge}")
print(f"  salt: {salt}")
print(f"  expire_at: {expire_at}")
print(f"  difficulty: {difficulty}")
print(f"  signature: {challenge_data['signature']}")

# 尝试解决 PoW
prefix = f"{salt}_{expire_at}_"
print(f"\nPrefix: {prefix}")

print("\n开始搜索 (SHA3-256)...")
start = time.time()

found = None
for i in range(difficulty):
    test_str = prefix + str(i)
    h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()

    if h == challenge:
        found = i
        break

elapsed = time.time() - start
print(f"搜索耗时: {elapsed:.2f}s")

if found:
    print(f"\n✓ 找到答案: {found}")
    print(f"验证: hash('{prefix + str(found)}') = {h}")
    print(f"目标: {challenge}")
else:
    print(f"\n✗ 未找到答案")

    # 显示样本
    print("\n样本哈希:")
    for i in [0, 1, 10, 100, 1000, 10000]:
        test_str = prefix + str(i)
        h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
        print(f"  prefix+{i}: {h[:20]}... (目标: {challenge[:20]}...)")

# 尝试其他格式
print("\n\n尝试其他 prefix 格式...")

alternative_prefixes = [
    f"{salt}_",  # 只有 salt
    f"{expire_at}_",  # 只有 expire_at
    f"{salt}{expire_at}",  # 无分隔符
    f"{salt}_{difficulty}_",  # 使用 difficulty 而不是 expire_at
]

for alt_prefix in alternative_prefixes:
    print(f"\n测试: {alt_prefix}")
    found = None
    for i in range(min(1000, difficulty)):
        test_str = alt_prefix + str(i)
        h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
        if h == challenge:
            found = i
            break

    if found:
        print(f"  ✓ 找到: {found}")
        break
    else:
        # 显示第一个哈希
        h = hashlib.sha3_256((alt_prefix + "0").encode('utf-8')).hexdigest()
        print(f"  ✗ 未找到 (prefix+0: {h[:20]}...)")

# 结论
print("\n\n" + "=" * 60)
print("结论:")
print("=" * 60)
print("如果所有格式都没找到答案，可能需要:")
print("1. 使用原始 Keccak (padding=1) 而不是 SHA3-256 (padding=6)")
print("2. 或者 WASM 实现使用了不同的哈希方式")

# 尝试 pycryptodome Keccak (padding=1)
try:
    from Crypto.Hash import keccak

    print("\n尝试 pycryptodome Keccak256 (原始 Keccak, padding=1):")

    for i in range(min(10000, difficulty)):
        k = keccak.new(digest_bits=256)
        k.update((prefix + str(i)).encode('utf-8'))
        h = k.hexdigest()
        if h == challenge:
            print(f"  ✓ 找到: {i} (使用原始 Keccak)")
            break

except ImportError:
    print("\npycryptodome 未安装")
    print("尝试安装: pip install pycryptodome")