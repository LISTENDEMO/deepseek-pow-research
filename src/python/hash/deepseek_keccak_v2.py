#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek PoW - 正确的 Keccak 实现 (rate=136 bytes, capacity=512 bits)
关键发现: JS 使用特殊的字节序处理！
"""

import struct
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

# Keccak round constants (as pairs of uint32 for JS compatibility)
RC = [
    (0x00000001, 0x00000000), (0x00008082, 0x00000000), (0x0000808a, 0x80000000),
    (0x80008000, 0x80000000), (0x0000808b, 0x00000000), (0x80000001, 0x00000000),
    (0x80008081, 0x80000000), (0x00008009, 0x80000000), (0x0000008a, 0x00000000),
    (0x00000088, 0x00000000), (0x80008009, 0x00000000), (0x8000000a, 0x00000000),
    (0x8000808b, 0x00000000), (0x0000008b, 0x80000000), (0x00008089, 0x80000000),
    (0x00008003, 0x80000000), (0x00008002, 0x80000000), (0x00000080, 0x80000000),
    (0x0000800a, 0x00000000), (0x8000000a, 0x80000000), (0x80008081, 0x80000000),
    (0x00008080, 0x80000000), (0x80000001, 0x00000000), (0x80008008, 0x80000000),
]

# Rotation offsets
RHO_OFFSETS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 2, 62],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14]
]

def rol64_pair(low, high, n):
    """Rotate a 64-bit value (stored as two 32-bit parts) by n bits"""
    if n == 0:
        return low, high
    if n < 32:
        new_low = (low << n) | (high >> (32 - n))
        new_high = (high << n) | (low >> (32 - n))
    else:
        n = n - 32
        new_low = high << n | low >> (32 - n)
        new_high = low << n | high >> (32 - n)
    return new_low & 0xFFFFFFFF, new_high & 0xFFFFFFFF

def copy_lane(src, src_idx, dst, dst_idx):
    """Copy a lane (2 uint32s) from src to dst"""
    dst[dst_idx] = src[src_idx]
    dst[dst_idx + 1] = src[src_idx + 1]

def keccak_f(state):
    """Keccak-f[1600] permutation using uint32 pairs (matching JS)"""
    C = [0] * 10  # 5 lanes as uint32 pairs
    D = [0] * 10  # 5 lanes as uint32 pairs
    W = [0] * 2   # temp lane

    for round_idx in range(24):
        # Theta - compute column parity
        for x in range(5):
            C[2*x] = state[2*x] ^ state[2*(x+5)] ^ state[2*(x+10)] ^ state[2*(x+15)] ^ state[2*(x+20)]
            C[2*x+1] = state[2*x+1] ^ state[2*(x+5)+1] ^ state[2*(x+10)+1] ^ state[2*(x+15)+1] ^ state[2*(x+20)+1]

        # Theta - compute D and apply
        for x in range(5):
            # D[x] = C[(x-1)%5] rol 1 ^ C[(x+1)%5]
            prev_x = (x + 4) % 5
            next_x = (x + 1) % 5
            # C[prev] rol 1
            W[0] = C[2*prev_x+1]  # low gets high
            W[1] = C[2*prev_x]    # high gets low
            # XOR with C[next]
            D[2*x] = W[0] ^ C[2*next_x]
            D[2*x+1] = W[1] ^ C[2*next_x+1]

            # Apply D to each row
            for y in range(5):
                state[2*(5*y + x)] ^= D[2*x]
                state[2*(5*y + x)+1] ^= D[2*x+1]

        # Rho and Pi
        B = [0] * 50  # 25 lanes as uint32 pairs
        for x in range(5):
            for y in range(5):
                new_x = y
                new_y = (2*x + 3*y) % 5
                # Copy and rotate
                src_idx = 2 * (5*y + x)
                rot = RHO_OFFSETS[x][y]
                low, high = rol64_pair(state[src_idx], state[src_idx+1], rot)
                B[2*(5*new_x + new_y)] = low
                B[2*(5*new_x + new_y)+1] = high

        # Chi
        for x in range(5):
            for y in range(5):
                idx = 2 * (5*x + y)
                next1_x = (x + 1) % 5
                next2_x = (x + 2) % 5
                # state[x,y] = B[x,y] ^ (~B[x+1,y] & B[x+2,y])
                # ~B[x+1,y] means invert both parts
                b_next1_low = B[2*(5*next1_x + y)]
                b_next1_high = B[2*(5*next1_x + y)+1]
                b_next2_low = B[2*(5*next2_x + y)]
                b_next2_high = B[2*(5*next2_x + y)+1]

                state[idx] = B[idx] ^ ((~b_next1_low & 0xFFFFFFFF) & b_next2_low)
                state[idx+1] = B[idx+1] ^ ((~b_next1_high & 0xFFFFFFFF) & b_next2_high)

        # Iota
        state[0] ^= RC[round_idx][0]
        state[1] ^= RC[round_idx][1]


def absorb_bytes_js(data, state):
    """
    Absorb bytes into state using JS's special byte ordering.

    JS code:
    e[n]^=t[r+7]<<24|t[r+6]<<16|t[r+5]<<8|t[r+4]  // state[n] gets bytes[7..4] BE
    e[n+1]^=t[r+3]<<24|t[r+2]<<16|t[r+1]<<8|t[r]  // state[n+1] gets bytes[3..0] BE

    So bytes [0,1,2,3,4,5,6,7] map to:
    - state[n+1] = (bytes[3]<<24 | bytes[2]<<16 | bytes[1]<<8 | bytes[0])
    - state[n] = (bytes[7]<<24 | bytes[6]<<16 | bytes[5]<<8 | bytes[4])
    """
    for r in range(0, len(data), 8):
        n = r // 4  # lane pair index
        if r + 8 <= len(data):
            # state[n] gets bytes[7..4] in big-endian order
            state[n] ^= (data[r+7] << 24) | (data[r+6] << 16) | (data[r+5] << 8) | data[r+4]
            # state[n+1] gets bytes[3..0] in big-endian order
            state[n+1] ^= (data[r+3] << 24) | (data[r+2] << 16) | (data[r+1] << 8) | data[r]
        else:
            # Handle partial block
            remaining = data[r:]
            padded = remaining + bytes(8 - len(remaining))
            state[n] ^= (padded[7] << 24) | (padded[6] << 16) | (padded[5] << 8) | padded[4]
            state[n+1] ^= (padded[3] << 24) | (padded[2] << 16) | (padded[1] << 8) | padded[0]


def squeeze_bytes_js(state, length):
    """
    Squeeze bytes from state using JS's special byte ordering.

    JS code:
    e[r]=t[n+1], e[r+1]=t[n+1]>>>8, ...  // bytes[0..3] = state[n+1] BE
    e[r+4]=t[n], e[r+5]=t[n]>>>8, ...    // bytes[4..7] = state[n] BE

    So bytes [0,1,2,3,4,5,6,7] come from:
    - bytes[0] = state[n+1] & 0xFF
    - bytes[1] = (state[n+1] >> 8) & 0xFF
    - bytes[2] = (state[n+1] >> 16) & 0xFF
    - bytes[3] = (state[n+1] >> 24) & 0xFF
    - bytes[4] = state[n] & 0xFF
    - bytes[5] = (state[n] >> 8) & 0xFF
    - bytes[6] = (state[n] >> 16) & 0xFF
    - bytes[7] = (state[n] >> 24) & 0xFF
    """
    result = bytearray()
    for r in range(0, length, 8):
        n = r // 4  # lane pair index
        # bytes[0..3] from state[n+1]
        result.append(state[n+1] & 0xFF)
        result.append((state[n+1] >> 8) & 0xFF)
        result.append((state[n+1] >> 16) & 0xFF)
        result.append((state[n+1] >> 24) & 0xFF)
        # bytes[4..7] from state[n]
        result.append(state[n] & 0xFF)
        result.append((state[n] >> 8) & 0xFF)
        result.append((state[n] >> 16) & 0xFF)
        result.append((state[n] >> 24) & 0xFF)
    return bytes(result[:length])


class DeepSeekKeccak:
    """DeepSeek's Keccak with rate=136 bytes, matching JS byte ordering"""

    def __init__(self):
        self.rate = 136  # bytes (DeepSeek specific: 200 - 256/4 = 136)
        self.state = [0] * 50  # 25 lanes as 50 uint32s (matching JS)
        self.queue = bytearray(self.rate)
        self.queue_offset = 0
        self.padding = 6

    def absorb(self, data):
        """Absorb data"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        for byte in data:
            self.queue[self.queue_offset] = byte
            self.queue_offset += 1
            if self.queue_offset >= self.rate:
                absorb_bytes_js(self.queue, self.state)
                keccak_f(self.state)
                self.queue_offset = 0
        return self

    def squeeze(self, output_bytes=32):
        """Squeeze output bytes"""
        # Apply padding
        self.queue[self.queue_offset] |= self.padding
        self.queue[self.rate - 1] |= 0x80

        # Final absorb
        absorb_bytes_js(self.queue, self.state)
        keccak_f(self.state)

        # Squeeze output (32 bytes for SHA3-256)
        result = bytearray()
        remaining = output_bytes
        offset = 0

        while remaining > 0:
            chunk_size = min(remaining, self.rate)
            chunk = squeeze_bytes_js(self.state, chunk_size)
            result.extend(chunk)
            remaining -= chunk_size
            if remaining > 0:
                keccak_f(self.state)

        return bytes(result)

    def hexdigest(self):
        return self.squeeze(32).hex()

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
    sponge.absorb(prefix)
    sponge.absorb(str(answer))
    return sponge.hexdigest()


# 测试用用户数据
print("=" * 60)
print("DeepSeek PoW Verification - JS Byte Ordering Match")
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
print(f"  Prefix: '{prefix}'")

hash_result = deepseek_hash(prefix, answer)
print(f"  Hash: {hash_result}")
print(f"  Match: {hash_result == challenge}")

if hash_result != challenge:
    # 快速搜索验证
    print(f"\n  Searching for correct answer...")
    start = time.time()
    for i in range(144000):
        h = deepseek_hash(prefix, i)
        if h == challenge:
            print(f"  *** FOUND! Answer = {i} (expected: {answer}) ***")
            break
        if i % 10000 == 0:
            print(f"    Checked {i}...")
    elapsed = time.time() - start
    print(f"  Search time: {elapsed:.2f}s")

# 第二组数据
print(f"\n" + "=" * 60)
challenge2 = "252f029a65d33fade32803d2f3bf23363584bda3be0e3110261659f9208107c1"
salt2 = "a9171b4026f92b32024f"
answer2 = 83094

print(f"Test 2:")
print(f"  Challenge: {challenge2}")
print(f"  Salt: {salt2}")
print(f"  Answer: {answer2}")
print(f"  Searching expire_at...")

start = time.time()
for exp in range(1776155800000, 1776156500000, 100):
    prefix = f"{salt2}_{exp}_"
    h = deepseek_hash(prefix, answer2)
    if h == challenge2:
        print(f"  *** FOUND! expire_at = {exp} ***")
        break
    if exp % 10000 == 0:
        print(f"    Checked {exp}...")
elapsed = time.time() - start
print(f"  Search time: {elapsed:.2f}s")