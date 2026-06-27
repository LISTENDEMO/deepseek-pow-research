#!/usr/bin/env python3
"""
使用 wbindgen 内存分配来运行 WASM
"""

import json
import base64
import struct
from pathlib import Path
import wasmtime

wasm_path = Path(__file__).parent / "sha3_wasm.wasm"

print("加载 WASM...")

engine = wasmtime.Engine()
store = wasmtime.Store(engine)
module = wasmtime.Module.from_file(store.engine, str(wasm_path))
instance = wasmtime.Instance(store, module, [])

exports = instance.exports(store)
memory = exports["memory"]
wasm_solve = exports["wasm_solve"]
wasm_hash = exports["wasm_deepseek_hash_v1"]

# wbindgen 函数
wbindgen_add_stack = exports["__wbindgen_add_to_stack_pointer"]
wbindgen_export_0 = exports["__wbindgen_export_0"]  # (i32, i32) -> i32
wbindgen_export_1 = exports["__wbindgen_export_1"]  # (i32, i32, i32, i32) -> i32
wbindgen_export_2 = exports["__wbindgen_export_2"]  # (i32, i32, i32) -> void

print("函数已加载!")

# 读取全局变量 (栈指针)
# Global 0 是栈指针，初始值 1048576
# 我们需要直接访问全局变量

def read_memory(store, memory, ptr, length):
    data = memory.data_ptr(store)
    return bytes(data[ptr:ptr + length])

def write_memory(store, memory, ptr, data_bytes):
    data = memory.data_ptr(store)
    for i, b in enumerate(data_bytes):
        data[ptr + i] = b

# 检查栈指针初始值
print("\n检查栈指针位置...")
stack_ptr = wbindgen_add_stack(store, 0)  # 获取当前栈指针
print(f"当前栈指针: {stack_ptr}")

# 查看栈附近的内存
stack_area = read_memory(store, memory, stack_ptr - 64, 64)
print(f"栈区域内容: {stack_area.hex()}")

# 查看数据段区域 (1048576+)
data_area = read_memory(store, memory, 1048576, 100)
print(f"数据段起始: {data_area[:50]}")

# 尝试使用 __wbindgen_export_0 来分配字符串
print("\n测试 __wbindgen_export_0...")

# 写入测试字符串到内存底部
test_str = "hello"
test_ptr = 0
write_memory(store, memory, test_ptr, test_str.encode('utf-8'))

# 调用 export_0: (ptr, len) -> result_ptr
try:
    result = wbindgen_export_0(store, test_ptr, len(test_str))
    print(f"export_0 结果: {result}")

    # 读取返回的内存区域
    result_bytes = read_memory(store, memory, result, 32)
    print(f"返回内容: {result_bytes.hex()}")

    # 可能是返回了 ptr+len 的结构体
    # wbindgen 通常返回 ptr 到一个包含两个 i32 的结构体
    ptr_out = struct.unpack('<i', result_bytes[:4])[0]
    len_out = struct.unpack('<i', result_bytes[4:8])[0]
    print(f"解析: ptr={ptr_out}, len={len_out}")

except Exception as e:
    print(f"export_0 错误: {e}")

# 尝试另一种方式：直接在栈上构建参数
print("\n\n尝试在栈上构建参数...")

# wasm_solve 参数顺序分析:
# 参数: [i32, i32, i32, i32, i32, f64]
# 可能: [challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty]

challenge = "6f03c2942e31a4c67fea7c3ee3184bb22bc32e9da51da1984f1a7fbb675c8531"
salt = "e35f5bc86e49d6101fa6"
expire_at = 1776156337056
difficulty = 144000.0

prefix = f"{salt}_{expire_at}_"

print(f"Challenge: {challenge[:30]}...")
print(f"Prefix: {prefix}")
print(f"Difficulty: {difficulty}")

# 在栈上分配空间
# 栈指针往下移动来分配空间
output_area = wbindgen_add_stack(store, -128)  # 分配 128 字节用于输出

# 写入 challenge 到低内存区域
challenge_ptr = 64  # 在数据段之前
write_memory(store, memory, challenge_ptr, challenge.encode('utf-8'))
challenge_len = len(challenge)

# 写入 prefix 到下一个位置
prefix_ptr = 128
write_memory(store, memory, prefix_ptr, prefix.encode('utf-8'))
prefix_len = len(prefix)

print(f"\nChallenge 写入: ptr={challenge_ptr}, len={challenge_len}")
print(f"Prefix 写入: ptr={prefix_ptr}, len={prefix_len}")
print(f"输出区域: ptr={output_area}")

# 现在尝试 wasm_solve
# 可能的参数顺序:
# 1. [output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty]
# 2. [challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty]

# 验证内存内容
print("\n验证内存内容:")
print(f"Challenge 内存: {read_memory(store, memory, challenge_ptr, 20).hex()}")
print(f"Prefix 内存: {read_memory(store, memory, prefix_ptr, 20).hex()}")

# 方案A: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)
try:
    print("\n方案A: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)")
    wasm_solve(store, challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_area, difficulty)

    # 读取输出
    answer = struct.unpack('<i', read_memory(store, memory, output_area, 4))[0]
    duration = struct.unpack('<d', read_memory(store, memory, output_area + 8, 8))[0]

    print(f"结果: answer={answer}, duration={duration}ms")

except Exception as e:
    print(f"方案A 错误: {e}")

# 方案B: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
try:
    print("\n方案B: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)")
    wasm_solve(store, output_area, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)

    answer = struct.unpack('<i', read_memory(store, memory, output_area, 4))[0]
    duration = struct.unpack('<d', read_memory(store, memory, output_area + 8, 8))[0]

    print(f"结果: answer={answer}, duration={duration}ms")

except Exception as e:
    print(f"方案B 错误: {e}")

# 查看栈区域的变化
print("\n栈区域变化:")
new_stack = wbindgen_add_stack(store, 0)
print(f"新栈指针: {new_stack}")
stack_area_after = read_memory(store, memory, output_area, 64)
print(f"栈内容: {stack_area_after.hex()}")

# 检查是否有 Rust panic 信息
print("\n检查数据段错误信息:")
error_area = read_memory(store, memory, 1048576, 200)
print(f"错误字符串: {error_area[:100]}")