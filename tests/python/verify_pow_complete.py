#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用第一组完整数据验证 PoW 算法
"""

import hashlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 第一组数据（完整）
challenge = "af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd"
salt = "811e05c93d1b71993710"
expire_at = 1776153216159  # 从 telemetry ds_expireAt
answer = 69992

print("=" * 60)
print("PoW Verification - Complete Data Set 1")
print("=" * 60)
print(f"Challenge: {challenge}")
print(f"Salt: {salt}")
print(f"expire_at: {expire_at}")
print(f"Known answer: {answer}")

# 标准 prefix
prefix = f"{salt}_{expire_at}_"
test_str = prefix + str(answer)

print(f"\nTesting standard format:")
print(f"  Prefix: {prefix}")
print(f"  Test string: {test_str}")

# SHA3-256
sha3_hash = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
print(f"  SHA3-256: {sha3_hash}")
print(f"  Target:   {challenge}")
print(f"  Match:    {sha3_hash == challenge}")

# 如果不匹配，尝试不同编码
print("\n\nTrying different encodings:")
encodings = ['utf-8', 'ascii', 'latin-1']
for enc in encodings:
    h = hashlib.sha3_256(test_str.encode(enc)).hexdigest()
    print(f"  {enc}: {h[:20]}... (match: {h == challenge})")

# 尝试 pycryptodome Keccak
print("\n\nTrying pycryptodome Keccak (padding=1):")
try:
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256)
    k.update(test_str.encode('utf-8'))
    keccak_hash = k.hexdigest()
    print(f"  Keccak256: {keccak_hash}")
    print(f"  Match: {keccak_hash == challenge}")
except ImportError:
    print("  pycryptodome not installed")

# 如果标准格式不匹配，尝试其他格式
print("\n\nTrying alternative prefix formats:")

formats = [
    (f"{salt}_{expire_at}", "no trailing underscore"),
    (f"{salt}_", "only salt"),
    (f"{expire_at}_{salt}_", "reversed"),
    (f"{salt}{expire_at}", "no separators"),
    (salt, "just salt"),
]

for alt_prefix, desc in formats:
    test_str = alt_prefix + str(answer)
    h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
    match = h == challenge
    print(f"\n  {desc}:")
    print(f"    Test: {test_str[:40]}...")
    print(f"    Hash: {h[:20]}...")
    print(f"    Match: {match}")
    if match:
        print("    *** SUCCESS! ***")
        break

# 反向验证：用已知 answer 计算所有可能的 expire_at 范围
print("\n\nReverse search: finding correct expire_at...")
print(f"  Salt: {salt}")
print(f"  Answer: {answer}")
print(f"  Target: {challenge}")

# 在 expire_at 附近搜索
for exp in range(expire_at - 100000, expire_at + 100000, 1):
    prefix = f"{salt}_{exp}_"
    test_str = prefix + str(answer)
    h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
    if h == challenge:
        print(f"\n  *** FOUND! Correct expire_at = {exp} ***")
        print(f"  Difference from ds_expireAt: {expire_at - exp}")
        break

print("\n\nConclusion:")
print("=" * 60)
if hashlib.sha3_256((f"{salt}_{expire_at}_{answer}").encode()).hexdigest() == challenge:
    print("Algorithm verified: SHA3-256 with prefix = salt_expire_at_")
else:
    print("Algorithm NOT verified with standard format")
    print("Possible issues:")
    print("1. expire_at needs different processing")
    print("2. WASM uses different hash parameters")