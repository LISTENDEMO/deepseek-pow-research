#!/usr/bin/env node
/**
 * 使用 keccak npm 包测试不同的 Keccak 变体
 */

const keccak = require('keccak');
const crypto = require('crypto');

// 测试数据
const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;

const prefix = `${salt}_${expire_at}_`;
const testStr = prefix + String(answer);

console.log('=' .repeat(60));
console.log('Testing keccak npm package variants');
console.log('=' .repeat(60));
console.log('Input:', testStr);
console.log('Target:', challenge);

// Keccak-256 (pre-SHA3, padding=0x01)
console.log('\nkeccak-256 (padding=0x01):');
const k256 = keccak('keccak256').update(testStr).digest('hex');
console.log('  Hash:', k256);
console.log('  Match:', k256 === challenge);

// Keccak-512
console.log('\nkeccak-512 (first 32 bytes):');
const k512 = keccak('keccak512').update(testStr).digest('hex').slice(0, 64);
console.log('  Hash:', k512);
console.log('  Match:', k512 === challenge);

// SHA3-256
console.log('\nsha3-256 (Node.js crypto):');
const sha3 = crypto.createHash('sha3-256').update(testStr).digest('hex');
console.log('  Hash:', sha3);
console.log('  Match:', sha3 === challenge);

// SHA3-512 (first 32 bytes)
console.log('\nsha3-512 (first 32 bytes):');
const sha3_512 = crypto.createHash('sha3-512').update(testStr).digest('hex').slice(0, 64);
console.log('  Hash:', sha3_512);
console.log('  Match:', sha3_512 === challenge);

// 测试不同格式
console.log('\n' + '=' .repeat(60));
console.log('Testing different input formats with keccak256:');
console.log('=' .repeat(60));

const formats = [
    testStr,
    prefix + String(answer),  // Same as testStr
    `${salt}_${expire_at}_${answer}`,
    `${salt}_${answer}`,
    `${expire_at}_${salt}_${answer}`,
    `${answer}_${salt}_${expire_at}`,
    `${expire_at}_${answer}_${salt}`,
];

formats.forEach((fmt, i) => {
    const h = keccak('keccak256').update(fmt).digest('hex');
    console.log(`\nFormat ${i+1}: ${fmt.slice(0, 50)}...`);
    console.log(`  Hash: ${h}`);
    console.log(`  Match: ${h === challenge}`);
});

// 测试搜索
console.log('\n' + '=' .repeat(60));
console.log('Searching with keccak256:');
console.log('=' .repeat(60));

const startPrefix = new keccak('keccak256');
startPrefix.update(prefix);

console.log('Prefix:', prefix);
console.log('Searching 0-20000...');

for (let i = 0; i < 20000; i++) {
    const k = new keccak('keccak256');
    k.update(prefix);
    k.update(String(i));
    if (k.digest('hex') === challenge) {
        console.log('*** FOUND! answer =', i, '***');
        break;
    }
    if (i % 5000 === 0) {
        console.log('Progress:', i);
    }
}
console.log('Done.');