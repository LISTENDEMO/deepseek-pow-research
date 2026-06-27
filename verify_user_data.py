#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用用户提供的完整数据验证 PoW 算法
"""

import hashlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 用户提供的完整数据
challenge = "af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd"
salt = "811e05c93d1b71993710"
expire_at = 1776153216159
answer = 69992
difficulty = 144000

print("=" * 60)
print("PoW Algorithm Verification with User Data")
print("=" * 60)
print(f"Challenge: {challenge}")
print(f"Salt: {salt}")
print(f"expire_at: {expire_at}")
print(f"Answer (known): {answer}")
print(f"Difficulty: {difficulty}")

# 测试各种 prefix 格式
prefix_formats = [
    (f"{salt}_{expire_at}_", "standard: salt_expire_at_"),
    (f"{salt}_", "only salt_"),
    (f"{expire_at}_", "only expire_at_"),
    (f"{salt}{expire_at}", "no separators"),
    (f"{salt}_{expire_at}", "no trailing underscore"),
    (f"{expire_at}_{salt}_", "reversed"),
]

print("\nTesting prefix formats with SHA3-256:")
print("-" * 60)

for prefix, desc in prefix_formats:
    test_str = prefix + str(answer)
    hash_result = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()

    match = hash_result == challenge
    print(f"\n{desc}")
    print(f"  Prefix: {prefix}")
    print(f"  Test string: {test_str}")
    print(f"  Hash: {hash_result}")
    print(f"  Target: {challenge}")
    print(f"  Match: {match}")

    if match:
        print("\n*** FOUND CORRECT FORMAT! ***")
        print(f"Correct prefix format: {desc}")
        break

# 如果没找到，尝试 pycryptodome Keccak (padding=1)
print("\n\nTesting with pycryptodome Keccak256 (padding=1):")
print("-" * 60)

try:
    from Crypto.Hash import keccak

    for prefix, desc in [(f"{salt}_{expire_at}_", "standard"), (f"{salt}_", "salt_only")]:
        k = keccak.new(digest_bits=256)
        k.update((prefix + str(answer)).encode('utf-8'))
        hash_result = k.hexdigest()
        match = hash_result == challenge
        print(f"\n{desc}: {prefix + str(answer)}")
        print(f"  Hash: {hash_result}")
        print(f"  Match: {match}")

        if match:
            print("\n*** FOUND WITH KECCAK (padding=1)! ***")
            break

except ImportError:
    print("pycryptodome not installed")

# 反向验证：从 answer 构建 hash
print("\n\nReverse verification:")
print("-" * 60)
print("If hash(prefix + answer) != challenge, then:")
print("1. The algorithm might use different hash parameters")
print("2. Or the prefix format is wrong")
print("3. Or there's additional data in the hash input")