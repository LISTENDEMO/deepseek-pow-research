// DeepSeek PoW Solver using WASM
const fs = require('fs');
const path = require('path');

class DeepSeekPowSolver {
    constructor() {
        this.wasmInstance = null;
        this.memory = null;
    }

    async init() {
        const wasmBuffer = fs.readFileSync(path.join(__dirname, 'sha3_wasm.wasm'));

        // 创建 memory
        this.memory = new WebAssembly.Memory({ initial: 256 });

        const wasmModule = await WebAssembly.compile(wasmBuffer);
        this.wasmInstance = await WebAssembly.instantiate(wasmModule, {
            wbindgen: {
                // 提供必要的 imports
            },
            env: {
                memory: this.memory,
            }
        });

        return this;
    }

    // 编码字符串到 WASM memory
    encodeString(str) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(str);
        const ptr = this.wasmInstance.exports.__wbindgen_add_to_stack_pointer(-bytes.length);
        const memView = new Uint8Array(this.memory.buffer);

        // 写入 bytes
        for (let i = 0; i < bytes.length; i++) {
            memView[ptr + i] = bytes[i];
        }

        return { ptr, length: bytes.length };
    }

    // 使用 WASM 计算 hash
    hash(prefix, answer) {
        const input = prefix + String(answer);
        const { ptr, length } = this.encodeString(input);

        // 调用 wasm_deepseek_hash_v1 或 wasm_solve
        // 先尝试 wasm_solve

        // 这个函数可能需要不同的参数
        // 让我直接使用 wasm_solve 来解决
    }

    // 解决 PoW
    solve(challenge, salt, difficulty, expireAt) {
        const prefix = `${salt}_${expireAt}_`;

        console.log('Solving with WASM...');
        console.log('  Prefix:', prefix);
        console.log('  Target:', challenge);
        console.log('  Difficulty:', difficulty);

        // wasm_solve 参数:
        // (challenge_hash, prefix, difficulty)
        // 返回找到的 answer

        try {
            const exports = this.wasmInstance.exports;

            // 编码参数
            const challengePtr = this.encodeString(challenge);
            const prefixPtr = this.encodeString(prefix);

            // 调用 wasm_solve
            // 需要看函数签名
            const result = exports.wasm_solve(
                challengePtr.ptr,
                challengePtr.length,
                prefixPtr.ptr,
                prefixPtr.length,
                difficulty
            );

            console.log('WASM solve result:', result);
            return result;
        } catch (e) {
            console.error('WASM error:', e);
            // Fallback to JS
            return this.solveJS(prefix, challenge, difficulty);
        }
    }

    // JS fallback (使用正确的 Keccak)
    solveJS(prefix, target, difficulty) {
        const { keccak256 } = require('js-sha3');
        const start = Date.now();

        for (let i = 0; i < difficulty; i++) {
            const hash = keccak256(prefix + String(i));
            if (hash === target) {
                console.log(`JS found: ${i} in ${(Date.now()-start)/1000}s`);
                return i;
            }
        }

        console.log('JS: not found');
        return null;
    }
}

// 主函数
async function main() {
    const solver = await new DeepSeekPowSolver().init();
    const challengeData = JSON.parse(process.argv[2] || '{}');

    if (challengeData.challenge) {
        const answer = solver.solve(
            challengeData.challenge,
            challengeData.salt,
            challengeData.difficulty,
            challengeData.expire_at
        );
        console.log(JSON.stringify({ answer }));
    } else {
        // 测试 hash
        console.log('Testing WASM hash...');
    }
}

main().catch(console.error);