#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试 - 包括流式响应解析验证
"""

import sys
import os
import json
import base64

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))

# 加载 token
token_file = os.path.join(script_dir, 'deepseek_login.json')
with open(token_file, 'r', encoding='utf-8') as f:
    token_data = json.load(f)
    token = token_data.get('token', '')

print('=' * 60)
print('完整流程测试 - 包含响应解析')
print('=' * 60)

from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 创建 session
print('\n1. 创建 session...')
session_id = api.create_session()
print(f'  session_id: {session_id}')

# 发送消息并解析响应
print('\n2. 发送消息...')
response = api.send_message_stream('你好，请思考一下什么是人工智能，然后回答', thinking=True)

current_fragment_type = None
thinking_content = ""
response_content = ""

print('  接收响应:')
for line in response.iter_lines(decode_unicode=True):
    if line and line.startswith('data: '):
        data_str = line[6:]
        if data_str == '[DONE]':
            continue

        try:
            data = json.loads(data_str)

            # 初始化响应结构
            if 'v' in data and isinstance(data['v'], dict):
                response_obj = data['v'].get('response', {})
                fragments = response_obj.get('fragments', [])
                if fragments:
                    last_fragment = fragments[-1]
                    current_fragment_type = last_fragment.get('type', 'RESPONSE')
                    initial_content = last_fragment.get('content', '')
                    if current_fragment_type == 'THINK':
                        thinking_content += initial_content
                    else:
                        response_content += initial_content

            # 切换 fragment
            elif data.get('p') == 'response/fragments' and data.get('o') == 'APPEND':
                new_fragments = data.get('v', [])
                if new_fragments:
                    last_new = new_fragments[-1]
                    current_fragment_type = last_new.get('type', 'RESPONSE')
                    initial_content = last_new.get('content', '')
                    if current_fragment_type == 'RESPONSE':
                        response_content += initial_content

            # 内容更新
            elif 'v' in data and isinstance(data['v'], str):
                text = data['v']
                p = data.get('p', '')

                if p.startswith('response/fragments') or p == '':
                    if current_fragment_type == 'THINK':
                        thinking_content += text
                    elif current_fragment_type == 'RESPONSE':
                        response_content += text

        except json.JSONDecodeError:
            pass

print('\n' + '=' * 60)
print('解析结果:')
print('=' * 60)

if thinking_content:
    print(f'思考内容 (THINK):')
    print(f'  {thinking_content[:200]}...' if len(thinking_content) > 200 else f'  {thinking_content}')
else:
    print('思考内容 (THINK): 无')

print(f'\n回复内容 (RESPONSE):')
print(f'  {response_content[:500]}...' if len(response_content) > 500 else f'  {response_content}')

print('\n' + '=' * 60)
print('测试完成!')
print('=' * 60)