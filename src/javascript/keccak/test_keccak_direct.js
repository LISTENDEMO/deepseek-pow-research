#!/usr/bin/env node
/**
 * DeepSeek PoW Solver - Direct JS Keccak implementation from Worker
 * 使用 Worker 中的确切 Keccak 实现
 */

// Keccak round constants as uint32 pairs
const RC = [
    [0x00000001, 0x00000000], [0x00008082, 0x00000000], [0x0000808a, 0x80000000],
    [0x80008000, 0x80000000], [0x0000808b, 0x00000000], [0x80000001, 0x00000000],
    [0x80008081, 0x80000000], [0x00008009, 0x80000000], [0x0000008a, 0x00000000],
    [0x00000088, 0x00000000], [0x80008009, 0x00000000], [0x8000000a, 0x00000000],
    [0x8000808b, 0x00000000], [0x0000008b, 0x80000000], [0x00008089, 0x80000000],
    [0x00008003, 0x80000000], [0x00008002, 0x80000000], [0x00000080, 0x80000000],
    [0x0000800a, 0x00000000], [0x8000000a, 0x80000000], [0x80008081, 0x80000000],
    [0x00008080, 0x80000000], [0x80000001, 0x00000000], [0x80008008, 0x80000000],
];

// Rotation offsets
const RHO_OFFSETS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 2, 62],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14]
];

// Pi permutation map
const PI_MAP = [
    [0, 6, 12, 18, 24],
    [1, 7, 13, 19, 25],
    [2, 8, 14, 20, 26],
    [3, 9, 15, 21, 27],
    [4, 10, 16, 22, 28]
];

// Helper to copy lane
function copyLane(src, srcIdx, dst, dstIdx) {
    dst[dstIdx] = src[srcIdx];
    dst[dstIdx + 1] = src[srcIdx + 1];
}

// Rotate 64-bit (stored as 2 uint32s)
function rol64pair(low, high, n) {
    if (n === 0) return [low, high];
    if (n < 32) {
        return [
            ((low << n) | (high >>> (32 - n))) >>> 0,
            ((high << n) | (low >>> (32 - n))) >>> 0
        ];
    } else {
        n -= 32;
        return [
            ((high << n) | (low >>> (32 - n))) >>> 0,
            ((low << n) | (high >>> (32 - n))) >>> 0
        ];
    }
}

// Absorb bytes into state (JS's special ordering)
function absorbBytes(data, state) {
    for (let r = 0; r < data.length; r += 8) {
        const n = r / 4;
        if (r + 8 <= data.length) {
            // state[n] = bytes[7..4] in BE order
            state[n] ^= (data[r+7] << 24) | (data[r+6] << 16) | (data[r+5] << 8) | data[r+4];
            // state[n+1] = bytes[3..0] in BE order
            state[n+1] ^= (data[r+3] << 24) | (data[r+2] << 16) | (data[r+1] << 8) | data[r];
        } else {
            // Handle partial block with padding
            const remaining = data.slice(r);
            const padded = Buffer.alloc(8);
            for (let i = 0; i < remaining.length; i++) padded[i] = remaining[i];
            state[n] ^= (padded[7] << 24) | (padded[6] << 16) | (padded[5] << 8) | padded[4];
            state[n+1] ^= (padded[3] << 24) | (padded[2] << 16) | (padded[1] << 8) | padded[0];
        }
    }
}

// Squeeze bytes from state
function squeezeBytes(state, length) {
    const result = Buffer.alloc(length);
    for (let r = 0; r < length; r += 8) {
        const n = r / 4;
        // bytes[0..3] from state[n+1]
        result[r] = state[n+1] & 0xFF;
        result[r+1] = (state[n+1] >>> 8) & 0xFF;
        result[r+2] = (state[n+1] >>> 16) & 0xFF;
        result[r+3] = (state[n+1] >>> 24) & 0xFF;
        // bytes[4..7] from state[n]
        result[r+4] = state[n] & 0xFF;
        result[r+5] = (state[n] >>> 8) & 0xFF;
        result[r+6] = (state[n] >>> 16) & 0xFF;
        result[r+7] = (state[n] >>> 24) & 0xFF;
    }
    return result.slice(0, length);
}

// Keccak-f[1600] permutation
function keccakF(state) {
    const C = new Uint32Array(10);
    const D = new Uint32Array(10);
    const W = new Uint32Array(2);
    const B = new Uint32Array(50);

    for (let round = 0; round < 24; round++) {
        // Theta - compute column parity C
        for (let x = 0; x < 5; x++) {
            C[2*x] = state[2*x] ^ state[2*(x+5)] ^ state[2*(x+10)] ^ state[2*(x+15)] ^ state[2*(x+20)];
            C[2*x+1] = state[2*x+1] ^ state[2*(x+5)+1] ^ state[2*(x+10)+1] ^ state[2*(x+15)+1] ^ state[2*(x+20)+1];
        }

        // Theta - compute D and apply
        for (let x = 0; x < 5; x++) {
            const prev = (x + 4) % 5;
            const next = (x + 1) % 5;
            // C[prev] rol 1
            W[0] = C[2*prev + 1];
            W[1] = C[2*prev];
            // D[x] = C[prev] rol 1 XOR C[next]
            D[2*x] = W[0] ^ C[2*next];
            D[2*x+1] = W[1] ^ C[2*next+1];

            // Apply D to column x
            for (let y = 0; y < 5; y++) {
                state[2*(y*5 + x)] ^= D[2*x];
                state[2*(y*5 + x) + 1] ^= D[2*x+1];
            }
        }

        // Rho and Pi
        for (let x = 0; x < 5; x++) {
            for (let y = 0; y < 5; y++) {
                const srcLane = y * 5 + x;
                const rot = RHO_OFFSETS[x][y];
                const newX = y;
                const newY = (2*x + 3*y) % 5;
                const dstLane = newX * 5 + newY;

                const [low, high] = rol64pair(state[2*srcLane], state[2*srcLane+1], rot);
                B[2*dstLane] = low;
                B[2*dstLane+1] = high;
            }
        }

        // Chi
        for (let x = 0; x < 5; x++) {
            for (let y = 0; y < 5; y++) {
                const lane = x * 5 + y;
                const next1 = ((x + 1) % 5) * 5 + y;
                const next2 = ((x + 2) % 5) * 5 + y;

                state[2*lane] = B[2*lane] ^ ((~B[2*next1] & 0xFFFFFFFF) & B[2*next2]);
                state[2*lane+1] = B[2*lane+1] ^ ((~B[2*next1+1] & 0xFFFFFFFF) & B[2*next2+1]);
            }
        }

        // Iota
        state[0] ^= RC[round][0];
        state[1] ^= RC[round][1];
    }
}

// DeepSeek Keccak sponge
class DeepSeekSponge {
    constructor(capacity = 256) {
        this.capacity = capacity;
        this.rate = 200 - capacity / 4;  // bytes
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

        // Squeeze output
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
        const newSponge = new DeepSeekSponge(this.capacity);
        newSponge.state = new Uint32Array(this.state);
        newSponge.queue = Buffer.from(this.queue);
        newSponge.queueOffset = this.queueOffset;
        return newSponge;
    }
}

// Solve PoW
function solvePow(challenge, prefix, difficulty) {
    const sponge = new DeepSeekSponge(256);
    sponge.absorb(prefix);

    for (let i = 0; i < difficulty; i++) {
        const testSponge = sponge.copy();
        testSponge.absorb(String(i));
        const hash = testSponge.hexdigest();

        if (hash === challenge) {
            return i;
        }
    }
    return null;
}

// Test with user data
console.log('='.repeat(60));
console.log('DeepSeek PoW Verification - Direct JS Implementation');
console.log('='.repeat(60));

// Test 1
const challenge1 = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt1 = '811e05c93d1b71993710';
const expire_at1 = 1776153216159;
const answer1 = 69992;

const prefix1 = `${salt1}_${expire_at1}_`;

console.log('\nTest 1:');
console.log('  Challenge:', challenge1);
console.log('  Salt:', salt1);
console.log('  expire_at:', expire_at1);
console.log('  Expected answer:', answer1);
console.log('  Prefix:', prefix1);

const sponge1 = new DeepSeekSponge(256);
sponge1.absorb(prefix1);
sponge1.absorb(String(answer1));
const hash1 = sponge1.hexdigest();
console.log('  Hash:', hash1);
console.log('  Match:', hash1 === challenge1);

if (hash1 !== challenge1) {
    console.log('\n  Searching for correct answer...');
    const start = Date.now();
    const found = solvePow(challenge1, prefix1, 144000);
    const elapsed = (Date.now() - start) / 1000;
    console.log(`  Result: ${found !== null ? found : 'Not found'}`);
    console.log(`  Time: ${elapsed}s`);
}

// Test 2
const challenge2 = '252f029a65d33fade32803d2f3bf23363584bda3be0e3110261659f9208107c1';
const salt2 = 'a9171b4026f92b32024f';
const answer2 = 83094;

console.log('\n' + '='.repeat(60));
console.log('Test 2:');
console.log('  Challenge:', challenge2);
console.log('  Salt:', salt2);
console.log('  Answer:', answer2);
console.log('  Searching expire_at...');

const start2 = Date.now();
for (let exp = 1776155800000; exp < 1776156500000; exp += 100) {
    const prefix = `${salt2}_${exp}_`;
    const sponge = new DeepSeekSponge(256);
    sponge.absorb(prefix);
    sponge.absorb(String(answer2));
    if (sponge.hexdigest() === challenge2) {
        console.log(`  *** FOUND! expire_at = ${exp} ***`);
        break;
    }
}
console.log(`  Search time: ${(Date.now() - start2) / 1000}s`);