#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
捕获原始响应数据测试
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
print('捕获原始响应数据')
print('=' * 60)

from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 创建 session
print('\n1. 创建 session...')
session_id = api.create_session()
print(f'  session_id: {session_id}')

# 发送消息并记录所有原始数据
print('\n2. 发送消息...')
response = api.send_message_stream('你好', thinking=False)

print('\n原始响应数据:')
print('-' * 60)

raw_chunks = []
for line in response.iter_lines(decode_unicode=True):
    if line:
        raw_chunks.append(line)
        print(line)

print('-' * 60)
print(f'\n总共收到 {len(raw_chunks)} 行数据')

# 解析分析
print('\n解析分析:')
print('=' * 60)

current_fragment_type = None
current_response = ""
thinking_content = ""

for chunk in raw_chunks:
    if chunk.startswith('data: '):
        data_str = chunk[6:]
        if data_str == '[DONE]':
            continue

        try:
            data = json.loads(data_str)

            # 1. 初始化响应结构
            if 'v' in data and isinstance(data['v'], dict):
                response_obj = data['v'].get('response', {})
                fragments = response_obj.get('fragments', [])
                if fragments:
                    last_fragment = fragments[-1]
                    current_fragment_type = last_fragment.get('type', 'RESPONSE')
                    initial_content = last_fragment.get('content', '')
                    if initial_content:
                        if current_fragment_type == 'RESPONSE':
                            current_response += initial_content
                            print(f'[INIT] fragment_type={current_fragment_type}, content="{initial_content}"')
                        elif current_fragment_type == 'THINK':
                            thinking_content += initial_content
                            print(f'[INIT] fragment_type={current_fragment_type}, content="{initial_content[:30]}..."')

            # 2. 切换 fragment
            elif data.get('p') == 'response/fragments' and data.get('o') == 'APPEND':
                new_fragments = data.get('v', [])
                if new_fragments:
                    last_new = new_fragments[-1]
                    current_fragment_type = last_new.get('type', 'RESPONSE')
                    initial_content = last_new.get('content', '')
                    print(f'[SWITCH] fragment_type={current_fragment_type}, content="{initial_content}"')
                    if initial_content and current_fragment_type == 'RESPONSE':
                        current_response += initial_content

            # 3. 内容更新
            elif 'v' in data and isinstance(data['v'], str):
                text = data['v']
                p = data.get('p', '')

                if p.startswith('response/fragments') or p == '':
                    if current_fragment_type == 'RESPONSE':
                        current_response += text
                        print(f'[TEXT] type=RESPONSE, text="{text}"')
                    elif current_fragment_type == 'THINK':
                        thinking_content += text
                        print(f'[TEXT] type=THINK, text="{text[:30]}..."')

        except json.JSONDecodeError as e:
            print(f'[ERROR] JSON解析失败: {e}')

print('\n' + '=' * 60)
print('最终结果:')
print('=' * 60)
print(f'回复内容 (长度={len(current_response)}):')
print(current_response)
if thinking_content:
    print(f'\n思考内容 (长度={len(thinking_content)}):')
    print(thinking_content[:100] + '...')