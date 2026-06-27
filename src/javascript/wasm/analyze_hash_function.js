#!/usr/bin/env node
/**
 * 分析 wasm_deepseek_hash_v1 的实际行为
 */

const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
const wasmBuffer = fs.readFileSync(wasmPath);

async function analyzeHashFunction() {
    const wasmModule = await WebAssembly.compile(wasmBuffer);
    const instance = await WebAssembly.instantiate(wasmModule, {});
    const wasm = instance.exports;

    let getMem = () => new Uint8Array(wasm.memory.buffer);
    let getView = () => new DataView(wasm.memory.buffer);

    function writeString(str) {
        const bytes = new TextEncoder().encode(str);
        const ptr = wasm.__wbindgen_export_0(bytes.length, 1);
        const mem = getMem();
        for (let i = 0; i < bytes.length; i++) {
            mem[ptr + i] = bytes[i];
        }
        return { ptr, len: bytes.length };
    }

    const testInput = '811e05c93d1b71993710_1776153216159_69992';

    console.log('测试 wasm_deepseek_hash_v1...');
    console.log('Input:', testInput);

    const { ptr: inputPtr, len: inputLen } = writeString(testInput);
    console.log('Input ptr:', inputPtr, 'len:', inputLen);

    // 尝试不同的调用方式

    // 方式 1: 提供 output pointer
    console.log('\n方式 1: 提供 output pointer');
    const outputPtr1 = wasm.__wbindgen_add_to_stack_pointer(-32);
    console.log('Output ptr:', outputPtr1);

    // 清零
    const mem = getMem();
    for (let i = 0; i < 32; i++) mem[outputPtr1 + i] = 0;

    // 调用
    wasm.wasm_deepseek_hash_v1(outputPtr1, inputPtr, inputLen);

    // 读取结果
    console.log('Output bytes:', mem.slice(outputPtr1, outputPtr1 + 32).map(b => b.toString(16).padStart(2, '0')).join(' '));

    // 检查返回值 - 注意 WASM 函数可能有返回值!
    // 让我看看函数签名

    console.log('\n检查函数签名...');
    const exports = WebAssembly.Module.exports(wasmModule);
    exports.forEach(exp => {
        console.log('  Export:', exp.name, 'kind:', exp.kind);
        if (exp.kind === 'function') {
            console.log('    (需要检查具体签名)');
        }
    });

    // 方式 2: 不提供 output pointer，让函数返回
    console.log('\n方式 2: 检查是否函数返回值是 hash pointer');

    // wasm_deepseek_hash_v1 可能只接受 2 个参数 (input_ptr, input_len)
    // 并返回一个 pointer
    try {
        // 尝试只用 2 个参数
        const result = wasm.wasm_deepseek_hash_v1(inputPtr, inputLen);
        console.log('Return value:', result);

        if (typeof result === 'number') {
            // 读取返回指针处的 hash
            const hashBytes = mem.slice(result, result + 32);
            const hashHex = Array.from(hashBytes).map(b => b.toString(16).padStart(2, '0')).join('');
            console.log('Hash at returned ptr:', hashHex);
            console.log('Expected:', 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd');
            console.log('Match:', hashHex === 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd');
        }
    } catch (e) {
        console.log('Error with 2 params:', e.message);
    }

    // 方式 3: 检查内存中是否有 hash
    console.log('\n方式 3: 搜索内存中的正确 hash');
    const expectedHash = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
    const expectedBytes = [];
    for (let i = 0; i < 64; i += 2) {
        expectedBytes.push(parseInt(expectedHash.slice(i, i+2), 16));
    }

    console.log('Expected hash bytes:', expectedBytes.map(b => b.toString(16).padStart(2, '0')).join(' '));

    // 搜索内存
    const memFull = getMem();
    for (let i = 0; i < memFull.length - 32; i++) {
        let match = true;
        for (let j = 0; j < 32; j++) {
            if (memFull[i + j] !== expectedBytes[j]) {
                match = false;
                break;
            }
        }
        if (match) {
            console.log('Found expected hash at offset:', i);
            break;
        }
    }
}

analyzeHashFunction().catch(console.error);