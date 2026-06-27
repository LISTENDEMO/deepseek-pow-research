#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keccak256 Sponge Implementation with custom padding (for DeepSeek PoW)
Based on DeepSeek's JavaScript implementation with padding=6
"""

import struct
from typing import Optional


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

# Rotation offsets for Rho (corrected)
RHO_OFFSETS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 2, 62],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14]
]

# Pi permutation: π[x, y] = (y, (2x + 3y) mod 5)
# This maps position (x,y) to new position
def get_pi_pos(x, y):
    return (y, (2*x + 3*y) % 5)


def rol64(a: int, n: int) -> int:
    """Rotate left 64-bit"""
    return ((a >> (64 - n)) + (a << n)) & 0xFFFFFFFFFFFFFFFF


def keccak_f(state: list) -> None:
    """Keccak-f[1600] permutation"""
    for round_idx in range(24):
        # Theta step
        C = [state[5*x] ^ state[5*x+1] ^ state[5*x+2] ^ state[5*x+3] ^ state[5*x+4] for x in range(5)]
        D = [C[(x-1) % 5] ^ rol64(C[(x+1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[5*x + y] ^= D[x]

        # Rho and Pi steps
        B = [[0]*5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                new_x, new_y = get_pi_pos(x, y)
                B[new_x][new_y] = rol64(state[5*x + y], RHO_OFFSETS[x][y])

        # Chi step
        for x in range(5):
            for y in range(5):
                state[5*x + y] = B[x][y] ^ ((~B[(x+1)%5][y]) & B[(x+2)%5][y])

        # Iota step
        state[0] ^= RC[round_idx]


class KeccakSponge:
    """Keccak Sponge with custom padding"""

    def __init__(self, capacity: int = 256, padding: int = 6):
        self.capacity = capacity
        self.padding = padding
        self.rate = 200 - capacity // 4  # in bytes
        self.state = [0] * 25  # 1600 bits as 25 uint64
        self.queue = bytearray(self.rate)
        self.queue_offset = 0

    def absorb(self, data: bytes) -> 'KeccakSponge':
        """Absorb data into sponge"""
        for byte in data:
            self.queue[self.queue_offset] = byte
            self.queue_offset += 1
            if self.queue_offset >= self.rate:
                self._absorb_block()
                self.queue_offset = 0
        return self

    def _absorb_block(self) -> None:
        """Absorb a full block into state"""
        # Convert queue bytes to state uint64s
        for i in range(0, self.rate, 8):
            if i + 8 <= self.rate:
                word = struct.unpack('<Q', self.queue[i:i+8])[0]
                self.state[i // 8] ^= word
        keccak_f(self.state)

    def squeeze(self, output_len: int) -> bytes:
        """Squeeze output from sponge"""
        output = bytearray()

        # Padding
        self.queue[self.queue_offset] |= self.padding
        self.queue[self.rate - 1] |= 0x80

        # Absorb final block
        self._absorb_block()
        self.queue_offset = 0

        # Squeeze
        while len(output) < output_len:
            # Convert state to bytes
            for i in range(min(self.rate // 8, (output_len - len(output)) // 8)):
                output.extend(struct.pack('<Q', self.state[i]))
            if len(output) < output_len:
                keccak_f(self.state)

        return bytes(output[:output_len])

    def digest(self, output_len: int = 32) -> bytes:
        """Get digest"""
        return self.squeeze(output_len)

    def hexdigest(self, output_len: int = 32) -> str:
        """Get hex digest"""
        return self.digest(output_len).hex()

    def copy(self) -> 'KeccakSponge':
        """Create a copy of current state"""
        new = KeccakSponge(self.capacity, self.padding)
        new.state = self.state.copy()
        new.queue = bytearray(self.queue)
        new.queue_offset = self.queue_offset
        return new


def keccak256_hex(data: str, padding: int = 6) -> str:
    """
    Compute Keccak256 hash with DeepSeek's custom padding (6)

    Args:
        data: Input string
        padding: Padding byte (default 6 for DeepSeek)

    Returns:
        Hex string of hash
    """
    sponge = KeccakSponge(capacity=256, padding=padding)
    sponge.absorb(data.encode('utf-8'))
    return sponge.hexdigest()


# Test
if __name__ == '__main__':
    # Test with standard vectors
    print("Testing Keccak256 with padding=6 (DeepSeek)")
    print(f"  '': {keccak256_hex('')}")
    print(f"  'abc': {keccak256_hex('abc')}")
    print(f"  'test': {keccak256_hex('test')}")

    # Compare with padding=1 (standard Keccak)
    print("\nTesting with padding=1 (standard Keccak)")
    print(f"  '': {keccak256_hex('', padding=1)}")
    print(f"  'abc': {keccak256_hex('abc', padding=1)}")