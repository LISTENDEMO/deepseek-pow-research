// 直接使用 DeepSeek WASM 计算 hash
const fs = require('fs');
const path = require('path');

async function testWasmHash() {
    const wasmBuffer = fs.readFileSync(path.join(__dirname, 'sha3_wasm.wasm'));

    // 加载 WASM
    const wasmModule = await WebAssembly.compile(wasmBuffer);

    // 创建 memory (足够大)
    const memory = new WebAssembly.Memory({ initial: 256, maximum: 256 });
    const memView = new Uint8Array(memory.buffer);

    // WASM 需要一些 imports
    const imports = {
        env: {
            memory: memory,
        }
    };

    const wasmInstance = await WebAssembly.instantiate(wasmModule, imports);
    const exports = wasmInstance.exports;

    console.log('WASM loaded successfully');
    console.log('Exports:', Object.keys(exports));

    // 编码字符串到 memory
    function encodeString(str, ptr) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(str);
        for (let i = 0; i < bytes.length; i++) {
            memView[ptr + i] = bytes[i];
        }
        return bytes.length;
    }

    // 从 memory 读取字符串
    function readString(ptr, length) {
        const decoder = new TextDecoder();
        return decoder.decode(memView.slice(ptr, ptr + length));
    }

    // 测试 wasm_deepseek_hash_v1
    // 参数可能是 (input_ptr, input_len, output_ptr)
    // 或者返回 hash 值

    // 先测试 wasm_solve 函数的参数
    // 从 DeepSeek 代码看: wasm_solve(a, u, c, l, p, r)
    // a = output pointer (16 bytes for result + duration)
    // u = challenge ptr
    // c = challenge length
    // l = prefix ptr
    // p = prefix length
    // r = difficulty

    // 测试输入
    const prefix = '597ae3e54605d43c1dd6_1776155801356_';
    const challenge = 'edfeafeb9893d67e42d763740c36d8f6eb4ab9af9e45cd40b79a13c4a2eefb44';
    const difficulty = 144000;

    // 分配内存
    const challengePtr = 0;
    const prefixPtr = 64;
    const outputPtr = 128;

    encodeString(challenge, challengePtr);
    encodeString(prefix, prefixPtr);

    console.log('\nInput:');
    console.log('  Challenge:', readString(challengePtr, challenge.length));
    console.log('  Prefix:', readString(prefixPtr, prefix.length));
    console.log('  Difficulty:', difficulty);

    // 调用 wasm_solve
    try {
        const challengeLen = challenge.length;
        const prefixLen = prefix.length;

        // wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty)
        // 或者不同顺序的参数

        // 尝试不同参数顺序
        console.log('\nTrying wasm_solve...');

        // 可能的参数顺序:
        // 1. wasm_solve(a,u,c,l,p,r) - a=output, u=challenge_ptr, c=challenge_len, l=prefix_ptr, p=prefix_len, r=difficulty
        const result = exports.wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty);

        console.log('wasm_solve returned:', result);

        // 读取 output
        // output 格式: [result (4 bytes?), duration (8 bytes?)]
        const outputView = new DataView(memory.buffer);
        const answer = outputView.getInt32(outputPtr, true);  // little endian
        const duration = outputView.getFloat64(outputPtr + 8, true);

        console.log('Answer:', answer);
        console.log('Duration:', duration);

        // 验证 hash
        if (answer >= 0) {
            const testHash = computeHash(prefix, answer);
            console.log('Computed hash:', testHash);
            console.log('Matches:', testHash === challenge);
        }

    } catch (e) {
        console.error('wasm_solve error:', e.message);
        console.log('\nFalling back to JS...');
    }
}

// JS hash 计算 (用于验证)
function computeHash(prefix, answer) {
    const { keccak256 } = require('js-sha3');
    return keccak256(prefix + String(answer));
}

testWasmHash().catch(console.error);