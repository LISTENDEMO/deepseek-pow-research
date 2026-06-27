#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试快速模式和专家模式
"""

import sys
import os
import json

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))

# 加载 token
token_file = os.path.join(script_dir, 'deepseek_login.json')
with open(token_file, 'r', encoding='utf-8') as f:
    token_data = json.load(f)
    token = token_data.get('token', '')

print('=' * 60)
print('测试快速模式和专家模式')
print('=' * 60)

from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 创建 session
print('\n1. 创建 session...')
session_id = api.create_session()
print(f'  session_id: {session_id}')

# 测试快速模式
print('\n2. 快速模式 (default) 测试:')
response = api.send_message_stream('你好', thinking=False, model_type='default', search_enabled=False)

content = ""
for line in response.iter_lines(decode_unicode=True):
    if line and line.startswith('data: ') and 'v' in line:
        try:
            data = json.loads(line[6:])
            if isinstance(data.get('v'), str):
                content += data['v']
        except:
            pass

print(f'  响应: {content[:100]}...' if len(content) > 100 else f'  响应: {content}')

# 创建新 session 测试专家模式
print('\n3. 专家模式 (expert) 测试:')
session_id2 = api.create_session()
print(f'  session_id: {session_id2}')

response = api.send_message_stream('你好，请详细解释什么是量子计算', thinking=True, model_type='expert', search_enabled=False)

content2 = ""
for line in response.iter_lines(decode_unicode=True):
    if line and line.startswith('data: ') and 'v' in line:
        try:
            data = json.loads(line[6:])
            if isinstance(data.get('v'), str):
                content2 += data['v']
        except:
            pass

print(f'  响应: {content2[:200]}...' if len(content2) > 200 else f'  响应: {content2}')

print('\n' + '=' * 60)
print('测试完成!')
print('=' * 60)