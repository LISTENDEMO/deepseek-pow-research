#!/usr/bin/env node
/**
 * WASM 正确初始化 - 使用 WASM 自己的内存管理
 */

const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
const wasmBuffer = fs.readFileSync(wasmPath);

async function runWasmCorrectly() {
    const wasmModule = await WebAssembly.compile(wasmBuffer);
    const instance = await WebAssembly.instantiate(wasmModule, {});
    const wasm = instance.exports;

    console.log('WASM exports:', Object.keys(wasm));

    // 获取最新的内存视图
    let getMem = () => new Uint8Array(wasm.memory.buffer);
    let getView = () => new DataView(wasm.memory.buffer);

    // 写入字符串
    function writeString(str) {
        const bytes = new TextEncoder().encode(str);
        const ptr = wasm.__wbindgen_export_0(bytes.length, 1);
        const mem = getMem();
        for (let i = 0; i < bytes.length; i++) {
            mem[ptr + i] = bytes[i];
        }
        return { ptr, len: bytes.length };
    }

    // 读取字符串
    function readString(ptr, len) {
        const mem = getMem();
        return new TextDecoder().decode(mem.slice(ptr, ptr + len));
    }

    // 读取 hash (32 bytes hex)
    function readHash(ptr) {
        const mem = getMem();
        const bytes = mem.slice(ptr, ptr + 32);
        return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
    }

    // 测试数据
    const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
    const prefix = '811e05c93d1b71993710_1776153216159_';
    const testInput = prefix + '69992';

    console.log('\n测试数据:');
    console.log('  Challenge:', challenge);
    console.log('  Test input:', testInput);

    // 写入数据
    const { ptr: inputPtr, len: inputLen } = writeString(testInput);
    console.log(`  Input ptr: ${inputPtr}, len: ${inputLen}`);

    // 验证写入
    console.log('  Input in memory:', readString(inputPtr, inputLen));

    // 分配输出空间
    const hashPtr = wasm.__wbindgen_add_to_stack_pointer(-32);
    console.log('  Hash output ptr:', hashPtr);

    // 调用 hash 函数
    console.log('\n调用 wasm_deepseek_hash_v1...');
    try {
        wasm.wasm_deepseek_hash_v1(hashPtr, inputPtr, inputLen);

        const hashResult = readHash(hashPtr);
        console.log('  Hash:', hashResult);
        console.log('  Expected:', challenge);
        console.log('  Match:', hashResult === challenge);

        // 如果是全零，检查内存状态
        if (hashResult === '0000000000000000000000000000000000000000000000000000000000000000') {
            console.log('\n  返回全零，检查内存...');
            const mem = getMem();
            // 查看输入数据周围
            console.log('  Memory around input:', mem.slice(inputPtr - 8, inputPtr + inputLen + 8).map(b => b.toString(16).padStart(2, '0')).join(' '));
            // 查看输出数据周围
            console.log('  Memory around output:', mem.slice(hashPtr - 8, hashPtr + 40).map(b => b.toString(16).padStart(2, '0')).join(' '));
        }
    } catch (e) {
        console.log('  Error:', e.message);

        // 详细分析 unreachable 的原因
        console.log('\n分析 WASM panic 原因...');

        // 查看 WASM 的数据段
        const mem = getMem();
        console.log('Memory size:', wasm.memory.buffer.byteLength);

        // 查找可能的状态标志
        // 通常 wbindgen 有一些初始化标志
        for (let i = 0; i < 100; i++) {
            if (mem[i] !== 0) {
                console.log(`  Offset ${i}: ${mem[i]}`);
            }
        }

        // 检查 1048576 附近 (通常是栈起始位置)
        console.log('\nMemory around stack start (1048576):');
        const stackStart = 1048576;
        console.log('  ', mem.slice(stackStart - 16, stackStart + 16).map(b => b.toString(16).padStart(2, '0')).join(' '));
    }

    // 尝试 wasm_solve
    console.log('\n调用 wasm_solve...');
    const { ptr: challengePtr, len: challengeLen } = writeString(challenge);
    const { ptr: prefixPtr2, len: prefixLen2 } = writeString(prefix);

    // 输出空间 (int32 + float64 = 16 bytes)
    const solveOutputPtr = wasm.__wbindgen_add_to_stack_pointer(-16);

    console.log(`  Challenge ptr: ${challengePtr}, len: ${challengeLen}`);
    console.log(`  Prefix ptr: ${prefixPtr2}, len: ${prefixLen2}`);
    console.log(`  Output ptr: ${solveOutputPtr}`);

    try {
        wasm.wasm_solve(solveOutputPtr, challengePtr, challengeLen, prefixPtr2, prefixLen2, 144000);

        const view = getView();
        const answer = view.getInt32(solveOutputPtr, true);
        const duration = view.getFloat64(solveOutputPtr + 8, true);

        console.log('  Answer:', answer);
        console.log('  Duration:', duration);
        console.log('  Expected:', 69992);
    } catch (e) {
        console.log('  Error:', e.message);
    }
}

runWasmCorrectly().catch(console.error);