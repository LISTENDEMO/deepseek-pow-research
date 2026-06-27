#!/usr/bin/env node
/**
 * Corrected BigInt Keccak with proper offset indexing
 */

// Round constants as BigInt
const RC = [
    0x0000000000000001n, 0x0000000000008082n, 0x800000000000808an,
    0x8000000080008000n, 0x000000000000808bn, 0x0000000080000001n,
    0x8000000080008081n, 0x8000000000008009n, 0x000000000000008an,
    0x0000000000000088n, 0x0000000080008009n, 0x000000008000000an,
    0x000000008000808bn, 0x800000000000008bn, 0x8000000000008089n,
    0x8000000000008003n, 0x8000000000008002n, 0x8000000000000080n,
    0x000000000000800an, 0x800000008000000an, 0x8000000080008081n,
    0x8000000000008080n, 0x0000000080000001n, 0x8000000080008008n,
];

// Rotation offsets: offsets[x][y] for lane at position (x, y)
// Standard Keccak offsets
const RHO = [
    [ 0, 36,  3, 41, 18],  // x=0
    [ 1, 44, 10,  2, 56],  // x=1
    [62,  6, 43, 15, 61],  // x=2
    [28, 55, 25, 21, 56],  // x=3  -- Note: (3,4) should be 56, not 27
    [27, 20, 39,  8, 14],  // x=4
];

// Correct offsets (from FIPS 202)
const RHO_FIPS202 = [
    [ 0,  1, 62, 28, 27],
    [36, 44,  6, 55, 20],
    [ 3, 10, 43, 25, 39],
    [41, 55, 15, 21,  8],  // Fixed: (3,1) = 55
    [18,  2, 61, 56, 14],  // Fixed: (4,1) = 2, (4,3) = 56
];

function rol64(a, n) {
    n = BigInt(n % 64);
    if (n === 0n) return a;
    return ((a << n) | (a >> (64n - n))) & 0xFFFFFFFFFFFFFFFFn;
}

// Standard Keccak-f[1600] permutation (corrected)
function keccakF(state, startRound = 0) {
    for (let round = startRound; round < 24; round++) {
        // Theta
        const C = new Array(5);
        for (let x = 0; x < 5; x++) {
            C[x] = state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20];
        }
        const D = new Array(5);
        for (let x = 0; x < 5; x++) {
            D[x] = C[(x + 4) % 5] ^ rol64(C[(x + 1) % 5], 1);
        }
        for (let i = 0; i < 25; i++) {
            state[i] ^= D[i % 5];
        }

        // Rho and Pi
        const B = new Array(25).fill(0n);
        for (let x = 0; x < 5; x++) {
            for (let y = 0; y < 5; y++) {
                const srcIdx = 5 * y + x;  // source lane index
                const dstX = y;             // Pi: new column
                const dstY = (2 * x + 3 * y) % 5;  // Pi: new row
                const dstIdx = 5 * dstY + dstX;
                // Rotation: use offsets[x][y]
                B[dstIdx] = rol64(state[srcIdx], RHO_FIPS202[x][y]);
            }
        }

        // Chi
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                const idx = 5 * y + x;
                state[idx] = B[idx] ^ ((~B[5 * y + ((x + 1) % 5)]) & B[5 * y + ((x + 2) % 5)]) & 0xFFFFFFFFFFFFFFFFn;
            }
        }

        // Iota
        state[0] ^= RC[round];
    }
}

// Keccak sponge
class KeccakSponge {
    constructor(rateBytes = 136, startRound = 0, padding = 6) {
        this.rate = rateBytes;
        this.startRound = startRound;
        this.state = new Array(25).fill(0n);
        this.queue = Buffer.alloc(this.rate);
        this.queueOffset = 0;
        this.padding = padding;
    }

    absorb(data) {
        if (typeof data === 'string') {
            data = Buffer.from(data, 'utf8');
        }
        for (let i = 0; i < data.length; i++) {
            this.queue[this.queueOffset++] = data[i];
            if (this.queueOffset >= this.rate) {
                this._absorbBlock();
                this.queueOffset = 0;
            }
        }
        return this;
    }

    _absorbBlock() {
        for (let i = 0; i < this.rate; i += 8) {
            if (i + 8 <= this.rate) {
                let word = 0n;
                for (let j = 0; j < 8; j++) {
                    word |= BigInt(this.queue[i + j]) << BigInt(j * 8);
                }
                this.state[i / 8] ^= word;
            }
        }
        keccakF(this.state, this.startRound);
    }

    squeeze(outputBytes = 32) {
        this.queue[this.queueOffset] |= this.padding;
        this.queue[this.rate - 1] |= 0x80;
        this._absorbBlock();

        const result = Buffer.alloc(outputBytes);
        let offset = 0;
        while (offset < outputBytes) {
            const chunkLen = Math.min(this.rate, outputBytes - offset);
            for (let i = 0; i < chunkLen; i++) {
                const lane = Math.floor(i / 8);
                const byteInLane = i % 8;
                result[offset + i] = Number((this.state[lane] >> BigInt(byteInLane * 8)) & 0xFFn);
            }
            offset += chunkLen;
            if (offset < outputBytes) {
                keccakF(this.state, this.startRound);
            }
        }
        return result;
    }

    hexdigest() {
        return this.squeeze(32).toString('hex');
    }
}

// Test
const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;
const prefix = `${salt}_${expire_at}_`;
const testStr = prefix + String(answer);

console.log('='.repeat(60));
console.log('Corrected BigInt Keccak');
console.log('='.repeat(60));
console.log('Input:', testStr);
console.log('Target:', challenge);

// Standard (24 rounds)
console.log('\nStandard (24 rounds, padding=6):');
const std = new KeccakSponge(136, 0, 6);
std.absorb(testStr);
console.log('  Hash:', std.hexdigest());

// Node.js reference
const crypto = require('crypto');
console.log('  Node.js SHA3-256:', crypto.createHash('sha3-256').update(testStr).digest('hex'));

// Skip round 0 (23 rounds)
console.log('\nSkip round 0 (23 rounds, padding=6):');
const skip = new KeccakSponge(136, 1, 6);
skip.absorb(testStr);
console.log('  Hash:', skip.hexdigest());
console.log('  Match:', skip.hexdigest() === challenge);

// Search
console.log('\n' + '='.repeat(60));
console.log('Searching with skip round 0:');
for (let i = 0; i < 20000; i++) {
    const s = new KeccakSponge(136, 1, 6);
    s.absorb(prefix + String(i));
    if (s.hexdigest() === challenge) {
        console.log(`*** FOUND! answer = ${i} ***`);
        break;
    }
}
console.log('Done.');