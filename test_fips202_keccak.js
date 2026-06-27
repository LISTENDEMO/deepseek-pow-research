#!/usr/bin/env node
/**
 * Correct Keccak with FIPS 202 standard rotation offsets
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

// FIPS 202 rotation offsets: R[x, y] where R[x][y] is the rotation for lane (x, y)
// Directly from FIPS 202 Section 3.2.1
const RHO = [
    [ 0, 36,  3, 41, 18],  // R[0, y] for y=0,1,2,3,4
    [ 1, 44, 10,  2, 62],  // R[1, y]
    [62,  6, 43, 15, 61],  // R[2, y]
    [28, 55, 25, 21, 56],  // R[3, y]
    [27, 20, 39,  8, 14],  // R[4, y]
];

function rol64(a, n) {
    n = BigInt(n % 64);
    if (n === 0n) return a;
    return ((a << n) | (a >> (64n - n))) & 0xFFFFFFFFFFFFFFFFn;
}

// Keccak-f[1600] permutation (FIPS 202 compliant)
function keccakF(state) {
    for (let round = 0; round < 24; round++) {
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
                // Source: lane at (x, y) = state[5*y + x]
                const srcIdx = 5 * y + x;
                // Destination: lane at (y, (2x+3y) mod 5)
                const dstX = y;
                const dstY = (2 * x + 3 * y) % 5;
                const dstIdx = 5 * dstY + dstX;
                // Rotation: R[x, y]
                const rot = RHO[x][y];
                B[dstIdx] = rol64(state[srcIdx], rot);
            }
        }

        // Chi
        for (let y = 0; y < 5; y++) {
            for (let x = 0; x < 5; x++) {
                const idx = 5 * y + x;
                const next1 = 5 * y + ((x + 1) % 5);
                const next2 = 5 * y + ((x + 2) % 5);
                state[idx] = B[idx] ^ ((~B[next1]) & B[next2]) & 0xFFFFFFFFFFFFFFFFn;
            }
        }

        // Iota
        state[0] ^= RC[round];
    }
}

// Keccak sponge
class KeccakSponge {
    constructor(rateBytes = 136, padding = 6) {
        this.rate = rateBytes;
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
        keccakF(this.state);
    }

    squeeze(outputBytes = 32) {
        // SHA3 padding: queue[offset] |= 0x06, queue[rate-1] |= 0x80
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
                keccakF(this.state);
            }
        }
        return result;
    }

    hexdigest() {
        return this.squeeze(32).toString('hex');
    }
}

// Test
const crypto = require('crypto');

// Test empty string first (known SHA3-256("") = a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a)
console.log('='.repeat(60));
console.log('FIPS 202 Standard Keccak Verification');
console.log('='.repeat(60));

console.log('\nSHA3-256("") test:');
const emptySponge = new KeccakSponge(136, 6);
emptySponge.absorb('');
const emptyHash = emptySponge.hexdigest();
console.log('  My implementation:', emptyHash);
console.log('  Expected:', 'a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a');
console.log('  Node.js SHA3-256:', crypto.createHash('sha3-256').update('').digest('hex'));
console.log('  Match:', emptyHash === 'a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a');

console.log('\nSHA3-256("abc") test:');
const abcSponge = new KeccakSponge(136, 6);
abcSponge.absorb('abc');
const abcHash = abcSponge.hexdigest();
console.log('  My implementation:', abcHash);
console.log('  Expected:', '3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532');
console.log('  Node.js SHA3-256:', crypto.createHash('sha3-256').update('abc').digest('hex'));
console.log('  Match:', abcHash === '3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532');

// DeepSeek test
console.log('\n' + '='.repeat(60));
console.log('DeepSeek PoW Test');
console.log('='.repeat(60));

const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;
const prefix = `${salt}_${expire_at}_`;
const testStr = prefix + String(answer);

console.log('\nInput:', testStr);
console.log('Target:', challenge);

const dsSponge = new KeccakSponge(136, 6);
dsSponge.absorb(testStr);
console.log('SHA3-256 hash:', dsSponge.hexdigest());
console.log('Node.js SHA3-256:', crypto.createHash('sha3-256').update(testStr).digest('hex'));