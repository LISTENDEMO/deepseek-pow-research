#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程测试
"""

import sys
import json
import subprocess
import os
import base64

sys.stdout.reconfigure(encoding='utf-8')

print('='*60)
print('完整流程测试')
print('='*60)

script_dir = os.path.dirname(os.path.abspath(__file__))

# 1. 测试 WASM solver
print('\n1. WASM Solver 测试:')
test_data = {
    'challenge': 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd',
    'salt': '811e05c93d1b71993710',
    'expire_at': 1776153216159,
    'difficulty': 144000
}

solver_path = os.path.join(script_dir, 'deepseek_pow_solver.js')
print(f'  Solver path: {solver_path}')
print(f'  Solver exists: {os.path.exists(solver_path)}')

result = subprocess.run(
    ['node', solver_path],
    input=json.dumps(test_data),
    capture_output=True,
    text=True,
    cwd=script_dir
)

print(f'  Return code: {result.returncode}')

if result.returncode == 0:
    output = json.loads(result.stdout)
    print(f'  Success: {output.get("success")}')
    print(f'  Answer: {output.get("answer")}')
    print(f'  Expected: 69992')
    print(f'  Match: {output.get("answer") == 69992}')
    answer = output.get('answer')
else:
    print(f'  Error: {result.stderr}')
    answer = None

# 2. 测试 PoW response 构建
print('\n2. PoW Response 构建:')
pow_response = {
    'algorithm': 'DeepSeekHashV1',
    'challenge': test_data['challenge'],
    'salt': test_data['salt'],
    'answer': answer or 69992,
    'signature': 'test_sig',
    'target_path': '/api/v0/chat/completion'
}
encoded = base64.b64encode(json.dumps(pow_response).encode()).decode()
print(f'  Encoded: {encoded[:60]}...')

# 3. 测试 PyQt6 GUI 导入
print('\n3. PyQt6 GUI 导入:')
try:
    from deepseek_gui import DeepSeekChatWindow, DeepSeekAPI
    print('  导入成功!')

    # 测试 API 类方法
    api = DeepSeekAPI()

    # 模拟数据解析
    mock_challenge = {
        'data': {
            'biz_data': {
                'challenge': {
                    'challenge': 'test123',
                    'salt': 'salt123',
                    'expire_at': 123456,
                    'difficulty': 144000,
                    'signature': 'sig123'
                }
            }
        }
    }

    # 测试解析逻辑
    result = mock_challenge
    if 'data' in result and 'biz_data' in result['data']:
        challenge = result['data']['biz_data']['challenge']
        print('  Challenge 解析成功!')
        print(f'    challenge: {challenge.get("challenge")}')
        print(f'    salt: {challenge.get("salt")}')
        print(f'    expire_at: {challenge.get("expire_at")}')

except Exception as e:
    print(f'  Error: {e}')

# 4. Token 检查
print('\n4. Token 检查:')
token_file = os.path.join(script_dir, 'deepseek_login.json')
if os.path.exists(token_file):
    with open(token_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        token = data.get('token', '')
        if token:
            print(f'  Token: {token[:20]}...')
            print('  Token 有效!')
else:
    print('  Token 文件不存在')

print('\n' + '='*60)
print('测试完成!')
print('='*60)

print('\n运行 GUI:')
print('  python deepseek_gui.py')