// 使用 WASM 的 wasm_solve 函数直接解决 PoW
const fs = require('fs');
const path = require('path');
const https = require('https');

async function solvePowWithWasm() {
    // 加载 WASM
    const wasmBuffer = fs.readFileSync(path.join(__dirname, 'sha3_wasm.wasm'));
    const wasmModule = await WebAssembly.compile(wasmBuffer);

    // 创建 memory
    const memory = new WebAssembly.Memory({ initial: 256, maximum: 256 });

    // WASM imports (需要一些基本函数)
    const imports = {
        env: {
            memory: memory,
        }
    };

    const wasmInstance = await WebAssembly.instantiate(wasmModule, imports);
    const exports = wasmInstance.exports;

    // Helper 函数
    function writeString(str, ptr) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(str);
        const memView = new Uint8Array(memory.buffer);
        for (let i = 0; i < bytes.length; i++) {
            memView[ptr + i] = bytes[i];
        }
        return bytes.length;
    }

    // 获取 challenge (从 API)
    const token = 'IlBUFXG6Wu6p1BabVT/bRi3kNux5ngdRHabtBcZjoUTHhR8f5auo7jgXNx/clZs9';

    console.log('Getting challenge from API...');

    const challengeData = await new Promise((resolve, reject) => {
        const postData = JSON.stringify({ target_path: '/api/v0/chat/completion' });

        const options = {
            hostname: 'chat.deepseek.com',
            path: '/api/v0/chat/create_pow_challenge',
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'x-app-version': '20241129.1',
                'x-client-locale': 'zh_CN',
                'x-client-platform': 'web',
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                const json = JSON.parse(data);
                resolve(json.data.biz_data.challenge);
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });

    console.log('Challenge received:');
    console.log('  challenge:', challengeData.challenge.substring(0, 20) + '...');
    console.log('  salt:', challengeData.salt);
    console.log('  difficulty:', challengeData.difficulty);
    console.log('  expire_at:', challengeData.expire_at);

    // 构建 prefix (根据 DeepSeek 代码: salt + '_' + expire_at + '_')
    const prefix = `${challengeData.salt}_${challengeData.expire_at}_`;
    console.log('  prefix:', prefix);

    // 使用 WASM solve
    const challengePtr = 0;
    const prefixPtr = 64;
    const outputPtr = 128;

    const challengeLen = writeString(challengeData.challenge, challengePtr);
    const prefixLen = writeString(prefix, prefixPtr);

    console.log('\nCalling WASM wasm_solve...');

    try {
        // wasm_solve 参数顺序需要实验
        // 可能的顺序: (output_ptr, challenge_ptr, challenge_len, prefix_ptr, prefix_len, difficulty)

        const result = exports.wasm_solve(
            outputPtr,        // 输出位置
            challengePtr,     // challenge 指针
            challengeLen,     // challenge 长度
            prefixPtr,        // prefix 指针
            prefixLen,        // prefix 长度
            challengeData.difficulty  // difficulty
        );

        console.log('wasm_solve returned:', result);

        // 读取输出 (answer + duration)
        const outputView = new DataView(memory.buffer);
        const answer = outputView.getInt32(outputPtr, true);
        const duration = outputView.getFloat64(outputPtr + 8, true);

        console.log('\nResult:');
        console.log('  Answer:', answer);
        console.log('  Duration:', duration, 'ms');

        return { answer, duration };

    } catch (e) {
        console.error('WASM error:', e.message);

        // Fallback to JS search
        console.log('\nFalling back to JS search...');
        const { keccak256 } = require('js-sha3');

        const start = Date.now();
        for (let i = 0; i < challengeData.difficulty; i++) {
            const hash = keccak256(prefix + String(i));
            if (hash === challengeData.challenge) {
                console.log('JS Found answer:', i, 'in', (Date.now() - start), 'ms');
                return { answer: i, duration: Date.now() - start };
            }
        }

        console.log('JS: Not found');
        return { answer: null };
    }
}

solvePowWithWasm()
    .then(result => console.log('\nFinal result:', JSON.stringify(result)))
    .catch(err => console.error('Error:', err));