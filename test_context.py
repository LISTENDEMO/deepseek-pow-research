#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试对话上下文
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
print('测试对话上下文')
print('=' * 60)

from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 创建 session
print('\n1. 创建 session...')
session_id = api.create_session()
print(f'  session_id: {session_id}')

# 第一条消息
print('\n2. 发送第一条消息: "我叫张三"')
api.add_to_history('user', '我叫张三')  # 添加到历史
response = api.send_message_stream('我叫张三', thinking=False, model_type='default', search_enabled=False)

content1 = ""
for line in response.iter_lines(decode_unicode=True):
    if line and line.startswith('data: ') and 'v' in line:
        try:
            data = json.loads(line[6:])
            if isinstance(data.get('v'), str):
                content1 += data['v']
        except:
            pass
print(f'  响应: {content1}')
api.add_to_history('assistant', content1.replace('FINISHED', ''))  # 添加AI响应到历史

# 第二条消息 - 测试上下文
print('\n3. 发送第二条消息: "我叫什么名字？"')
api.add_to_history('user', '我叫什么名字？')  # 添加到历史
response = api.send_message_stream('我叫什么名字？', thinking=False, model_type='default', search_enabled=False)

content2 = ""
for line in response.iter_lines(decode_unicode=True):
    if line and line.startswith('data: ') and 'v' in line:
        try:
            data = json.loads(line[6:])
            if isinstance(data.get('v'), str):
                content2 += data['v']
        except:
            pass
print(f'  响应: {content2}')

print('\n' + '=' * 60)
print('分析:')
print('=' * 60)

print(f'对话历史: {api.messages_history}')

if '张三' in content2:
    print('✓ 有上下文 - AI 记住了名字"张三"')
else:
    print('✗ 无上下文 - AI 不知道名字')