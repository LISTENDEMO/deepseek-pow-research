#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek PoW - Big-endian 64-bit lane absorption
关键发现: JS 使用 big-endian 64-bit 字节序！
"""

import struct
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

# Keccak round constants (as 64-bit values)
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

# Rotation offsets (standard)
RHO_OFFSETS = [
    [0, 1, 62, 28, 27],
    [36, 44, 6, 55, 20],
    [3, 10, 43, 25, 39],
    [41, 2, 15, 21, 8],
    [18, 56, 61, 14, 56]  # Note: last row is special
]

# Actually the standard offsets are:
RHO_OFFSETS_STD = [
    [ 0,  1, 62, 28, 27],
    [36, 44,  6, 55, 20],
    [ 3, 10, 43, 25, 39],
    [41,  2, 15, 21,  8],
    [18, 56, 61, 14,  0],  # (4,4) = 14, not 56
]

def rol64(a, n):
    """Rotate 64-bit value left by n bits"""
    n = n % 64
    return ((a << n) | (a >> (64 - n))) & 0xFFFFFFFFFFFFFFFF

def keccak_f(state):
    """Keccak-f[1600] permutation (standard implementation)"""
    for round_idx in range(24):
        # Theta - compute column parity
        C = [state[5*y] ^ state[5*y+1] ^ state[5*y+2] ^ state[5*y+3] ^ state[5*y+4] for y in range(5)]

        # Theta - compute D and apply
        D = [C[(y-1) % 5] ^ rol64(C[(y+1) % 5], 1) for y in range(5)]
        for y in range(5):
            for x in range(5):
                state[5*y + x] ^= D[y]

        # Rho and Pi
        B = [0] * 25
        for x in range(5):
            for y in range(5):
                # Pi: (x, y) -> (y, (2x + 3y) % 5)
                new_x = y
                new_y = (2*x + 3*y) % 5
                # Rho: rotate by offset[x][y]
                B[5*new_y + new_x] = rol64(state[5*y + x], RHO_OFFSETS_STD[y][x])

        # Chi
        for x in range(5):
            for y in range(5):
                state[5*y + x] = B[5*y + x] ^ ((~B[5*y + (x+1)%5]) & B[5*y + (x+2)%5])

        # Iota
        state[0] ^= RC[round_idx]


class DeepSeekKeccak:
    """DeepSeek's Keccak with big-endian 64-bit absorption"""

    def __init__(self):
        self.rate = 136  # bytes (SHA3-256 rate)
        self.state = [0] * 25  # 25 64-bit lanes
        self.queue = bytearray(self.rate)
        self.queue_offset = 0
        self.padding = 6  # SHA3-256 padding

    def absorb(self, data):
        """Absorb data with big-endian 64-bit byte ordering"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        for byte in data:
            self.queue[self.queue_offset] = byte
            self.queue_offset += 1
            if self.queue_offset >= self.rate:
                self._absorb_block()
                self.queue_offset = 0
        return self

    def _absorb_block(self):
        """Absorb block into state using BIG-ENDIAN 64-bit"""
        for i in range(0, self.rate, 8):
            if i + 8 <= self.rate:
                # KEY FIX: Use big-endian unpacking!
                # JS: state[n] ^= bytes[7..4] BE, state[n+1] ^= bytes[3..0] BE
                # Combined as big-endian 64-bit: bytes[0..7] read as BE
                word = struct.unpack('>Q', self.queue[i:i+8])[0]
                self.state[i // 8] ^= word
        keccak_f(self.state)

    def squeeze(self, output_bytes=32):
        """Squeeze output bytes"""
        # Padding
        self.queue[self.queue_offset] |= self.padding
        self.queue[self.rate - 1] |= 0x80

        # Final absorb
        self._absorb_block()

        # Squeeze output (32 bytes)
        result = bytearray()
        remaining = output_bytes

        while remaining > 0:
            chunk_size = min(remaining, self.rate)
            for i in range(chunk_size):
                # Output as big-endian too
                lane_idx = i // 8
                byte_offset = 7 - (i % 8)  # Big-endian: byte 0 = lane >> 56
                result.append((self.state[lane_idx] >> (byte_offset * 8)) & 0xFF)
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


# Test
print("=" * 60)
print("DeepSeek PoW - Big-endian 64-bit Test")
print("=" * 60)

# Test 1
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
    print(f"\n  Searching for correct answer...")
    start = time.time()
    for i in range(min(100000, 144000)):
        h = deepseek_hash(prefix, i)
        if h == challenge:
            print(f"  *** FOUND! Answer = {i} ***")
            break
        if i % 10000 == 0:
            print(f"    Checked {i}...")
    elapsed = time.time() - start
    print(f"  Search time: {elapsed:.2f}s")