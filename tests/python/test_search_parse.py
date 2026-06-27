#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试联网搜索解析逻辑
"""

import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

# 模拟联网搜索响应数据
test_chunks = [
    'data: {"v":{"response":{"message_id":2,"fragments":[{"id":2,"type":"SEARCH","results":[]}]}}}',
    'data: {"p":"response/fragments/-1/results","v":[{"url":"http://example.com"}]}',
    'data: {"p":"response/fragments/-1/status","v":"FINISHED"}',
    'data: {"p":"response","o":"BATCH","v":[{"p":"fragments","o":"APPEND","v":[{"id":3,"type":"RESPONSE","content":""}]}]}',
    'data: {"p":"response/fragments/-1/content","o":"APPEND","v":"今天"}',
    'data: {"v":"北京"}',
    'data: {"v":"天气"}',
    'data: {"v":"晴"}',
    'data: {"p":"response/status","o":"SET","v":"FINISHED"}',
]

current_fragment_type = None
current_response = ""

print('=' * 60)
print('测试联网搜索解析')
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
                    print(f'[INIT] fragment_type={current_fragment_type}')

            # 2. BATCH 批量操作
            elif data.get('p') == 'response' and data.get('o') == 'BATCH':
                batch_ops = data.get('v', [])
                for op in batch_ops:
                    if op.get('p') == 'fragments' and op.get('o') == 'APPEND':
                        new_fragments = op.get('v', [])
                        if new_fragments:
                            last_new = new_fragments[-1]
                            current_fragment_type = last_new.get('type', 'RESPONSE')
                            print(f'[BATCH] fragment_type={current_fragment_type}')

            # 3. 内容更新
            elif 'v' in data and isinstance(data['v'], str):
                text = data['v']
                p = data.get('p', '')

                if p.startswith('response/fragments') or p == '':
                    if current_fragment_type == 'RESPONSE':
                        current_response += text
                        print(f'[TEXT] type=RESPONSE, text="{text}"')
                    elif current_fragment_type == 'SEARCH':
                        print(f'[TEXT] type=SEARCH, ignored text="{text[:20]}"...')
                    else:
                        print(f'[TEXT] type={current_fragment_type}, text="{text}"')

        except json.JSONDecodeError:
            pass

print('\n' + '=' * 60)
print('结果:')
print('=' * 60)
print(f'最终响应: {current_response}')
print(f'预期: 今天北京天气晴')
print(f'匹配: {current_response == "今天北京天气晴"}')