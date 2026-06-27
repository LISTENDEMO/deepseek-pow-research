#!/usr/bin/env node
/**
 * 正确的 WASM 初始化 - 模拟完整 wbindgen 环境
 */

const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
const wasmBuffer = fs.readFileSync(wasmPath);

console.log('WASM size:', wasmBuffer.length, 'bytes');

// 分析 WASM 的 imports 和 exports
async function analyzeAndRun() {
    const wasmModule = await WebAssembly.compile(wasmBuffer);

    // 获取 imports 需求
    const imports = WebAssembly.Module.imports(wasmModule);
    console.log('\nRequired imports:');
    imports.forEach(imp => {
        console.log(`  ${imp.module}.${imp.name}: ${imp.kind}`);
    });

    // 获取 exports
    const exports = WebAssembly.Module.exports(wasmModule);
    console.log('\nExports:');
    exports.forEach(exp => {
        console.log(`  ${exp.name}: ${exp.kind} (index=${exp.index || 'N/A'})`);
    });

    // 创建完整的环境
    const memory = new WebAssembly.Memory({ initial: 17, maximum: 17 });

    // Text encoder/decoder
    const textEncoder = new TextEncoder('utf-8');
    const textDecoder = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });

    // 内存视图
    let uint8Mem = null;
    let dataViewMem = null;

    function getUint8Mem() {
        if (!uint8Mem || uint8Mem.buffer !== memory.buffer) {
            uint8Mem = new Uint8Array(memory.buffer);
        }
        return uint8Mem;
    }

    function getDataViewMem() {
        if (!dataViewMem || dataViewMem.buffer !== memory.buffer) {
            dataViewMem = new DataView(memory.buffer);
        }
        return dataViewMem;
    }

    // Stack pointer (从 WASM 分析，初始值约 1048576)
    let stackPointer = 1048576;

    // 写入字符串到内存
    let WASM_VECTOR_LEN = 0;

    function passStringToWasm0(str) {
        const buf = textEncoder.encode(str);
        const ptr = stackPointer;
        const len = buf.length;

        // 扩展栈
        stackPointer += len + 16;  // 多分配一些空间

        // 写入
        const mem = getUint8Mem();
        for (let i = 0; i < len; i++) {
            mem[ptr + i] = buf[i];
        }

        WASM_VECTOR_LEN = len;
        return ptr;
    }

    // wbindgen imports
    const wbindgenImports = {
        __wbindgen_add_to_stack_pointer: function(n) {
            stackPointer += n;
            return stackPointer;
        },
        __wbindgen_export_0: function(len, align) {
            // malloc-like: 分配内存
            const ptr = stackPointer;
            stackPointer = ptr + len + (align > 0 ? align - 1 : 0);
            return ptr;
        },
        __wbindgen_export_1: function(ptr, len, newLen, align) {
            // realloc-like: 重新分配
            if (newLen <= len) return ptr;
            const newPtr = stackPointer;
            stackPointer = newPtr + newLen + (align > 0 ? align - 1 : 0);
            // 复制旧数据
            const mem = getUint8Mem();
            for (let i = 0; i < len; i++) {
                mem[newPtr + i] = mem[ptr + i];
            }
            return newPtr;
        },
        __wbindgen_export_2: function(ptr) {
            // free-like: 释放内存 (wbindgen 使用栈，不需要真正释放)
            // 不做任何事
        },
        memory: memory
    };

    // 构建 imports 对象
    const importObject = {
        wbg: wbindgenImports,
        env: { memory: memory }
    };

    // 检查是否需要其他 imports
    const missingImports = imports.filter(imp => {
        if (imp.module === 'wbg' || imp.module === 'env') {
            return !importObject[imp.module]?.[imp.name];
        }
        return true;  // 未知的 module
    });

    if (missingImports.length > 0) {
        console.log('\nMissing imports that need stubbing:');
        missingImports.forEach(imp => {
            console.log(`  ${imp.module}.${imp.name}`);
            // 添加 stub
            if (!importObject[imp.module]) {
                importObject[imp.module] = {};
            }
            if (imp.kind === 'function') {
                importObject[imp.module][imp.name] = function(...args) {
                    console.log(`Stub called: ${imp.module}.${imp.name}(${args})`);
                    return 0;
                };
            }
        });
    }

    // 实例化 WASM
    try {
        const instance = await WebAssembly.instantiate(wasmModule, importObject);
        const wasmExports = instance.exports;

        console.log('\nWASM 实例化成功!');
        console.log('Exports:', Object.keys(wasmExports));

        // 测试数据
        const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
        const prefix = '811e05c93d1b71993710_1776153216159_';
        const difficulty = 144000;

        // 准备内存
        const challengePtr = passStringToWasm0(challenge);
        const challengeLen = WASM_VECTOR_LEN;

        const prefixPtr = passStringToWasm0(prefix);
        const prefixLen = WASM_VECTOR_LEN;

        // 输出位置 (栈下方)
        const outputPtr = stackPointer - 32;
        stackPointer = outputPtr;

        console.log('\n内存布局:');
        console.log(`  challenge: ptr=${challengePtr}, len=${challengeLen}`);
        console.log(`  prefix: ptr=${prefixPtr}, len=${prefixLen}`);
        console.log(`  output: ptr=${outputPtr}`);
        console.log(`  stackPointer: ${stackPointer}`);

        // 尝试调用 wasm_solve
        if (wasmExports.wasm_solve) {
            console.log('\n调用 wasm_solve...');

            try {
                wasmExports.wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty);

                const result = getDataViewMem().getInt32(outputPtr, true);
                const duration = getDataViewMem().getFloat64(outputPtr + 8, true);

                console.log('  Result:', result);
                console.log('  Duration:', duration);

                if (result === 69992) {
                    console.log('  ✓ 正确匹配!');
                } else if (result === 0) {
                    console.log('  未找到答案 (返回 0)');
                } else {
                    console.log(`  找到答案: ${result}`);
                }
            } catch (e) {
                console.log('  wasm_solve 错误:', e.message);
            }
        }

        // 尝试调用 wasm_deepseek_hash_v1
        if (wasmExports.wasm_deepseek_hash_v1) {
            console.log('\n调用 wasm_deepseek_hash_v1...');

            const testInput = prefix + '69992';
            const inputPtr = passStringToWasm0(testInput);
            const inputLen = WASM_VECTOR_LEN;

            const hashOutputPtr = stackPointer - 32;
            stackPointer = hashOutputPtr;

            console.log(`  input: "${testInput}"`);
            console.log(`  input ptr=${inputPtr}, len=${inputLen}`);
            console.log(`  hash output ptr=${hashOutputPtr}`);

            try {
                wasmExports.wasm_deepseek_hash_v1(hashOutputPtr, inputPtr, inputLen);

                // 读取 hash
                const hashBytes = getUint8Mem().slice(hashOutputPtr, hashOutputPtr + 32);
                const hashHex = Array.from(hashBytes).map(b => b.toString(16).padStart(2, '0')).join('');

                console.log('  Hash:', hashHex);
                console.log('  Expected:', challenge);
                console.log('  Match:', hashHex === challenge);

                if (hashHex === '0000000000000000000000000000000000000000000000000000000000000000') {
                    console.log('  ⚠ 返回全零 - 函数未正确执行');
                }
            } catch (e) {
                console.log('  wasm_deepseek_hash_v1 错误:', e.message);
            }
        }

    } catch (e) {
        console.log('WASM 实例化失败:', e.message);
        console.log(e.stack);
    }
}

analyzeAndRun().catch(console.error);