#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API Client - 独立 API 模块
供 Claude Code 或其他程序调用

配置:
    - token: DeepSeek Bearer token (从 Web 登录获取)
    - base_url: API 服务器地址，默认 https://chat.deepseek.com
    - solver_path: PoW solver 路径，默认同目录的 deepseek_pow_solver.js

使用方式:

    # 方式 1: 自动加载 token 文件
    from deepseek_api import DeepSeekAPI
    api = DeepSeekAPI()
    api.load_token_from_file()  # 从 deepseek_login.json 加载

    # 方式 2: 手动配置
    api = DeepSeekAPI(
        token='Bearer xxx...',
        base_url='https://chat.deepseek.com'
    )

    # 方式 3: 动态设置
    api = DeepSeekAPI()
    api.set_token('Bearer xxx...')
    api.set_base_url('https://your-proxy.com')

聊天:
    # 流式响应
    for chunk in api.chat_stream("你好"):
        print(chunk, end='', flush=True)

    # 完整响应
    result = api.chat("你好")
    print(result['content'])

文件上传:
    file_info = api.upload_file("document.pdf")
    result = api.chat("分析这个文件", file_ids=[file_info['file_id']])
"""

import os
import json
import base64
import subprocess
import requests


class DeepSeekAPI:
    """DeepSeek API 客户端 - 独立模块"""

    def __init__(self, token=None, base_url=None, solver_path=None):
        """
        初始化 API 客户端

        Args:
            token: DeepSeek API token (Bearer token)
            base_url: API 基础 URL，默认 https://chat.deepseek.com
            solver_path: PoW solver 路径，默认同目录下的 deepseek_pow_solver.js
        """
        self.base_url = base_url or 'https://chat.deepseek.com'
        self.token = token
        self.session_id = None
        self.parent_message_id = None
        self.messages_history = []

        # solver 路径
        if solver_path:
            self.solver_path = solver_path
        else:
            # 默认同目录
            self.solver_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'deepseek_pow_solver.js'
            )

        self.default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/',
            'x-app-version': '20241129.1',
            'x-client-locale': 'zh_CN',
            'x-client-platform': 'web',
            'x-client-timezone-offset': '28800',
            'x-client-version': '1.8.0',
        }

        if token:
            self.default_headers['Authorization'] = f'Bearer {token}'

    def set_token(self, token):
        """设置 API token"""
        self.token = token
        self.default_headers['Authorization'] = f'Bearer {token}'

    def load_token_from_file(self, file_path=None):
        """从 JSON 文件加载配置（token 和 base_url）

        Args:
            file_path: 配置文件路径，默认同目录的 deepseek_login.json
        """
        if file_path is None:
            file_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'deepseek_login.json'
            )

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                token = data.get('token')
                base_url = data.get('base_url')

                if token:
                    self.set_token(token)
                if base_url:
                    self.set_base_url(base_url)

                return bool(token)
        return False

    def set_base_url(self, base_url):
        """设置 API 基础 URL"""
        self.base_url = base_url
        self.default_headers['Origin'] = base_url
        self.default_headers['Referer'] = f'{base_url}/'

    def clear_history(self):
        """清空对话历史"""
        self.messages_history = []
        self.parent_message_id = None

    def get_pow_challenge(self, target_path='/api/v0/chat/completion'):
        """获取 PoW challenge"""
        url = f'{self.base_url}/api/v0/chat/create_pow_challenge'
        headers = self.default_headers.copy()
        data = {'target_path': target_path}

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 429:
            raise Exception('Rate Limit (429)')
        if response.status_code != 200:
            raise Exception(f'获取 challenge 失败: {response.status_code}')

        result = response.json()
        if 'data' in result and 'biz_data' in result['data']:
            return result['data']['biz_data']['challenge']
        elif 'data' in result:
            return result['data']
        return result

    def solve_pow_with_wasm(self, challenge_data):
        """使用 Node.js WASM solver 解决 PoW"""
        challenge = challenge_data.get('challenge')
        salt = challenge_data.get('salt')
        expire_at = challenge_data.get('expire_at')
        difficulty = challenge_data.get('difficulty', 144000)
        signature = challenge_data.get('signature')  # 必须包含 signature
        algorithm = challenge_data.get('algorithm', 'DeepSeekHashV1')
        target_path = challenge_data.get('target_path', '/api/v0/chat/completion')

        solver_input = json.dumps({
            'challenge': challenge,
            'salt': salt,
            'expire_at': expire_at,
            'difficulty': difficulty
        })

        result = subprocess.run(
            ['node', self.solver_path],
            input=solver_input,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(self.solver_path)
        )

        if result.returncode != 0:
            raise Exception(f'Solver 失败: {result.stderr}')

        solver_output = json.loads(result.stdout)
        if not solver_output.get('success'):
            raise Exception(f'未找到解: {solver_output}')

        return {
            'algorithm': algorithm,
            'challenge': challenge,
            'salt': salt,
            'answer': solver_output['answer'],
            'signature': signature,  # 必须包含
            'target_path': target_path
        }

    def create_session(self):
        """创建聊天 session"""
        url = f'{self.base_url}/api/v0/chat_session/create'
        headers = self.default_headers.copy()

        response = requests.post(url, headers=headers, json={})
        if response.status_code == 429:
            raise Exception('Rate Limit (429)')
        if response.status_code != 200:
            raise Exception(f'创建 session 失败: {response.status_code}')

        result = response.json()
        if 'data' in result and 'biz_data' in result['data']:
            biz_data = result['data']['biz_data']
            chat_session = biz_data.get('chat_session', {})
            self.session_id = chat_session.get('id') or biz_data.get('id')
        else:
            self.session_id = result.get('data', {}).get('session_id')

        if not self.session_id:
            raise Exception(f'无法获取 session_id')

        return self.session_id

    def send_message_stream(self, message, thinking=False, model_type='default',
                            search_enabled=False, file_ids=None):
        """发送消息并返回流式响应

        Returns:
            requests.Response: 流式响应对象，可用 iter_lines() 遍历
        """
        if not self.session_id:
            self.create_session()

        url = f'{self.base_url}/api/v0/chat/completion'

        # PoW
        challenge_data = self.get_pow_challenge()
        pow_solution = self.solve_pow_with_wasm(challenge_data)

        headers = self.default_headers.copy()
        headers['x-ds-pow-response'] = base64.b64encode(
            json.dumps(pow_solution).encode()
        ).decode()

        messages = self.messages_history.copy()
        messages.append({'role': 'user', 'content': message})

        data = {
            'chat_session_id': self.session_id,
            'parent_message_id': self.parent_message_id,
            'model_type': model_type,
            'prompt': message,
            'messages': messages,
            'ref_file_ids': file_ids or [],
            'thinking_enabled': thinking,
            'search_enabled': search_enabled,
            'preempt': False
        }

        response = requests.post(url, headers=headers, json=data, stream=True)
        if response.status_code == 429:
            raise Exception('Rate Limit (429)')
        if response.status_code != 200:
            raise Exception(f'发送失败: {response.status_code}')

        return response

    def chat_stream(self, message, thinking=False, model_type='default',
                    search_enabled=False, file_ids=None):
        """聊天流式响应 - 生成器方式

        Yields:
            str: 响应文本片段
        """
        response = self.send_message_stream(
            message, thinking, model_type, search_enabled, file_ids
        )

        current_fragment_type = None
        full_response = ""
        message_id = None

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            if line.startswith('event:'):
                continue

            if line.startswith('data:'):
                data_str = line[6:]
                if data_str == '[DONE]':
                    break

                try:
                    data = json.loads(data_str)

                    # 初始化响应结构
                    if isinstance(data.get('v'), dict):
                        resp = data['v'].get('response', {})
                        fragments = resp.get('fragments', [])
                        if fragments:
                            current_fragment_type = fragments[-1].get('type', 'RESPONSE')
                        if 'message_id' in resp:
                            message_id = resp['message_id']

                    # BATCH 操作
                    elif data.get('p') == 'response' and data.get('o') == 'BATCH':
                        for op in data.get('v', []):
                            if op.get('p') == 'fragments' and op.get('o') == 'APPEND':
                                new_frags = op.get('v', [])
                                if new_frags:
                                    current_fragment_type = new_frags[-1].get('type', 'RESPONSE')

                    # 内容更新
                    elif isinstance(data.get('v'), str):
                        if current_fragment_type == 'RESPONSE':
                            yield data['v']
                            full_response += data['v']

                except json.JSONDecodeError:
                    pass

        # 保存历史
        if message_id:
            self.parent_message_id = message_id
        if full_response:
            self.messages_history.append({'role': 'user', 'content': message})
            self.messages_history.append({'role': 'assistant', 'content': full_response})

    def chat(self, message, thinking=False, model_type='default',
             search_enabled=False, file_ids=None):
        """聊天 - 返回完整响应

        Returns:
            dict: {'content': 响应内容, 'message_id': 消息ID}
        """
        response = self.send_message_stream(
            message, thinking, model_type, search_enabled, file_ids
        )

        current_fragment_type = None
        content = ""
        message_id = None

        for line in response.iter_lines(decode_unicode=True):
            if not line or line.startswith('event:'):
                continue

            if line.startswith('data:'):
                data_str = line[6:]
                if data_str == '[DONE]':
                    break

                try:
                    data = json.loads(data_str)

                    if isinstance(data.get('v'), dict):
                        resp = data['v'].get('response', {})
                        fragments = resp.get('fragments', [])
                        if fragments:
                            current_fragment_type = fragments[-1].get('type', 'RESPONSE')
                        if 'message_id' in resp:
                            message_id = resp['message_id']

                    elif data.get('p') == 'response' and data.get('o') == 'BATCH':
                        for op in data.get('v', []):
                            if op.get('p') == 'fragments' and op.get('o') == 'APPEND':
                                new_frags = op.get('v', [])
                                if new_frags:
                                    current_fragment_type = new_frags[-1].get('type', 'RESPONSE')

                    elif isinstance(data.get('v'), str):
                        # 过滤状态字符串
                        if data['v'] in ('FINISHED', 'SUCCESS', 'PENDING'):
                            continue
                        if current_fragment_type == 'RESPONSE':
                            content += data['v']

                except json.JSONDecodeError:
                    pass

        # 保存历史
        if message_id:
            self.parent_message_id = message_id
        if content:
            self.messages_history.append({'role': 'user', 'content': message})
            self.messages_history.append({'role': 'assistant', 'content': content})

        return {'content': content, 'message_id': message_id}

    def upload_file(self, file_path, wait_for_parse=True, timeout=30):
        """上传文件

        Args:
            file_path: 文件路径
            wait_for_parse: 是否等待解析完成
            timeout: 解析等待超时时间

        Returns:
            dict: {'file_id': ..., 'file_name': ..., 'status': ...}
        """
        # PoW
        pow_challenge = self.get_pow_challenge('/api/v0/file/upload_file')
        pow_solution = self.solve_pow_with_wasm(pow_challenge)

        url = f'{self.base_url}/api/v0/file/upload_file'
        headers = self.default_headers.copy()
        headers['x-ds-pow-response'] = base64.b64encode(
            json.dumps(pow_solution).encode()
        ).decode()
        headers.pop('Content-Type', None)

        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()

        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
        }
        mime_type = mime_types.get(file_ext, 'application/octet-stream')

        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f, mime_type)}
            response = requests.post(url, headers=headers, files=files, data={})

        if response.status_code != 200:
            raise Exception(f'上传失败: {response.status_code}')

        result = response.json()
        if result.get('code') != 0:
            raise Exception(f'上传失败: {result.get("msg")}')

        file_info = result.get('data', {}).get('biz_data', {})
        file_id = file_info.get('id')

        result = {
            'file_id': file_id,
            'file_name': file_name,
            'status': file_info.get('status')
        }

        # 等待解析
        if wait_for_parse and file_id:
            import time
            start = time.time()
            while time.time() - start < timeout:
                status_info = self.get_file_status(file_id)
                if status_info:
                    status = status_info.get('status')
                    if status in ('SUCCESS', 'PARSED', 'READY'):
                        result['status'] = 'SUCCESS'
                        return result
                    elif status in ('FAILED', 'ERROR'):
                        raise Exception(f'文件解析失败')
                time.sleep(2)
            raise Exception('文件解析超时')

        return result

    def get_file_status(self, file_id):
        """获取文件状态"""
        url = f'{self.base_url}/api/v0/file/fetch_files'
        headers = self.default_headers.copy()

        response = requests.get(url, headers=headers, params={'file_ids': file_id})

        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                files = result.get('data', {}).get('biz_data', {}).get('files', [])
                for f in files:
                    if f.get('id') == file_id:
                        return f
        return None


# 便捷函数
def create_client(token=None, base_url=None):
    """创建 DeepSeek API 客户端"""
    return DeepSeekAPI(token=token, base_url=base_url)


if __name__ == '__main__':
    # 测试
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    # 从文件加载 token
    token_file = os.path.join(os.path.dirname(__file__), 'deepseek_login.json')
    if os.path.exists(token_file):
        with open(token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            token = data.get('token')

        api = DeepSeekAPI(token=token)

        print('创建 session...')
        session_id = api.create_session()
        print(f'session_id: {session_id}')

        print('发送消息...')
        for chunk in api.chat_stream('你好'):
            print(chunk, end='', flush=True)
        print()
    else:
        print('未找到 token 文件')