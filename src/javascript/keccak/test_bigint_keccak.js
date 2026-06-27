#!/usr/bin/env node
/**
 * Modified Keccak with proper BigInt handling
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

// Rotation offsets (standard)
const RHO_OFFSETS = [
    [ 0,  1, 62, 28, 27],
    [36, 44,  6, 55, 20],
    [ 3, 10, 43, 25, 39],
    [41,  2, 15, 21,  8],
    [18, 56, 61, 14,  0],
];

function rol64(a, n) {
    n = BigInt(n % 64);
    if (n === 0n) return a;
    return ((a << n) | (a >> (64n - n))) & 0xFFFFFFFFFFFFFFFFn;
}

// Keccak-f permutation (standard 24 rounds)
function keccakFStandard(state, skipRound0 = false) {
    const startRound = skipRound0 ? 1 : 0;

    for (let round = startRound; round < 24; round++) {
        // Theta
        const C = [];
        for (let x = 0; x < 5; x++) {
            C[x] = state[0*5 + x] ^ state[1*5 + x] ^ state[2*5 + x] ^ state[3*5 + x] ^ state[4*5 + x];
        }
        const D = [];
        for (let x = 0; x < 5; x++) {
            D[x] = C[(x-1+5) % 5] ^ rol64(C[(x+1) % 5], 1);
        }
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                state[y*5 + x] ^= D[x];
            }
        }

        // Rho and Pi
        const B = new Array(25).fill(0n);
        for (let x = 0; x < 5; x++) {
            for (let y = 0; y < 5; y++) {
                const newX = y;
                const newY = (2*x + 3*y) % 5;
                B[newY*5 + newX] = rol64(state[y*5 + x], RHO_OFFSETS[y][x]);
            }
        }

        // Chi
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                state[y*5 + x] = B[y*5 + x] ^ (~(B[y*5 + (x+1)%5]) & B[y*5 + (x+2)%5]) & 0xFFFFFFFFFFFFFFFFn;
            }
        }

        // Iota
        state[0] ^= RC[round];
    }
}

// Keccak sponge
class KeccakSponge {
    constructor(rateBytes = 136, skipRound0 = false, padding = 6) {
        this.rate = rateBytes;
        this.skipRound0 = skipRound0;
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
                // Little-endian 64-bit
                let word = 0n;
                for (let j = 0; j < 8; j++) {
                    word |= BigInt(this.queue[i + j]) << BigInt(j * 8);
                }
                this.state[i / 8] ^= word;
            }
        }
        keccakFStandard(this.state, this.skipRound0);
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
                result[offset + i] = Number((this.state[lane] >> BigInt(byteInLane * 8)) & 0xFFn);
            }
            offset += chunkLen;
            if (offset < outputBytes) {
                keccakFStandard(this.state, this.skipRound0);
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
console.log('BigInt Keccak Test');
console.log('='.repeat(60));
console.log('Input:', testStr);
console.log('Target:', challenge);

// Standard SHA3-256 (24 rounds)
console.log('\nStandard (24 rounds, padding=6):');
const stdSponge = new KeccakSponge(136, false, 6);
stdSponge.absorb(testStr);
const stdHash = stdSponge.hexdigest();
console.log('  Hash:', stdHash);
console.log('  Match:', stdHash === challenge);

// Skip round 0 (23 rounds)
console.log('\nSkip round 0 (23 rounds, padding=6):');
const skipSponge = new KeccakSponge(136, true, 6);
skipSponge.absorb(testStr);
const skipHash = skipSponge.hexdigest();
console.log('  Hash:', skipHash);
console.log('  Match:', skipHash === challenge);

// Standard with padding=1
console.log('\nStandard (24 rounds, padding=1):');
const p1Sponge = new KeccakSponge(136, false, 1);
p1Sponge.absorb(testStr);
console.log('  Hash:', p1Sponge.hexdigest());

// Skip round 0 with padding=1
console.log('\nSkip round 0 (23 rounds, padding=1):');
const skipP1Sponge = new KeccakSponge(136, true, 1);
skipP1Sponge.absorb(testStr);
console.log('  Hash:', skipP1Sponge.hexdigest());

// Compare with reference SHA3-256
const crypto = require('crypto');
console.log('\nNode.js SHA3-256 reference:');
console.log('  Hash:', crypto.createHash('sha3-256').update(testStr).digest('hex'));

// Search
console.log('\n' + '='.repeat(60));
console.log('Searching with skip round 0:');
for (let i = 0; i < 20000; i++) {
    const s = new KeccakSponge(136, true, 6);
    s.absorb(prefix + String(i));
    if (s.hexdigest() === challenge) {
        console.log(`*** FOUND! answer = ${i} ***`);
        break;
    }
    if (i % 5000 === 0) {
        console.log(`Progress: ${i}`);
    }
}
console.log('Done.');