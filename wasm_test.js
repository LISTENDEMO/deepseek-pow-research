// Load and test DeepSeek's WASM Keccak
const fs = require('fs');
const path = require('path');

async function testWasm() {
    const wasmBuffer = fs.readFileSync(path.join(__dirname, 'sha3_wasm.wasm'));

    // Load WASM
    const wasmModule = await WebAssembly.compile(wasmBuffer);
    const wasmInstance = await WebAssembly.instantiate(wasmModule, {
        env: {
            // 可能需要的 imports
            memory: new WebAssembly.Memory({ initial: 256 }),
        }
    });

    console.log('WASM exports:', Object.keys(wasmInstance.exports));

    // 检查导出的函数
    for (const [name, fn] of Object.entries(wasmInstance.exports)) {
        console.log(`  ${name}:`, typeof fn);
    }
}

testWasm().catch(console.error);