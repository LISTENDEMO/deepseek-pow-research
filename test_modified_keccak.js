#!/usr/bin/env node
/**
 * Modified Keccak that skips round 0 (matching DeepSeek's JS implementation)
 */

const crypto = require('crypto');

// Standard Keccak round constants (24 rounds)
const RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808a,
    0x8000000080008000, 0x000000000000808b, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008a,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000a,
    0x000000008000808b, 0x800000000000008b, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800a, 0x800000008000000a, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
];

// Rotation offsets (standard)
const RHO_OFFSETS = [
    [ 0,  1, 62, 28, 27],
    [36, 44,  6, 55, 20],
    [ 3, 10, 43, 25, 39],
    [41,  2, 15, 21,  8],
    [18, 56, 61, 14,  0],
];

// Rotation offsets from JS Worker (v and w arrays)
// v = lane indices to rotate
// w = rotation amounts
const V = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1];
const W = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44];

function rol64(a, n) {
    n = n % 64;
    if (n === 0) return a;
    return ((a << n) | (a >>> (64 - n))) >>> 0;
}

// Standard Keccak-f permutation
function keccakFStandard(state) {
    for (let round = 0; round < 24; round++) {
        // Theta
        const C = [];
        for (let x = 0; x < 5; x++) {
            C[x] = 0;
            for (let y = 0; y < 5; y++) {
                C[x] ^= state[5*y + x];
            }
        }
        const D = [];
        for (let x = 0; x < 5; x++) {
            D[x] = C[(x-1+5) % 5] ^ rol64(C[(x+1) % 5], 1);
        }
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                state[5*y + x] ^= D[x];
            }
        }

        // Rho and Pi
        const B = new Array(25).fill(0);
        for (let x = 0; x < 5; x++) {
            for (let y = 0; y < 5; y++) {
                const newX = y;
                const newY = (2*x + 3*y) % 5;
                B[5*newY + newX] = rol64(state[5*y + x], RHO_OFFSETS[y][x]);
            }
        }

        // Chi
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                state[5*y + x] = B[5*y + x] ^ ((~B[5*y + (x+1)%5] >>> 0) & B[5*y + (x+2)%5]);
            }
        }

        // Iota
        state[0] ^= RC[round];
    }
}

// DeepSeek's modified Keccak-f (starts from round 1)
function keccakFDeepSeek(state) {
    // Skip round 0!
    for (let round = 1; round < 24; round++) {
        // Theta
        const C = [];
        for (let x = 0; x < 5; x++) {
            C[x] = 0;
            for (let y = 0; y < 5; y++) {
                C[x] ^= state[5*y + x];
            }
        }
        const D = [];
        for (let x = 0; x < 5; x++) {
            D[x] = C[(x-1+5) % 5] ^ rol64(C[(x+1) % 5], 1);
        }
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                state[5*y + x] ^= D[x];
            }
        }

        // Rho and Pi
        const B = new Array(25).fill(0);
        for (let x = 0; x < 5; x++) {
            for (let y = 0; y < 5; y++) {
                const newX = y;
                const newY = (2*x + 3*y) % 5;
                B[5*newY + newX] = rol64(state[5*y + x], RHO_OFFSETS[y][x]);
            }
        }

        // Chi
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                state[5*y + x] = B[5*y + x] ^ ((~B[5*y + (x+1)%5] >>> 0) & B[5*y + (x+2)%5]);
            }
        }

        // Iota (using round 1-23 constants)
        state[0] ^= RC[round];
    }
}

// Keccak sponge with customizable permutation
class KeccakSponge {
    constructor(rateBytes = 136, permutation = keccakFStandard, padding = 6) {
        this.rate = rateBytes;
        this.permutation = permutation;
        this.state = new Array(25).fill(0);
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
                // Little-endian 64-bit
                const word = this.queue.readBigUInt64LE(i);
                this.state[i / 8] ^= Number(word);
            }
        }
        this.permutation(this.state);
    }

    squeeze(outputBytes = 32) {
        // Padding
        this.queue[this.queueOffset] |= this.padding;
        this.queue[this.rate - 1] |= 0x80;

        // Final absorb
        this._absorbBlock();

        // Squeeze output
        const result = Buffer.alloc(outputBytes);
        let offset = 0;
        while (offset < outputBytes) {
            const chunkLen = Math.min(this.rate, outputBytes - offset);
            for (let i = 0; i < chunkLen; i++) {
                const lane = Math.floor(i / 8);
                const byteInLane = i % 8;
                result[offset + i] = Number((BigInt(this.state[lane]) >> BigInt(byteInLane * 8)) & 0xFFn);
            }
            offset += chunkLen;
            if (offset < outputBytes) {
                this.permutation(this.state);
            }
        }
        return result;
    }

    hexdigest() {
        return this.squeeze(32).toString('hex');
    }
}

// Test data
const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;

const prefix = `${salt}_${expire_at}_`;
const testStr = prefix + String(answer);

console.log('='.repeat(60));
console.log('Modified Keccak Test (skip round 0)');
console.log('='.repeat(60));
console.log('Input:', testStr);
console.log('Target:', challenge);

// Standard SHA3-256
console.log('\nStandard SHA3-256 (Node.js crypto):');
const sha3Std = crypto.createHash('sha3-256').update(testStr).digest('hex');
console.log('  Hash:', sha3Std);
console.log('  Match:', sha3Std === challenge);

// Our standard implementation
console.log('\nStandard Keccak-f (24 rounds):');
const stdSponge = new KeccakSponge(136, keccakFStandard, 6);
stdSponge.absorb(testStr);
console.log('  Hash:', stdSponge.hexdigest());
console.log('  Match:', stdSponge.hexdigest() === challenge);

// DeepSeek's modified (skip round 0)
console.log('\nDeepSeek modified (skip round 0, 23 rounds):');
const dsSponge = new KeccakSponge(136, keccakFDeepSeek, 6);
dsSponge.absorb(testStr);
console.log('  Hash:', dsSponge.hexdigest());
console.log('  Match:', dsSponge.hexdigest() === challenge);

// Test with different padding
console.log('\nDeepSeek modified with padding=1 (Keccak-256 style):');
const dsSpongeP1 = new KeccakSponge(136, keccakFDeepSeek, 1);
dsSpongeP1.absorb(testStr);
console.log('  Hash:', dsSpongeP1.hexdigest());
console.log('  Match:', dsSpongeP1.hexdigest() === challenge);

// Search with DeepSeek modified
console.log('\n' + '='.repeat(60));
console.log('Searching with DeepSeek modified permutation:');
console.log('='.repeat(60));

for (let i = 0; i < 20000; i++) {
    const testSponge = new KeccakSponge(136, keccakFDeepSeek, 6);
    testSponge.absorb(prefix + String(i));
    if (testSponge.hexdigest() === challenge) {
        console.log(`*** FOUND! answer = ${i} ***`);
        break;
    }
    if (i % 5000 === 0) {
        console.log(`Progress: ${i}`);
    }
}
console.log('Done.');