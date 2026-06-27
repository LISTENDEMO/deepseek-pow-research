#!/usr/bin/env node
/**
 * Use js-sha3 directly and verify its correctness
 */

const crypto = require('crypto');

// Import js-sha3
let jsSha3;
try {
    jsSha3 = require('./node_modules/js-sha3/build/sha3.min.js');
} catch (e) {
    try {
        jsSha3 = require('./node_modules/js-sha3/src/sha3.js');
    } catch (e2) {
        console.log('Cannot load js-sha3:', e2.message);
        process.exit(1);
    }
}

console.log('='.repeat(60));
console.log('js-sha3 Library Verification');
console.log('='.repeat(60));

// Test SHA3-256 empty
console.log('\nSHA3-256("") test:');
const emptyJs = jsSha3.sha3_256('');
const emptyCrypto = crypto.createHash('sha3-256').update('').digest('hex');
console.log('  js-sha3:', emptyJs);
console.log('  Node.js:', emptyCrypto);
console.log('  Match:', emptyJs === emptyCrypto);
console.log('  Known:', emptyJs === 'a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a');

// Test SHA3-256 "abc"
console.log('\nSHA3-256("abc") test:');
const abcJs = jsSha3.sha3_256('abc');
const abcCrypto = crypto.createHash('sha3-256').update('abc').digest('hex');
console.log('  js-sha3:', abcJs);
console.log('  Node.js:', abcCrypto);
console.log('  Match:', abcJs === abcCrypto);
console.log('  Known:', abcJs === '3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532');

// Test Keccak-256 (pre-SHA3)
console.log('\nKeccak-256("") test:');
const keccakEmpty = jsSha3.keccak256('');
console.log('  js-sha3 keccak256:', keccakEmpty);
console.log('  Known (Keccak256): c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470');

// DeepSeek test
console.log('\n' + '='.repeat(60));
console.log('DeepSeek PoW Test');
console.log('='.repeat(60));

const challenge = 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd';
const salt = '811e05c93d1b71993710';
const expire_at = 1776153216159;
const answer = 69992;
const prefix = `${salt}_${expire_at}_`;
const testStr = prefix + String(answer);

console.log('\nInput:', testStr);
console.log('Target:', challenge);

console.log('\njs-sha3 sha3_256:', jsSha3.sha3_256(testStr));
console.log('js-sha3 keccak256:', jsSha3.keccak256(testStr));
console.log('Node.js sha3_256:', crypto.createHash('sha3-256').update(testStr).digest('hex'));

// Try different formats
console.log('\nTrying different input formats:');
const formats = [
    testStr,
    `${salt}_${expire_at}_${answer}`,
    `${salt}_${answer}`,
    prefix,
];

formats.forEach((fmt, i) => {
    console.log(`\nFormat ${i+1}: "${fmt}"`);
    console.log('  sha3_256:', jsSha3.sha3_256(fmt));
    console.log('  keccak256:', jsSha3.keccak256(fmt));
    console.log('  Match challenge:', jsSha3.sha3_256(fmt) === challenge || jsSha3.keccak256(fmt) === challenge);
});