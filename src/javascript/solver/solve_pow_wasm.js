#!/usr/bin/env node
/**
 * DeepSeek WASM PoW Solver
 * 接收 stdin 的 JSON challenge 数据，输出 JSON 结果
 */

const fs = require('fs');
const path = require('path');

async function solvePow() {
    // 从 stdin 读取 challenge 数据
    const input = fs.readFileSync(0, 'utf-8');
    const challengeData = JSON.parse(input);

    console.error('Received challenge:', JSON.stringify(challengeData, null, 2));

    const {
        algorithm,
        challenge,
        salt,
        difficulty,
        expire_at,
        signature
    } = challengeData;

    // 加载 WASM
    const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
    const wasmBuffer = fs.readFileSync(wasmPath);

    try {
        const wasmModule = await WebAssembly.compile(wasmBuffer);

        // 创建 memory
        const memory = new WebAssembly.Memory({ initial: 17, maximum: 17 });

        const imports = {
            env: { memory: memory },
            wbindgen: { memory: memory }
        };

        const wasmInstance = await WebAssembly.instantiate(wasmModule, imports);
        const exports = wasmInstance.exports;

        console.error('WASM loaded, exports:', Object.keys(exports));

        // Helper functions
        const memBuffer = new Uint8Array(memory.buffer);

        function writeString(str, offset) {
            const encoder = new TextEncoder();
            const bytes = encoder.encode(str);
            for (let i = 0; i < bytes.length; i++) {
                memBuffer[offset + i] = bytes[i];
            }
            return bytes.length;
        }

        function readInt32(offset) {
            const view = new DataView(memory.buffer);
            return view.getInt32(offset, true);
        }

        function readFloat64(offset) {
            const view = new DataView(memory.buffer);
            return view.getFloat64(offset, true);
        }

        // 准备数据
        const prefix = `${salt}_${expire_at}_`;
        console.error('Prefix:', prefix);

        const challengePtr = 0;
        const prefixPtr = 64;
        const outputPtr = exports.__wbindgen_add_to_stack_pointer(-32);

        const challengeLen = writeString(challenge, challengePtr);
        const prefixLen = writeString(prefix, prefixPtr);

        console.error(`Challenge at ${challengePtr}, len ${challengeLen}`);
        console.error(`Prefix at ${prefixPtr}, len ${prefixLen}`);
        console.error(`Output at ${outputPtr}`);

        // 尝试调用 wasm_solve
        // 参数: (i32, i32, i32, i32, i32, f64)
        // 顺序尝试多种可能

        let answer = null;
        let duration = null;

        // 方案1: (challengePtr, challengeLen, prefixPtr, prefixLen, outputPtr, difficulty)
        try {
            exports.wasm_solve(challengePtr, challengeLen, prefixPtr, prefixLen, outputPtr, difficulty);
            answer = readInt32(outputPtr);
            duration = readFloat64(outputPtr + 8);
            console.error('Method 1 success');
        } catch (e) {
            console.error('Method 1 failed:', e.message);
        }

        // 方案2: (outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty)
        if (!answer) {
            try {
                exports.wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty);
                answer = readInt32(outputPtr);
                duration = readFloat64(outputPtr + 8);
                console.error('Method 2 success');
            } catch (e) {
                console.error('Method 2 failed:', e.message);
            }
        }

        if (answer !== null) {
            const result = { answer, duration, algorithm, challenge, salt };
            console.log(JSON.stringify(result));
        } else {
            // WASM 失败，尝试 JS fallback
            console.error('WASM failed, trying JS fallback...');

            const jsAnswer = solvePowJS(challenge, prefix, difficulty);
            if (jsAnswer !== null) {
                const result = { answer: jsAnswer, duration: 0, algorithm, challenge, salt };
                console.log(JSON.stringify(result));
            } else {
                console.log(JSON.stringify({ error: "Failed to solve PoW" }));
            }
        }

    } catch (e) {
        console.error('WASM error:', e.message);

        // JS fallback
        const prefix = `${salt}_${expire_at}_`;
        const jsAnswer = solvePowJS(challenge, prefix, difficulty);

        if (jsAnswer !== null) {
            const result = { answer: jsAnswer, duration: 0, algorithm, challenge, salt };
            console.log(JSON.stringify(result));
        } else {
            console.log(JSON.stringify({ error: "Failed to solve PoW" }));
        }
    }
}

/**
 * JS Keccak 实现 (从 Worker 代码提取)
 * 使用 SHA3-256 标准算法
 */
function solvePowJS(challengeHash, prefix, maxDifficulty) {
    console.error('JS solve starting...');
    console.error('Target:', challengeHash);
    console.error('Prefix:', prefix);
    console.error('Max:', maxDifficulty);

    // 简单的 SHA3-256 实现
    const crypto = require('crypto');

    for (let i = 0; i < maxDifficulty; i++) {
        const input = prefix + String(i);
        const hash = crypto.createHash('sha3-256').update(input).digest('hex');

        if (hash === challengeHash) {
            console.error(`Found at i=${i}`);
            return i;
        }

        if (i % 10000 === 0) {
            console.error(`Progress: ${i}/${maxDifficulty}`);
        }
    }

    console.error('Not found');
    return null;
}

solvePow().catch(err => {
    console.error('Fatal error:', err);
    console.log(JSON.stringify({ error: err.message }));
});