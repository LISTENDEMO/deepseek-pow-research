// 分析 WASM 函数签名并测试
const fs = require('fs');
const path = require('path');

async function analyzeWasm() {
    const wasmBuffer = fs.readFileSync(path.join(__dirname, 'sha3_wasm.wasm'));

    // 解析 WASM 模块结构
    const wasmModule = await WebAssembly.compile(wasmBuffer);

    // 查看模块的 sections
    // WebAssembly.Module.customSections 可以获取自定义 section

    // 尝试不同的 imports
    // WASM 通常需要 wbindgen 相关的 imports

    // 创建 memory
    const memory = new WebAssembly.Memory({ initial: 256, maximum: 1024 });
    const memView = new Uint8Array(memory.buffer);

    // wbindgen imports
    const imports = {
        wbindgen: {
            // 可能需要的函数
        },
        env: {
            memory: memory,
        }
    };

    // 尝试加载
    try {
        const wasmInstance = await WebAssembly.instantiate(wasmModule, imports);
        const exports = wasmInstance.exports;

        console.log('Loaded with basic imports');

        // 测试 wasm_deepseek_hash_v1
        // 参数推测: (prefix_ptr, prefix_len, answer, output_ptr)
        // 或者: (prefix_ptr, prefix_len, answer) 返回 hash_ptr

        // 分配内存
        const prefix = 'test_prefix_';
        const prefixPtr = 0;
        const answer = 12345;

        // 编码 prefix
        const encoder = new TextEncoder();
        const prefixBytes = encoder.encode(prefix);
        for (let i = 0; i < prefixBytes.length; i++) {
            memView[prefixPtr + i] = prefixBytes[i];
        }

        console.log('Testing wasm_deepseek_hash_v1...');
        console.log('Prefix:', prefix);
        console.log('Answer:', answer);

        // 尝试不同参数组合
        // 可能是: wasm_deepseek_hash_v1(prefix_ptr, prefix_len, answer)
        // 或者: wasm_deepseek_hash_v1(algorithm, challenge_ptr, salt_ptr, difficulty, expireAt)

        const outputPtr = exports.__wbindgen_add_to_stack_pointer(-32);

        try {
            // 尝试调用
            const result = exports.wasm_deepseek_hash_v1(
                prefixPtr, prefixBytes.length, answer
            );
            console.log('Result:', result);
        } catch (e) {
            console.log('Error 1:', e.message);
        }

        // 或者其他参数
        try {
            const result = exports.wasm_deepseek_hash_v1(
                prefixPtr, prefixBytes.length, String(answer).length
            );
            console.log('Result 2:', result);
        } catch (e) {
            console.log('Error 2:', e.message);
        }

    } catch (e) {
        console.log('Load error:', e.message);
    }

    // 使用正确的 imports (从 Worker 代码中提取)
    // Worker 代码中需要 TextEncoder/TextDecoder

    console.log('\n--- Using proper imports ---');

    const properImports = {
        wbindgen: {
            TextEncoder: function() {
                return {
                    encode: function(str) {
                        const encoder = new TextEncoder();
                        return encoder.encode(str);
                    }
                };
            },
            TextDecoder: function(encoding, options) {
                return {
                    decode: function(bytes) {
                        const decoder = new TextDecoder(encoding, options);
                        return decoder.decode(bytes);
                    }
                };
            }
        },
        env: {
            memory: memory,
        }
    };

    // 尝试完整 Worker 代码加载
    // 实际上，我应该直接复制 Worker 的执行环境

    console.log('\nWASM exports available:');
    console.log('  wasm_deepseek_hash_v1 - hash function');
    console.log('  wasm_solve - solve PoW');

    // 最简单的方法: 直接运行 DeepSeek Worker JS 并传入 challenge
}

analyzeWasm().catch(console.error);