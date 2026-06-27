// 使用 WASM 解决 PoW - 正确的 wbindgen 方式
const fs = require('fs');
const path = require('path');

async function solvePow() {
    const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
    const wasmBuffer = fs.readFileSync(wasmPath);

    // 创建 wbindgen imports
    const memory = new WebAssembly.Memory({ initial: 17, maximum: 17 });

    // wbindgen 需要的基本 imports
    const imports = {
        wbindgen: {
            memory: memory,
        },
        env: {
            memory: memory,
        }
    };

    console.log('Loading WASM...');
    const wasmModule = await WebAssembly.compile(wasmBuffer);
    const wasmInstance = await WebAssembly.instantiate(wasmModule, imports);

    const exports = wasmInstance.exports;
    console.log('Exports:', Object.keys(exports));

    const memoryBuffer = new Uint8Array(memory.buffer);

    // Helper functions
    function writeString(str, offset) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(str);
        for (let i = 0; i < bytes.length; i++) {
            memoryBuffer[offset + i] = bytes[i];
        }
        return bytes.length;
    }

    function readBytes(offset, length) {
        return memoryBuffer.slice(offset, offset + length);
    }

    function readInt32(offset) {
        const view = new DataView(memory.buffer);
        return view.getInt32(offset, true);
    }

    function readFloat64(offset) {
        const view = new DataView(memory.buffer);
        return view.getFloat64(offset, true);
    }

    // 测试 challenge
    const challenge = "6f03c2942e31a4c67fea7c3ee3184bb22bc32e9da51da1984f1a7fbb675c8531";
    const salt = "e35f5bc86e49d6101fa6";
    const expire_at = 1776156337056;
    const difficulty = 144000;

    const prefix = `${salt}_${expire_at}_`;

    console.log('\nChallenge:', challenge.substring(0, 30) + '...');
    console.log('Prefix:', prefix);
    console.log('Difficulty:', difficulty);

    // 分配内存
    const challengePtr = 0;
    const prefixPtr = 64;
    const outputPtr = 128;

    writeString(challenge, challengePtr);
    writeString(prefix, prefixPtr);

    console.log('\nChallenge at', challengePtr, ', len', challenge.length);
    console.log('Prefix at', prefixPtr, ', len', prefix.length);

    // 获取栈指针并分配输出空间
    const stackPtr = exports.__wbindgen_add_to_stack_pointer(-32);
    console.log('Stack pointer:', stackPtr);

    // 尝试不同的参数顺序
    console.log('\nTrying wasm_solve...');

    // 方案1: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)
    try {
        console.log('Order 1: (challenge_ptr, challenge_len, prefix_ptr, prefix_len, output_ptr, difficulty)');
        exports.wasm_solve(challengePtr, challenge.length, prefixPtr, prefix.length, stackPtr, difficulty);

        const answer = readInt32(stackPtr);
        const duration = readFloat64(stackPtr + 8);

        console.log('Result: answer=' + answer + ', duration=' + duration + 'ms');
        return { answer, duration };
    } catch (e) {
        console.log('Order 1 error:', e.message);
    }

    // 方案2: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)
    try {
        console.log('\nOrder 2: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)');
        exports.wasm_solve(stackPtr, challengePtr, challenge.length, prefixPtr, prefix.length, difficulty);

        const answer = readInt32(stackPtr);
        const duration = readFloat64(stackPtr + 8);

        console.log('Result: answer=' + answer + ', duration=' + duration + 'ms');
        return { answer, duration };
    } catch (e) {
        console.log('Order 2 error:', e.message);
    }

    // 方案3: 其他顺序
    try {
        console.log('\nOrder 3: (challengePtr, prefixPtr, stackPtr, challenge.length, prefix.length, difficulty)');
        exports.wasm_solve(challengePtr, prefixPtr, stackPtr, challenge.length, prefix.length, difficulty);

        const answer = readInt32(stackPtr);
        const duration = readFloat64(stackPtr + 8);

        console.log('Result: answer=' + answer + ', duration=' + duration + 'ms');
        return { answer, duration };
    } catch (e) {
        console.log('Order 3 error:', e.message);
    }

    // 查看 WASM 导出的函数签名（通过分析）
    console.log('\n\nAnalyzing function behavior...');

    // 尝试 wasm_deepseek_hash_v1
    console.log('\nTrying wasm_deepseek_hash_v1...');
    try {
        const testPrefix = 'test_';
        const testAnswer = 12345;

        const testPrefixPtr = 200;
        writeString(testPrefix, testPrefixPtr);

        console.log('Test: prefix="' + testPrefix + '", answer=' + testAnswer);

        // 参数: (i32, i32, i32)
        // 可能: (prefix_ptr, prefix_len, answer)
        exports.wasm_deepseek_hash_v1(testPrefixPtr, testPrefix.length, testAnswer);

        // 结果可能在栈指针处
        const hashBytes = readBytes(stackPtr, 32);
        console.log('Hash output:', hashBytes.reduce((s, b) => s + b.toString(16).padStart(2, '0'), ''));
    } catch (e) {
        console.log('Hash error:', e.message);
    }

    console.log('\n\nMemory inspection:');
    console.log('Memory at 0-64:', readBytes(0, 64).reduce((s, b) => s + b.toString(16).padStart(2, '0'), '').substring(0, 40) + '...');
    console.log('Memory at stack:', readBytes(stackPtr, 64).reduce((s, b) => s + b.toString(16).padStart(2, '0'), '').substring(0, 40) + '...');
}

solvePow().catch(console.error);