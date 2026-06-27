#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek PoW - 正确的 Keccak 实现 (JS transposed layout)
关键发现: JS 使用 transposed 布局 (lane = 5*x + y)
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

# Rotation offsets for transposed layout: offsets[x][y] for lane at (x,y)
# In JS, lane index = 5*x + y, so we use offsets[x][y]
# Standard Keccak uses offsets[y][x] for lane = 5*y + x
# We need to transpose the standard offsets
RHO_STD = [
    [ 0,  1, 62, 28, 27],  # y=0
    [36, 44,  6, 55, 20],  # y=1
    [ 3, 10, 43, 25, 39],  # y=2
    [41,  2, 15, 21,  8],  # y=3
    [18, 56, 61, 14,  0],  # y=4
]
# Transpose to get offsets[x][y] for JS layout
RHO_OFFSETS_JS = [[RHO_STD[y][x] for y in range(5)] for x in range(5)]

def rol64(a, n):
    """Rotate 64-bit value left by n bits"""
    n = n % 64
    if n == 0:
        return a
    return ((a << n) | (a >> (64 - n))) & 0xFFFFFFFFFFFFFFFF

def keccak_f_js(state):
    """
    Keccak-f[1600] permutation - JS transposed layout version

    JS Layout: lane[x][y] = state[5*x + y]  (transposed from standard)
    Standard: lane[x][y] = state[5*y + x]

    This means:
    - Row y in standard = Column y in JS (indices 5*0+y, 5*1+y, 5*2+y, 5*3+y, 5*4+y)
    - Column x in standard = Row x in JS (indices 5*x+0, 5*x+1, 5*x+2, 5*x+3, 5*x+4)
    """
    for round_idx in range(24):
        # Theta - In JS, compute parity of "rows" which are actually columns in standard
        # Row y (JS) = lanes at 5*0+y, 5*1+y, ... = standard column y
        C = []
        for y in range(5):
            parity = 0
            for x in range(5):
                parity ^= state[5*x + y]
            C.append(parity)

        # D[y] = C[(y-1)%5] rol 1 ^ C[(y+1)%5]
        D = [C[(y-1) % 5] ^ rol64(C[(y+1) % 5], 1) for y in range(5)]

        # Apply D to each lane in row y (which is column y in standard)
        for y in range(5):
            for x in range(5):
                state[5*x + y] ^= D[y]

        # Rho and Pi - combined in JS
        # In standard Keccak: lane (x,y) -> lane (y, 2x+3y) with rotation offsets[y][x]
        # In JS with transposed layout: lane index = 5*x + y
        # We need to figure out the correct transformation

        B = [0] * 25
        for x in range(5):
            for y in range(5):
                # Standard Pi: (x, y) -> (y, (2x + 3y) % 5)
                new_x = y
                new_y = (2*x + 3*y) % 5
                # Rotation amount: use JS offsets[x][y] (transposed from standard)
                rot = RHO_OFFSETS_JS[x][y]
                # Source lane in JS layout: 5*x + y
                src_lane = 5*x + y
                # Destination lane in JS layout: 5*new_x + new_y
                dst_lane = 5*new_x + new_y
                # Apply rotation and copy
                B[dst_lane] = rol64(state[src_lane], rot)

        # Chi - In JS, operates on "columns" which are rows in standard
        # Column x (JS) = lanes at 5*x+0, 5*x+1, ... = standard row x
        for x in range(5):
            for y in range(5):
                lane_idx = 5*x + y
                next1_y = (y + 1) % 5
                next2_y = (y + 2) % 5
                state[lane_idx] = B[lane_idx] ^ ((~B[5*x + next1_y]) & B[5*x + next2_y])

        # Iota - XOR round constant into lane (0,0) = state[0]
        state[0] ^= RC[round_idx]


class DeepSeekKeccak:
    """DeepSeek's Keccak with JS transposed layout"""

    def __init__(self):
        self.rate = 136  # bytes
        self.state = [0] * 25  # 25 64-bit lanes
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
                self._absorb_block()
                self.queue_offset = 0
        return self

    def _absorb_block(self):
        """Absorb block into state (little-endian 64-bit, JS layout)"""
        for i in range(0, self.rate, 8):
            if i + 8 <= self.rate:
                # Little-endian 64-bit matches JS lane representation
                word = struct.unpack('<Q', self.queue[i:i+8])[0]
                # Lane index in JS layout: lane[byte_offset//8] = state[byte_offset//8]
                # First 136 bytes go into lanes 0-16 (17 lanes)
                self.state[i // 8] ^= word
        keccak_f_js(self.state)

    def squeeze(self, output_bytes=32):
        """Squeeze output bytes"""
        # Padding
        self.queue[self.queue_offset] |= self.padding
        self.queue[self.rate - 1] |= 0x80

        # Final absorb
        self._absorb_block()

        # Squeeze output
        result = bytearray()
        remaining = output_bytes

        while remaining > 0:
            chunk_size = min(remaining, self.rate)
            for i in range(chunk_size):
                lane_idx = i // 8
                byte_in_lane = i % 8
                # Little-endian byte extraction
                result.append((self.state[lane_idx] >> (byte_in_lane * 8)) & 0xFF)
            remaining -= chunk_size
            if remaining > 0:
                keccak_f_js(self.state)

        return bytes(result)

    def hexdigest(self):
        return self.squeeze(32).hex()

    def copy(self):
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
print("DeepSeek PoW - JS Transposed Layout")
print("=" * 60)

challenge = "af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd"
salt = "811e05c93d1b71993710"
expire_at = 1776153216159
answer = 69992

prefix = f"{salt}_{expire_at}_"

print(f"\nTest 1:")
print(f"  Challenge: {challenge}")
print(f"  Prefix: '{prefix}'")
print(f"  Answer: {answer}")

hash_result = deepseek_hash(prefix, answer)
print(f"  Hash: {hash_result}")
print(f"  Match: {hash_result == challenge}")

if hash_result != challenge:
    print(f"\n  Searching...")
    start = time.time()
    for i in range(min(20000, 144000)):
        h = deepseek_hash(prefix, i)
        if h == challenge:
            print(f"  *** FOUND at {i} ***")
            break
    print(f"  Time: {time.time() - start:.2f}s")