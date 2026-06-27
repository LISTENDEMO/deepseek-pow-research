#!/usr/bin/env node
/**
 * Direct WASM test with proper wbindgen initialization
 */

const fs = require('fs');
const path = require('path');

// WASM path
const wasmPath = path.join(__dirname, 'sha3_wasm.wasm');
const wasmBgPath = path.join(__dirname, 'sha3_wasm_bg.wasm');

// Check which WASM file exists
console.log('WASM files:');
console.log('  sha3_wasm.wasm exists:', fs.existsSync(wasmPath));
console.log('  sha3_wasm_bg.wasm exists:', fs.existsSync(wasmBgPath));

// Use the correct WASM file
const actualWasmPath = fs.existsSync(wasmBgPath) ? wasmBgPath : wasmPath;
console.log('  Using:', actualWasmPath);

async function testWasm() {
    const wasmBuffer = fs.readFileSync(actualWasmPath);
    console.log('\nWASM size:', wasmBuffer.length, 'bytes');

    // Try to compile WASM
    try {
        const wasmModule = await WebAssembly.compile(wasmBuffer);
        console.log('WASM compiled successfully');

        // Create minimal imports for wbindgen
        const memory = new WebAssembly.Memory({ initial: 17, maximum: 17 });

        // Create a minimal wbindgen environment
        let textEncoder = new TextEncoder();
        let textDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });

        let WASM_VECTOR_LEN = 0;
        let cachedUint8Memory = null;
        let cachedDataViewMemory = null;

        function getUint8Memory() {
            if (cachedUint8Memory === null || cachedUint8Memory.buffer !== memory.buffer) {
                cachedUint8Memory = new Uint8Array(memory.buffer);
            }
            return cachedUint8Memory;
        }

        function getDataViewMemory() {
            if (cachedDataViewMemory === null || cachedDataViewMemory.buffer !== memory.buffer) {
                cachedDataViewMemory = new DataView(memory.buffer);
            }
            return cachedDataViewMemory;
        }

        function passStringToWasm0(arg, malloc, realloc) {
            if (realloc === undefined) {
                const buf = textEncoder.encode(arg);
                const ptr = malloc(buf.length, 1) >>> 0;
                getUint8Memory().subarray(ptr, ptr + buf.length).set(buf);
                WASM_VECTOR_LEN = buf.length;
                return ptr;
            }
            let len = arg.length;
            let ptr = malloc(len, 1) >>> 0;
            const mem = getUint8Memory();
            let offset = 0;
            for (; offset < len; offset++) {
                const code = arg.charCodeAt(offset);
                if (code > 127) break;
                mem[ptr + offset] = code;
            }
            if (offset !== len) {
                if (offset !== 0) {
                    arg = arg.slice(offset);
                }
                ptr = realloc(ptr, len, len = offset + 3 * arg.length, 1) >>> 0;
                const buf = textEncoder.encode(arg);
                const mem = getUint8Memory();
                mem.set(buf, ptr + offset);
                offset += buf.length;
            }
            WASM_VECTOR_LEN = offset;
            return ptr;
        }

        // Stack pointer management
        let stack_pointer = 1048576;

        const imports = {
            wbg: {
                memory: memory,
                __wbindgen_export_0: (len, align) => {
                    const ptr = stack_pointer;
                    stack_pointer = ptr + len + (align - 1) & ~(align - 1);
                    return ptr >>> 0;
                },
                __wbindgen_export_1: (ptr, len, new_len, align) => {
                    // realloc - for now just extend stack
                    stack_pointer = ptr + new_len + (align - 1) & ~(align - 1);
                    return ptr >>> 0;
                },
                __wbindgen_add_to_stack_pointer: (n) => {
                    stack_pointer += n;
                    return stack_pointer >>> 0;
                },
            },
            env: {
                memory: memory,
            }
        };

        const wasmInstance = await WebAssembly.instantiate(wasmModule, imports);
        const exports = wasmInstance.exports;

        console.log('WASM exports:', Object.keys(exports));

        // Test the hash function
        const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
        const prefix = '811e05c93d1b71993710_1776153216159_';
        const difficulty = 144000;

        console.log('\nTest data:');
        console.log('  Challenge:', challenge);
        console.log('  Prefix:', prefix);
        console.log('  Difficulty:', difficulty);

        // Try to call wasm_solve
        if (exports.wasm_solve) {
            console.log('\nCalling wasm_solve...');

            // Prepare memory layout
            const outputPtr = stack_pointer - 16;
            stack_pointer = outputPtr;

            const challengePtr = passStringToWasm0(challenge, exports.__wbindgen_export_0, exports.__wbindgen_export_1);
            const challengeLen = WASM_VECTOR_LEN;

            const prefixPtr = passStringToWasm0(prefix, exports.__wbindgen_export_0, exports.__wbindgen_export_1);
            const prefixLen = WASM_VECTOR_LEN;

            console.log('  Challenge ptr:', challengePtr, 'len:', challengeLen);
            console.log('  Prefix ptr:', prefixPtr, 'len:', prefixLen);
            console.log('  Output ptr:', outputPtr);

            try {
                exports.wasm_solve(outputPtr, challengePtr, challengeLen, prefixPtr, prefixLen, difficulty);

                const result = getDataViewMemory().getInt32(outputPtr, true);
                const duration = getDataViewMemory().getFloat64(outputPtr + 8, true);

                console.log('\n  Result:', result);
                console.log('  Duration:', duration);
                console.log('  Expected answer:', 69992);
                console.log('  Match:', result === 69992);
            } catch (e) {
                console.log('  wasm_solve error:', e.message);
                console.log('  This is expected if wbindgen needs more imports');
            }
        }

        // Try wasm_deepseek_hash_v1
        if (exports.wasm_deepseek_hash_v1) {
            console.log('\nCalling wasm_deepseek_hash_v1...');
            const testInput = prefix + '69992';
            const inputPtr = passStringToWasm0(testInput, exports.__wbindgen_export_0, exports.__wbindgen_export_1);
            const inputLen = WASM_VECTOR_LEN;

            const outputPtr2 = stack_pointer - 32;
            stack_pointer = outputPtr2;

            try {
                exports.wasm_deepseek_hash_v1(outputPtr2, inputPtr, inputLen);

                // Read 32 bytes output
                const hashBytes = getUint8Memory().slice(outputPtr2, outputPtr2 + 32);
                const hashHex = Array.from(hashBytes).map(b => b.toString(16).padStart(2, '0')).join('');

                console.log('  Input:', testInput);
                console.log('  Hash:', hashHex);
                console.log('  Expected:', challenge);
                console.log('  Match:', hashHex === challenge);
            } catch (e) {
                console.log('  wasm_deepseek_hash_v1 error:', e.message);
            }
        }

    } catch (e) {
        console.log('WASM error:', e.message);
        console.log('Stack trace:', e.stack);
    }
}

testWasm().catch(console.error);