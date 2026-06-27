#!/usr/bin/env python3
"""
DeepSeek WASM PoW Solver - 正确的参数顺序
"""

import json
import base64
from pathlib import Path
import wasmtime

# 加载 WASM
wasm_path = Path(__file__).parent / "sha3_wasm.wasm"

print("加载 WASM...")

engine = wasmtime.Engine()
store = wasmtime.Store(engine)
module = wasmtime.Module.from_file(store.engine, str(wasm_path))
instance = wasmtime.Instance(store, module, [])

exports = instance.exports(store)
memory = exports["memory"]
wasm_hash_v1 = exports["wasm_deepseek_hash_v1"]
wasm_solve = exports["wasm_solve"]
stack_adjust = exports["__wbindgen_add_to_stack_pointer"]

print("函数已加载!")

def write_string(store, memory, text: str, ptr: int):
    """写入字符串到内存"""
    encoded = text.encode('utf-8')
    data = memory.data_ptr(store)
    for i, byte in enumerate(encoded):
        data[ptr + i] = byte
    return len(encoded)

def read_bytes(store, memory, ptr: int, length: int):
    """从内存读取字节"""
    data = memory.data_ptr(store)
    return bytes(data[ptr:ptr + length])

def write_i32(store, memory, value: int, ptr: int):
    """写入 i32 到内存"""
    data = memory.data_ptr(store)
    # 小端序
    data[ptr] = value & 0xff
    data[ptr + 1] = (value >> 8) & 0xff
    data[ptr + 2] = (value >> 16) & 0xff
    data[ptr + 3] = (value >> 24) & 0xff

def read_i32(store, memory, ptr: int):
    """从内存读取 i32"""
    data = memory.data_ptr(store)
    return data[ptr] | (data[ptr+1] << 8) | (data[ptr+2] << 16) | (data[ptr+3] << 24)

def read_f64(store, memory, ptr: int):
    """从内存读取 f64"""
    data = memory.data_ptr(store)
    return struct.unpack('<d', bytes(data[ptr:ptr+8]))[0]

import struct

# 测试 wasm_deepseek_hash_v1
print("\n测试 wasm_deepseek_hash_v1")
print("=" * 60)

# 分配栈空间用于输出
output_ptr = stack_adjust(store, -64)

# 参数顺序猜测:
# 方案1: (output_ptr, prefix_ptr, prefix_len) + answer 通过某种方式传入
# 方案2: (prefix_ptr, prefix_len, answer) + output 需要预先分配

test_prefix = "test_"
test_answer = 123

prefix_ptr = 128
prefix_len = write_string(store, memory, test_prefix, prefix_ptr)

print(f"测试前缀: {test_prefix}")
print(f"测试答案: {test_answer}")
print(f"栈指针: {output_ptr}")

# 方案A: (output_ptr, prefix_ptr, prefix_len) - 但缺少 answer 参数
# 方案B: (prefix_ptr, prefix_len, answer) - 输出到栈

# 测试方案B: (prefix_ptr, prefix_len, answer)
try:
    print("\n尝试方案B: (prefix_ptr, prefix_len, answer)")
    wasm_hash_v1(store, prefix_ptr, prefix_len, test_answer)

    # 尝试读取输出 - 可能写入栈或固定位置
    # 检查栈位置
    hash_output = read_bytes(store, memory, output_ptr, 32)
    print(f"栈输出: {hash_output.hex()}")
except Exception as e:
    print(f"方案B错误: {e}")

# 测试方案A: 先写入 answer 到内存
try:
    print("\n尝试方案A: (output_ptr, prefix_ptr, prefix_len)")
    answer_ptr = 192
    write_i32(store, memory, test_answer, answer_ptr)

    wasm_hash_v1(store, output_ptr, prefix_ptr, prefix_len)

    hash_output = read_bytes(store, memory, output_ptr, 32)
    print(f"输出: {hash_output.hex()}")
except Exception as e:
    print(f"方案A错误: {e}")

# 查看内存布局
print("\n查看关键内存区域:")
print(f"前缀位置 (128): {read_bytes(store, memory, 128, 20).hex()}")
print(f"栈位置 ({output_ptr}): {read_bytes(store, memory, output_ptr, 64).hex()}")

# 测试 wasm_solve
print("\n\n测试 wasm_solve")
print("=" * 60)

# 参数: 5个 i32 + 1个 f64
# 可能顺序: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
# 或: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)

challenge = "6f03c2942e31a4c67fea7c3ee3184bb22bc32e9da51da1984f1a7fbb675c8531"
salt = "e35f5bc86e49d6101fa6"
expire_at = 1776156337056
difficulty = 144000.0  # f64

prefix = f"{salt}_{expire_at}_"

print(f"Challenge: {challenge[:30]}...")
print(f"Prefix: {prefix}")
print(f"Difficulty: {difficulty}")

# 分配内存
challenge_ptr = 256
prefix_ptr = 320
output_ptr = stack_adjust(store, -128)  # 重新分配栈

challenge_len = write_string(store, memory, challenge, challenge_ptr)
prefix_len = write_string(store, memory, prefix, prefix_ptr)

print(f"\nChallenge 写入位置: {challenge_ptr}, 长度: {challenge_len}")
print(f"Prefix 写入位置: {prefix_ptr}, 长度: {prefix_len}")
print(f"Output 位置: {output_ptr}")

# 方案1: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
try:
    print("\n方案1: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)")
    wasm_solve(store, output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)

    # 读取结果: answer (i32) + duration (f64) ?
    answer = read_i32(store, memory, output_ptr)
    duration = read_f64(store, memory, output_ptr + 8)

    print(f"结果: answer={answer}, duration={duration}ms")

    # 验证: 计算 hash(prefix + answer)
    verify_prefix = prefix + str(answer)
    print(f"验证字符串: {verify_prefix}")

except Exception as e:
    print(f"方案1错误: {e}")

# 方案2: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)
try:
    print("\n方案2: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)")
    wasm_solve(store, challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)

    answer = read_i32(store, memory, output_ptr)
    duration = read_f64(store, memory, output_ptr + 8)

    print(f"结果: answer={answer}, duration={duration}ms")
except Exception as e:
    print(f"方案2错误: {e}")

# 方案3: 其他顺序
try:
    print("\n方案3: (challenge_ptr, prefix_ptr, output_ptr, challenge_len, prefix_len, difficulty)")
    wasm_solve(store, challenge_ptr, prefix_ptr, output_ptr, challenge_len, prefix_len, difficulty)

    answer = read_i32(store, memory, output_ptr)
    duration = read_f64(store, memory, output_ptr + 8)

    print(f"结果: answer={answer}, duration={duration}ms")
except Exception as e:
    print(f"方案3错误: {e}")