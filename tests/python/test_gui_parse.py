#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟 GUI 解析逻辑测试
"""

import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

# 模拟 DeepSeek 流式响应数据 - 包含初始 content
test_chunks = [
    'data: {"v":{"response":{"message_id":2,"fragments":[{"id":2,"type":"RESPONSE","content":"你好"}]}}}',
    'data: {"v":"！"}',
    'data: {"v":"😊"}',
    'data: {"v":" 很高兴见到你"}',
    'data: {"v":"\\n\\n"}',
    'data: {"v":"我是DeepSeek，由深度求索公司创造的AI助手。"}',
]

# GUI 解析逻辑
current_fragment_type = None
current_response = ""
thinking_content = ""

print('=' * 60)
print('模拟 GUI 解析测试')
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
                    initial_content = last_fragment.get('content', '')
                    if initial_content:
                        if current_fragment_type == 'RESPONSE':
                            current_response += initial_content
                            print(f'  初始化 RESPONSE: "{initial_content}"')
                        elif current_fragment_type == 'THINK':
                            thinking_content += initial_content

            # 2. 内容更新
            elif 'v' in data and isinstance(data['v'], str):
                text = data['v']
                if current_fragment_type == 'RESPONSE':
                    current_response += text
                    print(f'  添加内容: "{text}" -> 总长度: {len(current_response)}')

        except json.JSONDecodeError:
            pass

print('\n' + '=' * 60)
print('解析结果:')
print('=' * 60)
print(f'完整回复: {current_response}')

expected = "你好！😊 很高兴见到你\n\n我是DeepSeek，由深度求索公司创造的AI助手。"
print(f'\n验证: "{current_response}" == "{expected}" ? {current_response == expected}')