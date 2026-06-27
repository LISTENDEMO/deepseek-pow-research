#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查响应中的 message_id
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
print('检查响应中的 message_id')
print('=' * 60)

from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 创建 session
print('\n1. 创建 session...')
session_id = api.create_session()
print(f'  session_id: {session_id}')

# 发送消息并捕获 message_id
print('\n2. 发送消息...')
response = api.send_message_stream('你好', thinking=False, model_type='default', search_enabled=False)

last_message_id = None
for line in response.iter_lines(decode_unicode=True):
    if line:
        print(f'  原始: {line[:100]}...' if len(line) > 100 else f'  原始: {line}')
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                # 检查 message_id
                if isinstance(data.get('v'), dict):
                    response_obj = data['v'].get('response', {})
                    if 'message_id' in response_obj:
                        last_message_id = response_obj['message_id']
                        print(f'  发现 message_id: {last_message_id}')
            except:
                pass

print(f'\n最后 message_id: {last_message_id}')