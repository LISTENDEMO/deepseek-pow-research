#!/usr/bin/env node
/**
 * DeepSeek PoW Solver - 正确版本
 * 可以被 Python 通过 subprocess 调用
 *
 * 输入: JSON stdin
 * 输出: JSON stdout
 */

const fs = require('fs');
const path = require('path');

// 加载 WASM
const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
const wasmBuffer = fs.readFileSync(wasmPath);

let wasmInstance = null;

async function initWasm() {
    if (wasmInstance) return wasmInstance;

    const wasmModule = await WebAssembly.compile(wasmBuffer);
    wasmInstance = await WebAssembly.instantiate(wasmModule, {});
    return wasmInstance;
}

function getMem(wasm) {
    return new Uint8Array(wasm.exports.memory.buffer);
}

function getView(wasm) {
    return new DataView(wasm.exports.memory.buffer);
}

function writeString(wasm, str) {
    const bytes = new TextEncoder().encode(str);
    const ptr = wasm.exports.__wbindgen_export_0(bytes.length, 1);
    const mem = getMem(wasm);
    for (let i = 0; i < bytes.length; i++) {
        mem[ptr + i] = bytes[i];
    }
    return { ptr, len: bytes.length };
}

function readHash(wasm, ptr) {
    const mem = getMem(wasm);
    const bytes = mem.slice(ptr, ptr + 32);
    return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * 计算 DeepSeek hash
 * @param {string} input - 输入字符串 (prefix + answer)
 * @returns {string} - 32 bytes hex hash
 */
async function deepseekHash(input) {
    const wasm = await initWasm();

    const { ptr: inputPtr, len: inputLen } = writeString(wasm, input);
    const hashPtr = wasm.exports.__wbindgen_add_to_stack_pointer(-32);

    wasm.exports.wasm_deepseek_hash_v1(hashPtr, inputPtr, inputLen);

    return readHash(wasm, hashPtr);
}

/**
 * 解决 PoW
 * @param {string} challenge - 目标 hash
 * @param {string} prefix - prefix (salt_expire_at_)
 * @param {number} difficulty - 最大搜索范围
 * @returns {number|null} - 答案或 null
 */
async function solvePow(challenge, prefix, difficulty) {
    const wasm = await initWasm();

    const { ptr: challengePtr, len: challengeLen } = writeString(wasm, challenge);
    const { ptr: prefixPtr, len: prefixLen } = writeString(wasm, prefix);

    // 输出空间: int32 + float64 = 16 bytes
    const outputPtr = wasm.exports.__wbindgen_add_to_stack_pointer(-16);

    wasm.exports.wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty);

    const view = getView(wasm);
    const status = view.getInt32(outputPtr + 0, true);
    const answer = view.getFloat64(outputPtr + 8, true);

    // status = 0 表示未找到，status > 0 表示找到
    if (status === 0) {
        return null;
    }
    return Math.floor(answer);
}

// 主程序
async function main() {
    // 从 stdin 读取输入
    const input = fs.readFileSync(0, 'utf-8');
    let data;

    try {
        data = JSON.parse(input);
    } catch (e) {
        console.error('Invalid JSON input:', e.message);
        console.log(JSON.stringify({ error: 'Invalid JSON' }));
        return;
    }

    console.error('Received:', JSON.stringify(data));

    const { challenge, salt, expire_at, difficulty, action } = data;

    if (action === 'hash') {
        // 单独计算 hash
        const inputStr = data.input;
        const hash = await deepseekHash(inputStr);
        console.log(JSON.stringify({ hash }));
        return;
    }

    if (action === 'verify') {
        // 验证特定答案
        const answer = data.answer;
        const prefix = `${salt}_${expire_at}_`;
        const testInput = prefix + String(answer);
        const hash = await deepseekHash(testInput);
        const match = hash === challenge;
        console.log(JSON.stringify({ hash, challenge, match, answer }));
        return;
    }

    // 默认: 解决 PoW
    const prefix = `${salt}_${expire_at}_`;
    console.error(`Solving PoW: prefix="${prefix}", difficulty=${difficulty}`);

    const answer = await solvePow(challenge, prefix, difficulty);

    if (answer !== null) {
        console.log(JSON.stringify({
            success: true,
            answer: answer,
            algorithm: 'DeepSeekHashV1',
            challenge: challenge,
            salt: salt
        }));
    } else {
        console.log(JSON.stringify({
            success: false,
            error: 'No solution found within difficulty range'
        }));
    }
}

main().catch(err => {
    console.error('Error:', err);
    console.log(JSON.stringify({ error: err.message }));
});