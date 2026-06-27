#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 Python SHA3-256 实现
"""

import sys
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

# 测试数据
test_cases = [
    ("", "a7ffc6f8bf7ed7e5c4f1c4208c6d6f4b72d1c5d0e6f8c7b7e6d5c4b3a2f1e0d"),
    ("abc", "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525f467f7f9f3d7b3e"),
    ("DeepSeek", "expected: ?"),
]

print("SHA3-256 测试:")
print("=" * 60)

# 使用 hashlib
print("\nPython hashlib.sha3_256:")
for data, expected in test_cases:
    h = hashlib.sha3_256(data.encode()).hexdigest()
    print(f"  '{data}' -> {h}")
    if expected.startswith("expected"):
        print(f"    (no known expected value)")
    else:
        print(f"    Expected: {expected}")
        print(f"    Match: {h == expected}")

# 使用 pycryptodome (如果可用)
try:
    from Crypto.Hash import SHA3_256
    print("\npycryptodome SHA3_256:")
    for data, expected in test_cases:
        h = SHA3_256.new(data.encode()).hexdigest()
        print(f"  '{data}' -> {h}")
except ImportError:
    print("\npycryptodome not installed")

# 测试 DeepSeek 格式
print("\n" + "=" * 60)
print("DeepSeek PoW 测试:")

challenge = "af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd"
salt = "811e05c93d1b71993710"
expire_at = 1776153216159
answer = 69992

prefix = f"{salt}_{expire_at}_"
test_str = prefix + str(answer)

print(f"  Test string: '{test_str}'")
print(f"  Expected hash: {challenge}")
print(f"  SHA3-256 hash: {hashlib.sha3_256(test_str.encode()).hexdigest()}")