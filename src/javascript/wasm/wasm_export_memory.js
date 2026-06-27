#!/usr/bin/env node
/**
 * 使用 WASM 导出的 memory，而不是导入
 */

const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
const wasmBuffer = fs.readFileSync(wasmPath);

async function runWithExportedMemory() {
    const wasmModule = await WebAssembly.compile(wasmBuffer);

    // WASM 没有 imports! (exports memory 自己)
    const importObject = {};

    // 实例化
    const instance = await WebAssembly.instantiate(wasmModule, importObject);
    const wasmExports = instance.exports;

    console.log('WASM 实例化成功!');
    console.log('Exports:', Object.keys(wasmExports));

    // 使用 WASM 导出的 memory
    const memory = wasmExports.memory;
    const uint8Mem = new Uint8Array(memory.buffer);
    const dataView = new DataView(memory.buffer);

    console.log('\nMemory info:');
    console.log('  Buffer size:', memory.buffer.byteLength);
    console.log('  Initial pages:', memory.buffer.byteLength / 65536);

    // 使用 WASM 导出的栈指针函数
    const addToStackPointer = wasmExports.__wbindgen_add_to_stack_pointer;
    const malloc = wasmExports.__wbindgen_export_0;
    const realloc = wasmExports.__wbindgen_export_1;

    // 先看看内存初始状态
    console.log('\nInitial memory (first 100 bytes):');
    console.log('  ', uint8Mem.slice(0, 100).map(b => b.toString(16).padStart(2, '0')).join(' '));

    // 检查 WASM 是否有预加载的数据 (从 data section)
    // 搜索可能的 round constants 或其他特征数据
    console.log('\nSearching for Keccak round constants in memory...');
    const rcPattern = [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00];  // RC[0] = 1
    for (let i = 0; i < memory.buffer.byteLength - 8; i++) {
        let match = true;
        for (let j = 0; j < 8; j++) {
            if (uint8Mem[i + j] !== rcPattern[j]) {
                match = false;
                break;
            }
        }
        if (match) {
            console.log(`  Found RC[0] pattern at offset ${i}`);
            // 打印周围的数据
            const context = uint8Mem.slice(i - 16, i + 200);
            console.log('  Context:', context.map(b => b.toString(16).padStart(2, '0')).join(' '));
            break;
        }
    }

    // 测试数据
    const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
    const prefix = '811e05c93d1b71993710_1776153216159_';

    // 写入字符串
    function writeString(str, offset) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(str);
        for (let i = 0; i < bytes.length; i++) {
            uint8Mem[offset + i] = bytes[i];
        }
        return bytes.length;
    }

    // 使用 WASM 的 malloc 分配内存
    const challengePtr = malloc(64, 1);  // 分配 64 bytes for challenge
    const challengeLen = writeString(challenge, challengePtr);

    const prefixPtr = malloc(40, 1);  // 分配 40 bytes for prefix
    const prefixLen = writeString(prefix, prefixPtr);

    // 输出空间
    const outputPtr = addToStackPointer(-32);  // 在栈上分配 32 bytes

    console.log('\n内存布局:');
    console.log(`  challenge: ptr=${challengePtr}, len=${challengeLen}`);
    console.log(`  prefix: ptr=${prefixPtr}, len=${prefixLen}`);
    console.log(`  output: ptr=${outputPtr}`);

    // 验证写入
    console.log('\n验证写入:');
    const challengeBytes = uint8Mem.slice(challengePtr, challengePtr + challengeLen);
    console.log('  Challenge in memory:', new TextDecoder().decode(challengeBytes));

    const prefixBytes = uint8Mem.slice(prefixPtr, prefixPtr + prefixLen);
    console.log('  Prefix in memory:', new TextDecoder().decode(prefixBytes));

    // 尝试调用 wasm_solve
    console.log('\n调用 wasm_solve...');
    try {
        wasmExports.wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, 144000);

        const result = dataView.getInt32(outputPtr, true);
        const duration = dataView.getFloat64(outputPtr + 8, true);

        console.log('  Result:', result);
        console.log('  Duration:', duration);
    } catch (e) {
        console.log('  Error:', e.message);

        // 检查 unreachable 发生在哪里
        // 可能是因为某些预初始化数据缺失
        console.log('\n分析: unreachable 可能是因为:');
        console.log('  1. 缺少 wbindgen glue code');
        console.log('  2. 内部 panic (Rust 断言失败)');
        console.log('  3. 内存布局不正确');
    }

    // 尝试 hash 函数
    console.log('\n调用 wasm_deepseek_hash_v1...');
    try {
        const testInput = prefix + '69992';
        const inputPtr = malloc(50, 1);
        const inputLen = writeString(testInput, inputPtr);

        const hashPtr = addToStackPointer(-32);

        wasmExports.wasm_deepseek_hash_v1(hashPtr, inputPtr, inputLen);

        const hashBytes = uint8Mem.slice(hashPtr, hashPtr + 32);
        const hashHex = Array.from(hashBytes).map(b => b.toString(16).padStart(2, '0')).join('');

        console.log('  Input:', testInput);
        console.log('  Hash:', hashHex);
        console.log('  Expected:', challenge);
    } catch (e) {
        console.log('  Error:', e.message);
    }

    // 检查栈指针位置
    console.log('\n栈指针状态:');
    const currentStack = addToStackPointer(0);
    console.log('  Current stack pointer:', currentStack);
}

runWithExportedMemory().catch(console.error);