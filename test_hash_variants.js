#!/usr/bin/env node
/**
 * 测试不同的 Keccak 变体
 */

const crypto = require('crypto');

// 测试数据
const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;

const prefix = `${salt}_${expire_at}_`;
const testStr = prefix + String(answer);

console.log('=' .repeat(60));
console.log('Testing different hash algorithms');
console.log('=' .repeat(60));
console.log('Input:', testStr);
console.log('Target:', challenge);

// SHA3-256
console.log('\nSHA3-256:', crypto.createHash('sha3-256').update(testStr).digest('hex'));

// SHA3-512 (then take first 32 bytes)
console.log('SHA3-512 (first 32 bytes):', crypto.createHash('sha3-512').update(testStr).digest('hex').slice(0, 64));

// SHA-256
console.log('SHA-256:', crypto.createHash('sha256').update(testStr).digest('hex'));

// Keccak-256 (if pycryptodome-style available)
// Node.js crypto doesn't have pre-SHA3 Keccak, so we'll implement it

// Try different padding values
console.log('\nTrying with pycryptodome Keccak (if available):');
try {
    // Node.js doesn't have direct Keccak-256, but we can check
    console.log('  (Node.js crypto does not have pre-SHA3 Keccak)');
} catch (e) {
    console.log('  Error:', e.message);
}

// 测试不同 prefix 格式
console.log('\n' + '=' .repeat(60));
console.log('Testing different prefix formats:');
console.log('=' .repeat(60));

const formats = [
    `${salt}_${expire_at}_${answer}`,
    `${salt}_${expire_at}_${answer}`,
    `${expire_at}_${salt}_${answer}`,
    `${salt}_${answer}`,
    `${expire_at}_${answer}`,
];

formats.forEach((fmt, i) => {
    const h = crypto.createHash('sha3-256').update(fmt).digest('hex');
    console.log(`Format ${i+1}: ${fmt.slice(0, 50)}...`);
    console.log(`  Hash: ${h}`);
    console.log(`  Match: ${h === challenge}`);
});