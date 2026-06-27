#!/usr/bin/env python3
"""
DeepSeek WASM PoW Solver using wasmtime
"""

import json
import base64
from pathlib import Path
import wasmtime

# Load WASM
wasm_path = Path(__file__).parent / "sha3_wasm.wasm"

print("Loading WASM with wasmtime...")

# Create engine and store
engine = wasmtime.Engine()
store = wasmtime.Store(engine)

# Load module
module = wasmtime.Module.from_file(store.engine, str(wasm_path))
print(f"Module loaded!")

# Get exports
print("Exports:", [e.name for e in module.exports])

# Create instance (no imports needed!)
instance = wasmtime.Instance(store, module, [])

# Get functions
exports = instance.exports(store)
memory = exports["memory"]
wasm_hash_v1 = exports["wasm_deepseek_hash_v1"]
wasm_solve = exports["wasm_solve"]

print("Functions available!")

def write_string_to_memory(store, memory, text: str, ptr: int):
    """Write a string to WASM memory"""
    encoded = text.encode('utf-8')
    data = memory.data_ptr(store)
    for i, byte in enumerate(encoded):
        data[ptr + i] = byte
    return len(encoded)

def read_string_from_memory(store, memory, ptr: int, length: int):
    """Read a string from WASM memory"""
    data = memory.data_ptr(store)
    return bytes(data[ptr:ptr + length]).decode('utf-8')

def read_bytes_from_memory(store, memory, ptr: int, length: int):
    """Read bytes from WASM memory"""
    data = memory.data_ptr(store)
    return bytes(data[ptr:ptr + length])

# Test wasm_deepseek_hash_v1
print("\nTesting wasm_deepseek_hash_v1...")
print("=" * 60)

# Allocate memory positions
prefix_ptr = 0
output_ptr = 64

# Test prefix
test_prefix = "test_prefix_"
prefix_len = write_string_to_memory(store, memory, test_prefix, prefix_ptr)

print(f"Test prefix: {test_prefix}")
print(f"Prefix written at: {prefix_ptr}, length: {prefix_len}")

# Try different parameter configurations
test_answer = 12345

print(f"\nTesting answer: {test_answer}")

# Try calling wasm_deepseek_hash_v1
# Parameters might be: (prefix_ptr, prefix_len, answer) -> hash_ptr/length
# Or: (prefix_ptr, prefix_len, answer, output_ptr)

try:
    # First try: (prefix_ptr, prefix_len, answer)
    result = wasm_hash_v1(store, prefix_ptr, prefix_len, test_answer)
    print(f"Result type 1: {result}")

    # Read output from memory (assuming result is pointer)
    hash_bytes = read_bytes_from_memory(store, memory, result, 32)
    print(f"Hash (32 bytes): {hash_bytes.hex()}")
except Exception as e:
    print(f"Error type 1: {e}")

try:
    # Second try: (output_ptr, prefix_ptr, prefix_len, answer)
    result = wasm_hash_v1(store, output_ptr, prefix_ptr, prefix_len, test_answer)
    print(f"Result type 2: {result}")

    hash_bytes = read_bytes_from_memory(store, memory, output_ptr, 32)
    print(f"Hash at output_ptr: {hash_bytes.hex()}")
except Exception as e:
    print(f"Error type 2: {e}")

# Try wasm_solve
print("\n\nTesting wasm_solve...")
print("=" * 60)

# Test challenge data
challenge_str = "6f03c2942e31a4c67fea7c3ee3184bb22bc32e9da51da1984f1a7fbb675c8531"
salt = "e35f5bc86e49d6101fa6"
expire_at = 1776156337056
difficulty = 144000

prefix = f"{salt}_{expire_at}_"

print(f"Challenge: {challenge_str[:40]}...")
print(f"Prefix: {prefix}")
print(f"Difficulty: {difficulty}")

# Allocate memory for wasm_solve
challenge_ptr = 0
prefix_ptr = 64
output_ptr = 128

# Write to memory
challenge_len = write_string_to_memory(store, memory, challenge_str, challenge_ptr)
prefix_len = write_string_to_memory(store, memory, prefix, prefix_ptr)

print(f"\nChallenge at {challenge_ptr}, len={challenge_len}")
print(f"Prefix at {prefix_ptr}, len={prefix_len}")

# wasm_solve parameters:
# Likely: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty, output_ptr)
# Or: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)

try:
    # Try different orderings
    print("\nAttempting wasm_solve...")

    # Order 1: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
    result = wasm_solve(store, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
    print(f"Order 1 result: {result}")

    # Read answer from memory
    answer = read_bytes_from_memory(store, memory, output_ptr, 8)
    print(f"Output bytes: {answer.hex()}")
except Exception as e:
    print(f"Order 1 error: {e}")

try:
    # Order 2: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
    result = wasm_solve(store, output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
    print(f"Order 2 result: {result}")
except Exception as e:
    print(f"Order 2 error: {e}")

try:
    # Order 3: (challenge_ptr, prefix_ptr, difficulty) - might use memory data directly
    result = wasm_solve(store, challenge_ptr, prefix_ptr, difficulty)
    print(f"Order 3 result: {result}")
except Exception as e:
    print(f"Order 3 error: {e}")

# Inspect function signatures
print("\n\nFunction signatures:")
for e in module.exports:
    if e.name.startswith("wasm"):
        print(f"  {e.name}: {e}")