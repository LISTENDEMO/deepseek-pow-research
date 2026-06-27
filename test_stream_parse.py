#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试流式响应解析
"""

import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

# 模拟 DeepSeek 流式响应数据
test_chunks = [
    'event: ready',
    'data: {"request_message_id":5,"response_message_id":6}',
    'event: update_session',
    'data: {"updated_at":1776165770.428922}',
    'data: {"v":{"response":{"message_id":6,"fragments":[{"id":2,"type":"THINK","content":"我们"}]}}}',
    'data: {"v":"注意到"}',
    'data: {"v":"用户"}',
    'data: {"v":"说"}',
    'data: {"v":"了"}',
    'data: {"v":"问候"}',
    'data: {"p":"response/fragments","o":"APPEND","v":[{"id":3,"type":"RESPONSE","content":"你好"}]}',
    'data: {"v":"！"}',
    'data: {"v":"很高兴"}',
    'data: {"v":"见到"}',
    'data: {"v":"你"}',
    'data: {"v":"\\n\\n"}',
    'data: {"v":"有什么"}',
    'data: {"v":"问题"}',
    'data: {"v":"吗"}',
    'data: {"v":"？"}',
    'data: {"p":"response/status","o":"SET","v":"FINISHED"}',
    'event: close',
]

# 解析逻辑
current_fragment_type = None
thinking_content = ""
response_content = ""

print('=' * 60)
print('测试流式响应解析')
print('=' * 60)

for chunk in test_chunks:
    if chunk.startswith('data: '):
        data_str = chunk[6:]
        try:
            data = json.loads(data_str)

            # 1. 初始化响应结构
            if 'v' in data and isinstance(data['v'], dict):
                response = data['v'].get('response', {})
                fragments = response.get('fragments', [])
                if fragments:
                    last_fragment = fragments[-1]
                    current_fragment_type = last_fragment.get('type', 'RESPONSE')
                    print(f'  初始化 fragment 类型: {current_fragment_type}')
                    # 提取初始内容
                    initial_content = last_fragment.get('content', '')
                    if current_fragment_type == 'THINK':
                        thinking_content += initial_content
                    else:
                        response_content += initial_content

            # 2. 添加新 fragment
            elif data.get('p') == 'response/fragments' and data.get('o') == 'APPEND':
                new_fragments = data.get('v', [])
                if new_fragments:
                    last_new = new_fragments[-1]
                    current_fragment_type = last_new.get('type', 'RESPONSE')
                    print(f'  切换 fragment 类型: {current_fragment_type}')
                    # 提取新 fragment 初始内容
                    initial_content = last_new.get('content', '')
                    if current_fragment_type == 'RESPONSE':
                        response_content += initial_content

            # 3. 内容更新
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
print(f'思考内容 (THINK): {thinking_content}')
print(f'回复内容 (RESPONSE): {response_content}')

expected_thinking = "我们注意到用户说了问候"
expected_response = "你好！很高兴见到你\n\n有什么问题吗？"

print('\n验证:')
print(f'  THINK: "{thinking_content}" == "{expected_thinking}" ? {thinking_content == expected_thinking}')
print(f'  RESPONSE: "{response_content}" == "{expected_response}" ? {response_content == expected_response}')