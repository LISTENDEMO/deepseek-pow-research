#!/usr/bin/env python3
"""
使用已知 challenge 测试 PoW 算法
"""

import hashlib
import time

# 之前成功获取的 challenge 数据
challenge = "5ec7f27dd193030c1f7005e1c42a768b8e9f0c597ecbcabfb5ecc1ac63981747"
salt = "f4a237ca82e6d21c6b01"
expire_at = 1776157855885
difficulty = 144000

print("=" * 60)
print("DeepSeek PoW 算法测试")
print("=" * 60)
print(f"Challenge: {challenge}")
print(f"Salt: {salt}")
print(f"Expire_at: {expire_at}")
print(f"Difficulty: {difficulty}")

# 标准 prefix 格式: salt + "_" + expire_at + "_"
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
        print(f"\n✓ 找到答案: {i}")
        print(f"耗时: {time.time() - start:.2f}s")
        break

    # 每 10000 次显示进度
    if i % 10000 == 0:
        elapsed = time.time() - start
        print(f"  进度: {i}/{difficulty} ({i/difficulty*100:.1f}%), 耗时: {elapsed:.2f}s")

if found is None:
    elapsed = time.time() - start
    print(f"\n搜索完成，未找到答案")
    print(f"总耗时: {elapsed:.2f}s")

    # 显示样本
    print("\n样本哈希:")
    for i in [0, 1, 10, 100, 1000]:
        test_str = prefix + str(i)
        h = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()
        print(f"  prefix+{i}: {h}")

# 尝试其他格式
print("\n\n尝试其他 prefix 格式:")

alternative_formats = [
    # 格式1: 只有 salt
    (f"{salt}_", "salt_"),

    # 格式2: salt + expire_at (无分隔符)
    (f"{salt}{expire_at}", "salt+expire_at"),

    # 格式3: expire_at 在前
    (f"{expire_at}_{salt}_", "expire_salt_"),

    # 格式4: 使用 difficulty
    (f"{salt}_{difficulty}_", "salt_difficulty_"),

    # 格式5: 只有 expire_at
    (f"{expire_at}_", "expire_at_"),

    # 格式6: 无下划线结尾
    (f"{salt}_{expire_at}", "salt_expire_at"),
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
        print(f"  ✓ 找到: {found}")
    else:
        # 显示第一个哈希
        h = hashlib.sha3_256((alt_prefix + "0").encode('utf-8')).hexdigest()
        print(f"  ✗ 未找到 (前5000), h[0]={h[:20]}...")

# 尝试 pycryptodome Keccak (padding=1)
print("\n\n尝试 Keccak (padding=1):")

try:
    from Crypto.Hash import keccak

    for alt_prefix, desc in [(prefix, "standard"), (f"{salt}_", "salt_")]:
        print(f"\n{desc}: {alt_prefix}")

        found = None
        for i in range(min(10000, difficulty)):
            k = keccak.new(digest_bits=256)
            k.update((alt_prefix + str(i)).encode('utf-8'))
            h = k.hexdigest()
            if h == challenge:
                found = i
                break

        if found:
            print(f"  ✓ 找到: {found} (Keccak padding=1)")
        else:
            k = keccak.new(digest_bits=256)
            k.update((alt_prefix + "0").encode('utf-8'))
            h = k.hexdigest()
            print(f"  ✗ 未找到 (前10000), h[0]={h[:20]}...")

except ImportError:
    print("  pycryptodome 未安装")

print("\n\n" + "=" * 60)
print("结论:")
print("=" * 60)
print("如果所有格式都没找到，可能:")
print("1. Token 中的 challenge 已过期")
print("2. DeepSeek 使用了 WASM 特定的优化算法")
print("3. 需要从 HIF 服务获取额外的验证数据")