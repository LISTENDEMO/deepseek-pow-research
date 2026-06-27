#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的 API 流程
"""

import sys
import os
import json
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))

print('=' * 60)
print('测试修复后的 API 流程')
print('=' * 60)

# 加载 token
token_file = os.path.join(script_dir, 'deepseek_login.json')
if not os.path.exists(token_file):
    print('错误: Token 文件不存在')
    sys.exit(1)

with open(token_file, 'r', encoding='utf-8') as f:
    token_data = json.load(f)
    token = token_data.get('token', '')

if not token:
    print('错误: Token 无效')
    sys.exit(1)

print(f'Token: {token[:20]}...')

# 导入修复后的 API
from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 测试 headers
print('\nHeaders:')
for key, value in api.default_headers.items():
    if key == 'Authorization':
        print(f'  {key}: Bearer {token[:20]}...')
    else:
        print(f'  {key}: {value}')

# 1. 测试 PoW challenge
print('\n1. 获取 PoW challenge...')
try:
    challenge_data = api.get_pow_challenge()
    print('  成功!')
    print(f'  challenge: {challenge_data.get("challenge", "")[:20]}...')
    print(f'  salt: {challenge_data.get("salt", "")}')
    print(f'  difficulty: {challenge_data.get("difficulty", "")}')
    print(f'  algorithm: {challenge_data.get("algorithm", "")}')
    print(f'  target_path: {challenge_data.get("target_path", "")}')
except Exception as e:
    print(f'  错误: {e}')
    sys.exit(1)

# 2. 测试 WASM solver
print('\n2. 解决 PoW...')
try:
    pow_solution = api.solve_pow_with_wasm(challenge_data)
    print('  成功!')
    print(f'  answer: {pow_solution.get("answer")}')
except Exception as e:
    print(f'  错误: {e}')
    sys.exit(1)

# 3. 测试 session 创建
print('\n3. 创建 session...')
try:
    session_id = api.create_session()
    print('  成功!')
    print(f'  session_id: {session_id}')
except Exception as e:
    print(f'  错误: {e}')
    sys.exit(1)

# 4. 测试发送消息
print('\n4. 发送测试消息...')
try:
    response = api.send_message_stream('你好', thinking=False)
    print('  成功! 开始接收响应...')

    # 读取流式响应
    full_response = ''
    for line in response.iter_lines(decode_unicode=True):
        if line:
            print(f'  收到: {line[:50]}...' if len(line) > 50 else f'  收到: {line}')
            if line.startswith('data: '):
                data_str = line[6:]
                if data_str == '[DONE]':
                    break
                try:
                    data = json.loads(data_str)
                    if 'choices' in data:
                        for choice in data['choices']:
                            if 'delta' in choice and 'content' in choice['delta']:
                                full_response += choice['delta']['content']
                except:
                    pass

    print(f'\n  完整响应: {full_response[:200]}...' if len(full_response) > 200 else f'\n  完整响应: {full_response}')

except Exception as e:
    print(f'  错误: {e}')
    sys.exit(1)

print('\n' + '=' * 60)
print('所有测试通过!')
print('=' * 60)