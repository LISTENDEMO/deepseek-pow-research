#!/usr/bin/env python3
"""
DeepSeek PoW Verification - Test multiple hash algorithms and formats
"""

import hashlib
import base64
import json

# Test data from API response
test_cases = [
    # From task output
    {
        "challenge": "6f03c2942e31a4c67fea7c3ee3184bb22bc32e9da51da1984f1a7fbb675c8531",
        "salt": "e35f5bc86e49d6101fa6",
        "expire_at": 1776156337056,
        "difficulty": 144000,
    },
    # From summary data (need expire_at)
    {
        "challenge": "252f029a65d33fade32803d2f3bf23363584bda3be0e3110261659f9208107c1",
        "salt": "a9171b4026f92b32024f",
        "answer": 83094,
        "expire_at": None,  # Need to find this
    },
]

def test_hash_algorithms(prefix: str, answer: int, target: str):
    """Test various hash algorithms"""
    test_str = prefix + str(answer)

    results = {}

    # SHA3-256 (padding=6)
    sha3_hash = hashlib.sha3_256(test_str.encode()).hexdigest()
    results['sha3_256'] = sha3_hash

    # SHA256 (different from SHA3)
    sha256_hash = hashlib.sha256(test_str.encode()).hexdigest()
    results['sha256'] = sha256_hash

    # Keccak256 using pycryptodome if available
    try:
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(test_str.encode())
        keccak_hash = k.hexdigest()
        results['keccak256'] = keccak_hash
    except ImportError:
        results['keccak256'] = "pycryptodome not installed"

    # Check matches
    for name, hash_val in results.items():
        if hash_val == target:
            print(f"  ✓ MATCH: {name} - {test_str}")
            return name, True

    return results, False

def find_answer(prefix: str, target: str, difficulty: int):
    """Search for answer using SHA3-256"""
    import time
    start = time.time()

    for i in range(difficulty):
        test_str = prefix + str(i)
        hash_val = hashlib.sha3_256(test_str.encode()).hexdigest()
        if hash_val == target:
            elapsed = time.time() - start
            print(f"Found answer: {i} in {elapsed:.2f}s")
            return i

    elapsed = time.time() - start
    print(f"Not found after {elapsed:.2f}s (searched 0-{difficulty})")
    return None

def main():
    print("=" * 60)
    print("DeepSeek PoW Verification")
    print("=" * 60)

    # Test case 1 - we have all data
    tc1 = test_cases[0]

    # Various prefix formats to test
    prefix_formats = [
        f"{tc1['salt']}_{tc1['expire_at']}_",  # Standard format
        f"{tc1['salt']}{tc1['expire_at']}",     # No underscores
        f"{tc1['salt']}_",                       # Just salt
        f"{tc1['expire_at']}_",                  # Just expire
        tc1['salt'],                             # Only salt
    ]

    print("\nTesting Case 1:")
    print(f"  Challenge: {tc1['challenge'][:20]}...")
    print(f"  Salt: {tc1['salt']}")
    print(f"  Expire_at: {tc1['expire_at']}")
    print(f"  Difficulty: {tc1['difficulty']}")

    # Test first few answers with each format
    for prefix in prefix_formats:
        print(f"\n  Prefix: {prefix[:30]}...")
        for answer in [0, 1, 10, 100]:
            results, matched = test_hash_algorithms(prefix, answer, tc1['challenge'])
            if matched:
                break
            if answer == 0:
                print(f"    Answer=0: sha3={results['sha3_256'][:20]}...")

    # Full search with standard format
    print("\n\nFull search with standard prefix format:")
    standard_prefix = f"{tc1['salt']}_{tc1['expire_at']}_"
    print(f"  Prefix: {standard_prefix}")

    # Sample hashes
    for i in [0, 100, 1000, 10000]:
        test_str = standard_prefix + str(i)
        h = hashlib.sha3_256(test_str.encode()).hexdigest()
        print(f"  prefix+{i}: {h[:20]}...")

    print(f"\n  Target: {tc1['challenge'][:20]}...")

    # Search
    answer = find_answer(standard_prefix, tc1['challenge'], tc1['difficulty'])

    if answer is None:
        print("\n  Trying different formats...")
        # Maybe prefix doesn't include expire_at?
        for prefix in [tc1['salt'], f"{tc1['salt']}_"]:
            print(f"\n  Testing prefix: {prefix}")
            answer = find_answer(prefix, tc1['challenge'], min(tc1['difficulty'], 1000))
            if answer:
                break

    # Test case 2 - we have answer, need to verify
    print("\n\n" + "=" * 60)
    print("Testing Case 2 (known answer):")
    tc2 = test_cases[1]
    print(f"  Challenge: {tc2['challenge'][:20]}...")
    print(f"  Salt: {tc2['salt']}")
    print(f"  Known Answer: {tc2['answer']}")

    # We need expire_at - estimate from timestamp pattern
    # expire_at is typically around 5 minutes ahead in milliseconds
    # Let's try some plausible values

    print("\n  Searching for correct expire_at...")
    # expire_at format: milliseconds since epoch
    # From telemetry, timestamps were around 1776155xxx range

    for expire_at in range(1776155800000, 1776156400000, 1000):
        prefix = f"{tc2['salt']}_{expire_at}_"
        test_str = prefix + str(tc2['answer'])
        h = hashlib.sha3_256(test_str.encode()).hexdigest()
        if h == tc2['challenge']:
            print(f"  ✓ FOUND! expire_at = {expire_at}")
            print(f"  Prefix: {prefix}")
            print(f"  Full string: {test_str}")
            break

if __name__ == "__main__":
    main()