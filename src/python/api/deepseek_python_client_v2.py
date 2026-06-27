#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Python Client - 使用 Node.js WASM solver
"""

import subprocess
import json
import requests
import base64
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self, token_file='deepseek_login.json', solver_path='deepseek_pow_solver.js'):
        self.base_url = 'https://chat.deepseek.com'
        self.solver_path = solver_path
        self.token = self._load_token(token_file)

        # 默认 headers
        self.default_headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'x-app-version': '20241129.1',
            'x-client-locale': 'zh_CN',
            'x-client-platform': 'web',
        }

    def _load_token(self, token_file):
        """加载 token"""
        if os.path.exists(token_file):
            with open(token_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('token', '')
        raise FileNotFoundError(f"Token file not found: {token_file}")

    def get_pow_challenge(self, target_path='/api/v0/chat/completion'):
        """获取 PoW challenge"""
        url = f'{self.base_url}/api/v0/chat/create_pow_challenge'
        headers = self.default_headers.copy()
        data = {'target_path': target_path}

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f'Failed to get challenge: {response.status_code} - {response.text}')

        return response.json()['data']

    def solve_pow(self, challenge_data):
        """使用 Node.js WASM solver 解决 PoW"""
        challenge = challenge_data.get('challenge')
        salt = challenge_data.get('salt')
        expire_at = challenge_data.get('expire_at')
        difficulty = challenge_data.get('difficulty', 144000)
        signature = challenge_data.get('signature')

        # 调用 Node.js solver
        solver_input = json.dumps({
            'challenge': challenge,
            'salt': salt,
            'expire_at': expire_at,
            'difficulty': difficulty
        })

        # 运行 Node.js solver
        result = subprocess.run(
            ['node', self.solver_path],
            input=solver_input,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        if result.returncode != 0:
            raise Exception(f'Solver failed: {result.stderr}')

        solver_output = json.loads(result.stdout)
        if not solver_output.get('success'):
            raise Exception(f'No solution found: {solver_output}')

        answer = solver_output['answer']
        return {
            'algorithm': 'DeepSeekHashV1',
            'challenge': challenge,
            'salt': salt,
            'answer': answer,
            'signature': signature,
            'target_path': '/api/v0/chat/completion'
        }

    def build_pow_response(self, pow_data):
        """构建 x-ds-pow-response header"""
        return base64.b64encode(json.dumps(pow_data).encode()).decode()

    def create_session(self):
        """创建聊天 session"""
        url = f'{self.base_url}/api/v0/chat/session/create'
        headers = self.default_headers.copy()
        data = {}

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f'Failed to create session: {response.status_code} - {response.text}')

        return response.json()['data']['session_id']

    def send_message(self, session_id, message, thinking=False):
        """发送消息"""
        url = f'{self.base_url}/api/v0/chat/completion'

        # 获取 PoW challenge
        challenge_data = self.get_pow_challenge()

        # 解决 PoW
        pow_solution = self.solve_pow(challenge_data)

        # 构建 headers
        headers = self.default_headers.copy()
        headers['x-ds-pow-response'] = self.build_pow_response(pow_solution)

        # 构建请求
        data = {
            'session_id': session_id,
            'parent_id': None,
            'messages': [{'content': message, 'role': 'user'}],
            'thinking': thinking
        }

        response = requests.post(url, headers=headers, json=data, stream=True)
        return response


def main():
    """主函数 - 测试客户端"""
    print('='*60)
    print('DeepSeek Python Client - WASM Solver Test')
    print('='*60)

    try:
        client = DeepSeekClient()
        print('Token loaded successfully')

        # 测试 PoW
        print('\n获取 PoW challenge...')
        challenge = client.get_pow_challenge()
        print(f'  Challenge: {challenge.get("challenge")[:40]}...')
        print(f'  Salt: {challenge.get("salt")}')
        print(f'  expire_at: {challenge.get("expire_at")}')
        print(f'  Difficulty: {challenge.get("difficulty")}')

        # 解决 PoW
        print('\n解决 PoW...')
        solution = client.solve_pow(challenge)
        print(f'  Answer: {solution.get("answer")}')
        print(f'  Algorithm: {solution.get("algorithm")}')

        # 构建 header
        pow_header = client.build_pow_response(solution)
        print(f'  x-ds-pow-response: {pow_header[:40]}...')

        print('\n' + '='*60)
        print('测试成功!')
        print('='*60)

        # 可选: 创建 session 并发送消息
        # print('\n创建 session...')
        # session_id = client.create_session()
        # print(f'  Session ID: {session_id}')

        # print('\n发送消息...')
        # response = client.send_message(session_id, 'Hello')
        # for line in response.iter_lines():
        #     if line:
        #         print(line.decode('utf-8'))

    except FileNotFoundError as e:
        print(f'Error: {e}')
        print('请确保 deepseek_login.json 文件存在并包含有效的 token')
    except Exception as e:
        print(f'Error: {e}')


if __name__ == '__main__':
    main()