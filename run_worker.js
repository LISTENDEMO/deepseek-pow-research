// 在 Node.js 中运行 DeepSeek Worker
const fs = require('fs');
const path = require('path');

// 读取 Worker JS
const workerCode = fs.readFileSync(path.join(__dirname, 'deepseek_worker_js.js'), 'utf8');

// Worker 代码是一个 webpack bundle
// 需要 Worker 环境的 globals

// 设置必要的 globals
let result = null;

global.postMessage = function(msg) {
    result = msg;
    console.log('postMessage called:', JSON.stringify(msg, null, 2));
};

global.importScripts = function(...urls) {
    console.log('importScripts:', urls);
    // 模拟加载脚本 - 实际 WASM 已经在 bundle 中
};

global.self = global;

// 执行 Worker 代码
console.log('Executing Worker bundle...');
try {
    eval(workerCode);
} catch (e) {
    console.log('Eval error:', e.message);
    if (e.stack) console.log('Stack:', e.stack.split('\n').slice(0, 5).join('\n'));
}

console.log('\nAfter eval:');
console.log('onmessage type:', typeof global.onmessage);

// 发送 challenge
if (typeof global.onmessage === 'function') {
    console.log('\nSending challenge...');
    const challengeData = {
        type: 'pow-challenge',
        challenge: {
            algorithm: 'DeepSeekHashV1',
            challenge: 'edfeafeb9893d67e42d763740c36d8f6eb4ab9af9e45cd40b79a13c4a2eefb44',
            salt: '597ae3e54605d43c1dd6',
            difficulty: 144000,
            expireAt: 1776155801356,
            signature: 'test_signature'
        }
    };

    global.onmessage({ data: challengeData });
} else {
    console.log('onmessage not a function');
}

// 等待结果
setTimeout(() => {
    console.log('\nFinal result:', result);
    process.exit(0);
}, 15000);