#!/usr/bin/env node
/**
 * 分析 wasm_solve 输出布局
 */

const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
const wasmBuffer = fs.readFileSync(wasmPath);

async function analyzeOutputLayout() {
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

    // 测试数据
    const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
    const prefix = '811e05c93d1b71993710_1776153216159_';
    const difficulty = 144000;

    console.log('测试 wasm_solve 输出布局...');
    console.log('Challenge:', challenge);
    console.log('Prefix:', prefix);
    console.log('Expected answer: 69992');

    const { ptr: challengePtr, len: challengeLen } = writeString(challenge);
    const { ptr: prefixPtr, len: prefixLen } = writeString(prefix);

    // 分配较大的输出空间以便观察
    const outputPtr = wasm.__wbindgen_add_to_stack_pointer(-64);

    // 清零输出区域
    const mem = getMem();
    for (let i = 0; i < 64; i++) {
        mem[outputPtr + i] = 0;
    }

    console.log('\n调用 wasm_solve...');
    console.log('Output ptr:', outputPtr);

    wasm.wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty);

    // 读取所有可能的输出格式
    const view = getView();

    console.log('\n原始输出 bytes (前 32 bytes):');
    console.log(' ', mem.slice(outputPtr, outputPtr + 32).map(b => b.toString(16).padStart(2, '0')).join(' '));

    console.log('\n各种解释:');
    console.log('  int32 at offset 0:', view.getInt32(outputPtr + 0, true));
    console.log('  int32 at offset 4:', view.getInt32(outputPtr + 4, true));
    console.log('  int32 at offset 8:', view.getInt32(outputPtr + 8, true));
    console.log('  int32 at offset 12:', view.getInt32(outputPtr + 12, true));

    console.log('\n  float64 at offset 0:', view.getFloat64(outputPtr + 0, true));
    console.log('  float64 at offset 8:', view.getFloat64(outputPtr + 8, true));

    console.log('\n  uint32 at offset 0:', view.getUint32(outputPtr + 0, true));
    console.log('  uint32 at offset 4:', view.getUint32(outputPtr + 4, true));
    console.log('  uint32 at offset 8:', view.getUint32(outputPtr + 8, true));

    // 检查内存变化
    console.log('\n内存变化分析:');
    console.log('  Bytes at output:');
    for (let i = 0; i < 16; i++) {
        const b = mem[outputPtr + i];
        console.log(`    offset ${i}: 0x${b.toString(16).padStart(2, '0')} (${b})`);
    }

    // 如果 float64 at offset 8 是 69992，那么答案可能在那里
    const possibleAnswer = view.getFloat64(outputPtr + 8, true);
    if (possibleAnswer === 69992) {
        console.log('\n*** 发现: float64 at offset 8 = 69992 ***');
        console.log('这意味着输出布局可能是:');
        console.log('  offset 0: int32 (状态/错误码)');
        console.log('  offset 8: float64 (答案)');
    }

    // 尝试不同的 interpretation
    console.log('\n检查: int32 at offset 8 作为答案:');
    const answerAsInt32 = view.getInt32(outputPtr + 8, true);
    console.log('  值:', answerAsInt32);
    console.log('  是否等于 69992:', answerAsInt32 === 69992);
}

analyzeOutputLayout().catch(console.error);