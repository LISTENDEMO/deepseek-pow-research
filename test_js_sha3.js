#!/usr/bin/env node
/**
 * Test js-sha3 library for DeepSeek PoW
 */

const jsSha3 = require('./node_modules/js-sha3/src/sha3.js');

// Test data
const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;

const prefix = `${salt}_${expire_at}_`;
const testStr = prefix + String(answer);

console.log('='.repeat(60));
console.log('js-sha3 library test');
console.log('='.repeat(60));
console.log('Input:', testStr);
console.log('Target:', challenge);

// Check what functions are available
console.log('\nAvailable functions:');
console.log('  keccak256:', typeof jsSha3.keccak256);
console.log('  keccak512:', typeof jsSha3.keccak512);
console.log('  sha3_256:', typeof jsSha3.sha3_256);
console.log('  sha3_512:', typeof jsSha3.sha3_512);

// Test all available hash functions
if (typeof jsSha3.keccak256 === 'function') {
    console.log('\nkeccak256 (padding=0x01):');
    const hash = jsSha3.keccak256(testStr);
    console.log('  Hash:', hash);
    console.log('  Match:', hash === challenge);
}

if (typeof jsSha3.sha3_256 === 'function') {
    console.log('\nsha3_256 (padding=0x06):');
    const hash = jsSha3.sha3_256(testStr);
    console.log('  Hash:', hash);
    console.log('  Match:', hash === challenge);
}

if (typeof jsSha3.keccak512 === 'function') {
    console.log('\nkeccak512 (first 32 bytes):');
    const hash = jsSha3.keccak512(testStr).slice(0, 64);
    console.log('  Hash:', hash);
    console.log('  Match:', hash === challenge);
}

if (typeof jsSha3.sha3_512 === 'function') {
    console.log('\nsha3_512 (first 32 bytes):');
    const hash = jsSha3.sha3_512(testStr).slice(0, 64);
    console.log('  Hash:', hash);
    console.log('  Match:', hash === challenge);
}

// Test different input formats
console.log('\n' + '='.repeat(60));
console.log('Testing different input formats:');
console.log('='.repeat(60));

const formats = [
    testStr,
    `${salt}_${expire_at}_${answer}`,
    `${salt}_${answer}`,
    `${expire_at}_${salt}_${answer}`,
    `${answer}`,
    `${salt}`,
];

formats.forEach((fmt, i) => {
    if (typeof jsSha3.keccak256 === 'function') {
        const h = jsSha3.keccak256(fmt);
        console.log(`\nFormat ${i+1}: ${fmt.slice(0, 50)}...`);
        console.log(`  keccak256: ${h}`);
        console.log(`  Match: ${h === challenge}`);
    }
});

// Search for answer
console.log('\n' + '='.repeat(60));
console.log('Searching with keccak256:');
console.log('='.repeat(60));

if (typeof jsSha3.keccak256 === 'function') {
    for (let i = 0; i < 20000; i++) {
        const input = prefix + String(i);
        const h = jsSha3.keccak256(input);
        if (h === challenge) {
            console.log(`*** FOUND! answer = ${i} ***`);
            break;
        }
        if (i % 5000 === 0) {
            console.log(`Progress: ${i}`);
        }
    }
    console.log('Done.');
}