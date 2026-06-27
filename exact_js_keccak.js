#!/usr/bin/env node
/**
 * Extract exact Keccak implementation from DeepSeek Worker
 */

// Round constants as uint32 pairs (from JS: d array)
const RC_PAIRS = [
    [0, 1], [0, 32898], [0x80000000, 32906], [0x80000000, 0x80008000],
    [0, 32907], [0, 0x80000001], [0x80000000, 0x80008081], [0x80000000, 32777],
    [0, 138], [0, 136], [0, 0x80008009], [0, 0x8000000a],
    [0, 0x8000808b], [0x80000000, 139], [0x80000000, 32905], [0x80000000, 32771],
    [0x80000000, 32770], [0x80000000, 128], [0, 32778], [0x80000000, 0x8000000a],
    [0x80000000, 0x80008081], [0x80000000, 32896], [0, 0x80000001], [0x80000000, 0x80008008]
];

// Lane copy helper (from JS: g function)
function copyLane(src, srcIdx, dst, dstIdx) {
    dst[dstIdx] = src[srcIdx];
    dst[dstIdx + 1] = src[srcIdx + 1];
}

// Chi function (from JS: y function)
function chi(A) {
    const C = new Uint32Array(10);
    for (let x = 0; x < 25; x += 5) {
        // Copy A[x..x+4] to C
        for (let n = 0; n < 5; n++) {
            copyLane(A, x + n, C, n);
        }
        // Apply chi
        for (let n = 0; n < 5; n++) {
            const idx = (x + n) * 2;
            const next1 = ((n + 1) % 5) * 2;
            const next2 = ((n + 2) % 5) * 2;
            A[idx] ^= (~C[next1] & C[next2]);
            A[idx + 1] ^= (~C[next1 + 1] & C[next2 + 1]);
        }
    }
}

// Rho+Pi function (from JS: E function)
// v = lane indices, w = rotation amounts
const v = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1];
const w = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44];

function rhoPi(A) {
    const C = new Uint32Array(10);
    const W = new Uint32Array(2);

    // Copy lane 1 to W
    copyLane(A, 2, W, 0);

    for (let i = 0; i < 24; i++) {
        const laneIdx = v[i];
        const rot = w[i];

        // Copy A[laneIdx] to C[0..1]
        copyLane(A, laneIdx * 2, C, 0);

        // Rotate C and store in W
        if (rot < 32) {
            W[0] = (C[0] << rot) | (C[1] >>> (32 - rot));
            W[1] = (C[1] << rot) | (C[0] >>> (32 - rot));
        } else {
            const r = rot - 32;
            W[0] = (C[1] << r) | (C[0] >>> (32 - r));
            W[1] = (C[0] << r) | (C[1] >>> (32 - r));
        }

        // Copy W to A[laneIdx]
        copyLane(W, 0, A, laneIdx * 2);

        // Copy C to W (for next iteration)
        copyLane(C, 0, W, 0);
    }
}

// Theta+D function (from JS: B function)
function thetaD(A) {
    const C = new Uint32Array(10);
    const D = new Uint32Array(10);
    const W = new Uint32Array(2);

    // Compute column parity C
    for (let x = 0; x < 5; x++) {
        const n = 2 * x;
        C[n] = A[n] ^ A[(x+5)*2] ^ A[(x+10)*2] ^ A[(x+15)*2] ^ A[(x+20)*2];
        C[n+1] = A[n+1] ^ A[(x+5)*2+1] ^ A[(x+10)*2+1] ^ A[(x+15)*2+1] ^ A[(x+20)*2+1];
    }

    // Compute D and apply
    for (let x = 0; x < 5; x++) {
        // C[(x+1)%5] rol 1
        const next = (x + 1) % 5;
        copyLane(C, next * 2, W, 0);
        // Rotate left by 1 bit
        const t0 = W[1];
        const t1 = W[0];
        W[0] = (t0 << 1) | (t1 >>> 31);
        W[1] = (t1 << 1) | (t0 >>> 31);

        // D[x] = C[(x+4)%5] ^ W
        const prev = (x + 4) % 5;
        D[2*x] = C[2*prev] ^ W[0];
        D[2*x+1] = C[2*prev+1] ^ W[1];

        // Apply D to column x
        for (let y = 0; y < 25; y += 5) {
            A[(y + x) * 2] ^= D[2*x];
            A[(y + x) * 2 + 1] ^= D[2*x + 1];
        }
    }
}

// Iota function (from JS: b function)
function iota(A, round) {
    A[0] ^= RC_PAIRS[round][0];
    A[1] ^= RC_PAIRS[round][1];
}

// Keccak permutation (from JS: this.keccak)
function keccakF(A) {
    const C = new Uint32Array(10);
    const D = new Uint32Array(10);
    const W = new Uint32Array(2);

    for (let i = 1; i < 24; i++) {
        thetaD(A);
        rhoPi(A);
        chi(A);
        iota(A, i);
    }
}

// Absorb bytes (from JS: I function)
function absorbBytes(bytes, state) {
    for (let r = 0; r < bytes.length; r += 8) {
        const n = r / 4;  // lane pair index
        if (r + 8 <= bytes.length) {
            state[n] ^= (bytes[r+7] << 24) | (bytes[r+6] << 16) | (bytes[r+5] << 8) | bytes[r+4];
            state[n+1] ^= (bytes[r+3] << 24) | (bytes[r+2] << 16) | (bytes[r+1] << 8) | bytes[r];
        }
    }
}

// Squeeze bytes (from JS: A function)
function squeezeBytes(state, length) {
    const result = Buffer.alloc(length);
    for (let r = 0; r < length; r += 8) {
        const n = r / 4;
        result[r] = state[n+1] & 0xff;
        result[r+1] = (state[n+1] >>> 8) & 0xff;
        result[r+2] = (state[n+1] >>> 16) & 0xff;
        result[r+3] = (state[n+1] >>> 24) & 0xff;
        result[r+4] = state[n] & 0xff;
        result[r+5] = (state[n] >>> 8) & 0xff;
        result[r+6] = (state[n] >>> 16) & 0xff;
        result[r+7] = (state[n] >>> 24) & 0xff;
    }
    return result.slice(0, length);
}

// DeepSeek sponge
class DeepSeekSponge {
    constructor(capacityBits = 256) {
        this.rate = 200 - capacityBits / 4;  // bytes
        this.state = new Uint32Array(50);  // 25 lanes as uint32 pairs
        this.queue = Buffer.alloc(this.rate);
        this.queueOffset = 0;
        this.padding = 6;
    }

    absorb(data) {
        if (typeof data === 'string') {
            data = Buffer.from(data, 'utf8');
        }
        for (let i = 0; i < data.length; i++) {
            this.queue[this.queueOffset++] = data[i];
            if (this.queueOffset >= this.rate) {
                absorbBytes(this.queue, this.state);
                keccakF(this.state);
                this.queueOffset = 0;
            }
        }
        return this;
    }

    squeeze(outputLen = 32) {
        // Padding
        this.queue[this.queueOffset] |= this.padding;
        this.queue[this.rate - 1] |= 0x80;

        // Final absorb
        absorbBytes(this.queue, this.state);
        keccakF(this.state);

        // Squeeze
        const result = Buffer.alloc(outputLen);
        let offset = 0;
        while (offset < outputLen) {
            const chunkLen = Math.min(this.rate, outputLen - offset);
            const chunk = squeezeBytes(this.state, chunkLen);
            chunk.copy(result, offset);
            offset += chunkLen;
            if (offset < outputLen) {
                keccakF(this.state);
            }
        }
        return result;
    }

    hexdigest() {
        return this.squeeze(32).toString('hex');
    }

    copy() {
        const newSponge = new DeepSeekSponge();
        newSponge.state = new Uint32Array(this.state);
        newSponge.queue = Buffer.from(this.queue);
        newSponge.queueOffset = this.queueOffset;
        return newSponge;
    }
}

// Test
console.log('=' .repeat(60));
console.log('Exact JS Keccak Implementation from Worker');
console.log('=' .repeat(60));

const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;

const prefix = `${salt}_${expire_at}_`;

console.log('\nTest 1:');
console.log('  Challenge:', challenge);
console.log('  Prefix:', prefix);
console.log('  Answer:', answer);

const sponge = new DeepSeekSponge(256);
sponge.absorb(prefix);
sponge.absorb(String(answer));
const hash = sponge.hexdigest();
console.log('  Hash:', hash);
console.log('  Match:', hash === challenge);

if (hash !== challenge) {
    console.log('\n  Searching...');
    const startSponge = new DeepSeekSponge(256);
    startSponge.absorb(prefix);

    for (let i = 0; i < 20000; i++) {
        const testSponge = startSponge.copy();
        testSponge.absorb(String(i));
        if (testSponge.hexdigest() === challenge) {
            console.log('  *** FOUND at', i, '***');
            break;
        }
    }
}

// Compare with standard SHA3-256
console.log('\n' + '=' .repeat(60));
console.log('Comparison with standard SHA3-256:');
const crypto = require('crypto');
const testStr = prefix + String(answer);
console.log('  Input:', testStr);
console.log('  SHA3-256:', crypto.createHash('sha3-256').update(testStr).digest('hex'));
console.log('  DeepSeek:', hash);