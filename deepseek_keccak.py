#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek PoW - 正确的 Keccak 实现 (rate=136 bytes, capacity=512 bits)
"""

import hashlib
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Keccak round constants
RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808a,
    0x8000000080008000, 0x000000000000808b, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008a,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000a,
    0x000000008000808b, 0x800000000000008b, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800a, 0x800000008000000a, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

# Rotation offsets
RHO_OFFSETS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 2, 62],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14]
]

def rol64(a, n):
    return ((a >> (64 - n)) + (a << n)) & 0xFFFFFFFFFFFFFFFF

def keccak_f(state):
    """Keccak-f[1600] permutation"""
    for round_idx in range(24):
        # Theta
        C = [state[5*x] ^ state[5*x+1] ^ state[5*x+2] ^ state[5*x+3] ^ state[5*x+4] for x in range(5)]
        D = [C[(x-1) % 5] ^ rol64(C[(x+1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[5*x + y] ^= D[x]

        # Rho and Pi
        B = [[0]*5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                new_x = y
                new_y = (2*x + 3*y) % 5
                B[new_x][new_y] = rol64(state[5*x + y], RHO_OFFSETS[x][y])

        # Chi
        for x in range(5):
            for y in range(5):
                state[5*x + y] = B[x][y] ^ ((~B[(x+1)%5][y]) & B[(x+2)%5][y])

        # Iota
        state[0] ^= RC[round_idx]

class DeepSeekKeccak:
    """DeepSeek's Keccak with rate=136 bytes (1088 bits)"""

    def __init__(self):
        # DeepSeek specific: rate = 136 bytes (not standard 168)
        self.rate = 136  # bytes
        self.state = [0] * 25
        self.queue = bytearray(self.rate)
        self.queue_offset = 0
        self.padding = 6

    def absorb(self, data):
        """Absorb data"""
        for byte in data:
            self.queue[self.queue_offset] = byte
            self.queue_offset += 1
            if self.queue_offset >= self.rate:
                self._absorb_block()
                self.queue_offset = 0
        return self

    def _absorb_block(self):
        """Absorb block into state"""
        for i in range(0, self.rate, 8):
            if i + 8 <= self.rate:
                word = struct.unpack('<Q', self.queue[i:i+8])[0]
                self.state[i // 8] ^= word
        keccak_f(self.state)

    def squeeze(self):
        """Squeeze 32 bytes output"""
        # Padding
        self.queue[self.queue_offset] |= self.padding
        self.queue[self.rate - 1] |= 0x80

        # Final absorb
        self._absorb_block()

        # Squeeze 32 bytes
        output = bytearray()
        for i in range(4):  # 32 bytes = 4 uint64
            output.extend(struct.pack('<Q', self.state[i]))

        return bytes(output)

    def hexdigest(self):
        return self.squeeze().hex()

    def copy(self):
        """Copy state"""
        new = DeepSeekKeccak()
        new.state = self.state.copy()
        new.queue = bytearray(self.queue)
        new.queue_offset = self.queue_offset
        return new


def deepseek_hash(prefix: str, answer: int) -> str:
    """Compute DeepSeek PoW hash"""
    sponge = DeepSeekKeccak()
    sponge.absorb(prefix.encode('utf-8'))
    sponge.absorb(str(answer).encode('utf-8'))
    return sponge.hexdigest()


# 测试用用户数据
print("=" * 60)
print("DeepSeek PoW Verification - Correct Implementation")
print("=" * 60)

# 第一组数据
challenge = "af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd"
salt = "811e05c93d1b71993710"
expire_at = 1776153216159
answer = 69992

prefix = f"{salt}_{expire_at}_"

print(f"\nTest 1:")
print(f"  Challenge: {challenge}")
print(f"  Salt: {salt}")
print(f"  expire_at: {expire_at}")
print(f"  Answer: {answer}")
print(f"  Prefix: {prefix}")

hash_result = deepseek_hash(prefix, answer)
print(f"  Hash: {hash_result}")
print(f"  Match: {hash_result == challenge}")

# 第二组数据
challenge2 = "252f029a65d33fade32803d2f3bf23363584bda3be0e3110261659f9208107c1"
salt2 = "a9171b4026f92b32024f"
answer2 = 83094

print(f"\nTest 2:")
print(f"  Challenge: {challenge2}")
print(f"  Salt: {salt2}")
print(f"  Answer: {answer2}")
print(f"  Need expire_at...")

# 搜索正确的 expire_at
print(f"\n  Searching expire_at for Test 2...")
for exp in range(1776155800000, 1776156400000, 100):
    prefix = f"{salt2}_{exp}_"
    h = deepseek_hash(prefix, answer2)
    if h == challenge2:
        print(f"  *** FOUND! expire_at = {exp} ***")
        break

# 搜索验证（完整搜索）
print("\n\nFull verification search for Test 1:")
prefix = f"{salt}_{expire_at}_"
print(f"  Prefix: {prefix}")
print(f"  Searching 0-{144000}...")

import time
start = time.time()
found = None
for i in range(144000):
    h = deepseek_hash(prefix, i)
    if h == challenge:
        found = i
        break

elapsed = time.time() - start
print(f"  Result: {found if found else 'Not found'}")
print(f"  Time: {elapsed:.2f}s")