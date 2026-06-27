#!/usr/bin/env python3
"""
验证 DeepSeek PoW 算法 - 使用正确的格式
"""

import hashlib
import time

# 测试数据
challenge = "6f03c2942e31a4c67fea7c3ee3184bb22bc32e9da51da1984f1a7fbb675c8531"
salt = "e35f5bc86e49d6101fa6"
expire_at = 1776156337056
difficulty = 144000

# prefix 格式: salt + "_" + expire_at + "_"
prefix = f"{salt}_{expire_at}_"

print("=" * 60)
print("DeepSeek PoW 算法验证")
print("=" * 60)
print(f"Challenge: {challenge}")
print(f"Salt: {salt}")
print(f"Expire_at: {expire_at}")
print(f"Prefix: {prefix}")
print(f"Difficulty: {difficulty}")

print("\n开始搜索...")

start_time = time.time()

# 使用 SHA3-256 (Keccak with padding=6)
found = None
for i in range(difficulty):
    test_str = prefix + str(i)
    hash_result = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()

    if hash_result == challenge:
        found = i
        break

elapsed = time.time() - start_time

print(f"\n搜索完成，耗时: {elapsed:.2f} 秒")
if found:
    print(f"找到答案: {found}")
    print(f"验证字符串: {prefix + str(found)}")
    print(f"哈希结果: {hashlib.sha3_256((prefix + str(found)).encode()).hexdigest()}")
else:
    print("未找到答案")

    # 显示一些样本哈希
    print("\n样本哈希:")
    for i in [0, 100, 1000, 10000, 50000, 100000]:
        test_str = prefix + str(i)
        h = hashlib.sha3_256(test_str.encode()).hexdigest()
        print(f"  prefix+{i}: {h[:30]}...")
        print(f"    目标: {challenge[:30]}...")

# 使用 JS Worker 中的备用方案：纯 Python Keccak sponge 实现
print("\n\n尝试手动 Keccak sponge 实现...")

# 从 JS Worker 代码中提取的关键点：
# - capacity = 256 (即 256 bit hash)
# - padding = 6 (从 squeeze(6) 可见)
# - prefix 格式: salt + "_" + expireAt + "_"
# - answer 是数字字符串

# Python hashlib.sha3_256 应该正确，但可能格式有问题
# 让我检查 expire_at 是否应该是秒而不是毫秒

print("\n尝试不同的 expire_at 格式:")

# expire_at 可能是秒级时间戳而不是毫秒
expire_at_seconds = expire_at // 1000
prefix_seconds = f"{salt}_{expire_at_seconds}_"
print(f"  秒级 prefix: {prefix_seconds}")

for i in range(min(10000, difficulty)):
    test_str = prefix_seconds + str(i)
    h = hashlib.sha3_256(test_str.encode()).hexdigest()
    if h == challenge:
        print(f"  找到答案（秒级）: {i}")
        break

# 或者 expire_at 需要不同的格式
expire_at_rounded = (expire_at // 1000) * 1000
prefix_rounded = f"{salt}_{expire_at_rounded}_"
print(f"\n  轮转 prefix: {prefix_rounded}")

for i in range(min(10000, difficulty)):
    test_str = prefix_rounded + str(i)
    h = hashlib.sha3_256(test_str.encode()).hexdigest()
    if h == challenge:
        print(f"  找到答案（轮转）: {i}")
        break

# 尝试使用 pycryptodome 的 Keccak
try:
    from Crypto.Hash import keccak

    print("\n使用 pycryptodome Keccak256 (padding=1, 原始 Keccak):")

    # 尝试不同的 padding
    k256 = keccak.new(digest_bits=256)

    for i in range(min(1000, difficulty)):
        k = keccak.new(digest_bits=256)
        k.update((prefix + str(i)).encode())
        h = k.hexdigest()
        if h == challenge:
            print(f"  找到答案 (pycryptodome): {i}")
            break

except ImportError:
    print("\npycryptodome 未安装")

# 结论：可能需要查看真实的 DeepSeek API 返回数据格式
print("\n\n结论:")
print("=" * 60)
print("Python hashlib.sha3_256 使用 SHA3-256 标准 (padding=6)")
print("这与 Worker JS 中的 squeeze(6) 一致")
print("但可能 challenge/salt/expire_at 的格式有问题")
print("需要从实际 API 获取实时数据来验证")