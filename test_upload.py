#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件上传功能
"""

import sys
import os
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))

# 加载 token
token_file = os.path.join(script_dir, 'deepseek_login.json')
with open(token_file, 'r', encoding='utf-8') as f:
    token_data = json.load(f)
    token = token_data.get('token', '')

print('=' * 60)
print('测试文件上传功能')
print('=' * 60)

from deepseek_gui import DeepSeekAPI

api = DeepSeekAPI(token)

# 创建 session
print('\n1. 创建 session...')
session_id = api.create_session()
print(f'  session_id: {session_id}')

# 创建测试文件
test_file_path = os.path.join(script_dir, 'test_upload.txt')
with open(test_file_path, 'w', encoding='utf-8') as f:
    f.write('这是一个测试文件的内容。\n测试上传功能。')

print(f'\n2. 创建测试文件: {test_file_path}')

# 上传文件
print('\n3. 上传文件...')
try:
    result = api.upload_file(test_file_path)
    print(f'  成功!')
    print(f'  file_id: {result.get("file_id")}')
    print(f'  file_name: {result.get("file_name")}')
    print(f'  status: {result.get("status")}')
except Exception as e:
    print(f'  上传错误: {e}')
    result = None

# 等待文件解析完成
if result and result.get('file_id'):
    file_id = result.get('file_id')
    print('\n4. 等待文件解析...')
    try:
        api.wait_for_file_parsed(file_id, timeout=30)
        print('  解析完成!')
    except Exception as e:
        print(f'  等待解析错误: {e}')

    # 发送带附件的消息
    print('\n5. 发送带附件的消息...')
    try:
        file_ids = [file_id]
        response = api.send_message_stream('请读取我上传的文件内容并告诉我写了什么', thinking=False, model_type='default', search_enabled=False, file_ids=file_ids)

        content = ""
        message_id = None
        current_fragment_type = None

        for line in response.iter_lines(decode_unicode=True):
            if line:
                print(f'  [收到] {line[:80]}...' if len(line) > 80 else f'  [收到] {line}')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        # 解析响应
                        if isinstance(data.get('v'), dict):
                            response_obj = data['v'].get('response', {})
                            fragments = response_obj.get('fragments', [])
                            if fragments:
                                current_fragment_type = fragments[-1].get('type', 'RESPONSE')
                            if 'message_id' in response_obj:
                                message_id = response_obj['message_id']
                        # 内容更新
                        if isinstance(data.get('v'), str) and current_fragment_type == 'RESPONSE':
                            content += data['v']
                    except json.JSONDecodeError:
                        pass

        print(f'\n  响应内容: {content[:200]}...' if len(content) > 200 else f'\n  响应内容: {content}')
        print(f'  message_id: {message_id}')
    except Exception as e:
        print(f'  发送消息错误: {e}')

# 清理测试文件
if os.path.exists(test_file_path):
    os.remove(test_file_path)
print('\n6. 清理测试文件')

print('\n' + '=' * 60)
print('测试完成!')
print('=' * 60)