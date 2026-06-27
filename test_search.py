#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试联网搜索响应格式
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
print('测试联网搜索响应格式')
print('=' * 60)

from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 创建 session
print('\n1. 创建 session...')
session_id = api.create_session()
print(f'  session_id: {session_id}')

# 测试联网搜索
print('\n2. 发送消息 (联网搜索): "今天北京天气"')
response = api.send_message_stream('今天北京天气', thinking=False, model_type='default', search_enabled=True)

print('\n原始响应:')
for line in response.iter_lines(decode_unicode=True):
    if line:
        print(f'  {line[:100]}...' if len(line) > 100 else f'  {line}')

print('\n' + '=' * 60)