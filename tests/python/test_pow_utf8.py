#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用已知 challenge 测试 PoW 算法
"""

import hashlib
import time
import sys

# 解决编码问题
sys.stdout.reconfigure(encoding='utf-8')

# 之前成功获取的 challenge 数据
challenge = "5ec7f27dd193030c1f7005e1c42a768b8e9f0c597ecbcabfb5ecc1ac63981747"
salt = "f4a237ca82e6d21c6b01"
expire_at = 1776157855885
difficulty = 144000

print("=" * 60)
print("DeepSeek PoW Algorithm Test")
print("=" * 60)
print(f"Challenge: {challenge}")
print(f"Salt: {salt}")
print(f"Expire_at: {expire_at}")
print(f"Difficulty: {difficulty}")

# 标准 prefix 格式
prefix = f"{salt}_{expire_at}_"
print(f"\nPrefix: {prefix}")

print("\nSearching (SHA3-256)...")
start = time.time()

found = None
for i in range(difficulty):
    test_str = prefix + str(i)
    h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()

    if h == challenge:
        found = i
        print(f"\n[OK] Found answer: {i}")
        print(f"Time: {time.time() - start:.2f}s")
        break

    if i % 10000 == 0:
        elapsed = time.time() - start
        print(f"  Progress: {i}/{difficulty} ({i/difficulty*100:.1f}%), Time: {elapsed:.2f}s")

elapsed = time.time() - start
if found is None:
    print(f"\nSearch complete, not found")
    print(f"Total time: {elapsed:.2f}s")

    # Show samples
    print("\nSample hashes:")
    for i in [0, 1, 10, 100, 1000]:
        test_str = prefix + str(i)
        h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
        print(f"  prefix+{i}: {h[:20]}... (target: {challenge[:20]}...)")

# Try other formats
print("\n\nTrying other prefix formats:")

alternative_formats = [
    (f"{salt}_", "salt_"),
    (f"{salt}{expire_at}", "salt+expire"),
    (f"{expire_at}_{salt}_", "expire_salt_"),
    (f"{salt}_{difficulty}_", "salt_diff_"),
    (f"{expire_at}_", "expire_"),
    (f"{salt}_{expire_at}", "salt_expire_no_end"),
]

for alt_prefix, desc in alternative_formats:
    print(f"\n{desc}: {alt_prefix}")

    found = None
    for i in range(min(5000, difficulty)):
        test_str = alt_prefix + str(i)
        h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
        if h == challenge:
            found = i
            break

    if found:
        print(f"  [OK] Found: {found}")
    else:
        h = hashlib.sha3_256((alt_prefix + "0").encode('utf-8')).hexdigest()
        print(f"  [FAIL] Not found (5000), h[0]={h[:20]}...")

# Try Keccak (padding=1)
print("\n\nTrying Keccak (padding=1):")

try:
    from Crypto.Hash import keccak

    test_prefixes = [prefix, f"{salt}_"]

    for test_prefix in test_prefixes:
        print(f"\nPrefix: {test_prefix}")

        found = None
        for i in range(min(10000, difficulty)):
            k = keccak.new(digest_bits=256)
            k.update((test_prefix + str(i)).encode('utf-8'))
            h = k.hexdigest()
            if h == challenge:
                found = i
                break

        if found:
            print(f"  [OK] Found: {found} (Keccak padding=1)")
        else:
            k = keccak.new(digest_bits=256)
            k.update((test_prefix + "0").encode('utf-8'))
            h = k.hexdigest()
            print(f"  [FAIL] h[0]={h[:20]}...")

except ImportError:
    print("  pycryptodome not installed")

# 结论
print("\n\n" + "=" * 60)
print("Conclusion:")
print("=" * 60)
print("If all formats fail, possibilities:")
print("1. Challenge expired (has expire_after=300000ms)")
print("2. Need WASM-specific implementation")
print("3. Need HIF service headers")

# 检查 expire_after
print(f"\nChallenge expire_after: 300000ms (5 minutes)")
print(f"Time between challenge creation and now: unknown")
print("This challenge may have already expired")