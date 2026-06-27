#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek OpenAI-Compatible Proxy Server

将 Anthropic/OpenAI API 格式转换为 DeepSeek Web API 格式
让 Claude Code 可以直接调用 DeepSeek

使用方式:
    1. 启动代理: python deepseek_proxy.py
    2. 配置 Claude Code settings.json:
       {
         "env": {
           "ANTHROPIC_BASE_URL": "http://127.0.0.1:8080",
           "ANTHROPIC_AUTH_TOKEN": "Bearer <deepseek_token>"
         }
       }

支持的端点:
    - POST /v1/messages (Anthropic 格式)
    - POST /v1/chat/completions (OpenAI 格式)
"""

import os
import sys
import json
import base64
import subprocess
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import argparse

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


# ==================== DeepSeek API Core ====================

class DeepSeekClient:
    """DeepSeek API 客户端核心"""

    def __init__(self, token, base_url='https://chat.deepseek.com', solver_path=None):
        self.token = token
        self.base_url = base_url
        self.session_id = None
        self.parent_message_id = None

        if solver_path:
            self.solver_path = solver_path
        else:
            self.solver_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'deepseek_pow_solver.js'
            )

        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/',
            'x-app-version': '20241129.1',
            'x-client-locale': 'zh_CN',
            'x-client-platform': 'web',
            'x-client-timezone-offset': '28800',
            'x-client-version': '1.8.0',
            'Authorization': f'Bearer {self.token}'
        }

        # 自动创建 session
        self._ensure_session()

    def _ensure_session(self):
        """确保 session 已创建"""
        if not self.session_id:
            self._create_session()

    def _create_session(self):
        """创建聊天 session"""
        url = f'{self.base_url}/api/v0/chat_session/create'
        try:
            response = requests.post(url, headers=self.headers, json={}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'data' in result and 'biz_data' in result['data']:
                    biz_data = result['data']['biz_data']
                    chat_session = biz_data.get('chat_session', {})
                    self.session_id = chat_session.get('id') or biz_data.get('id')
                    print(f'[DeepSeek] Session created: {self.session_id}')
                    return self.session_id
            print(f'[DeepSeek] Session creation failed: {response.status_code}')
        except Exception as e:
            print(f'[DeepSeek] Session error: {e}')
        return None

    def _get_pow_challenge(self, target_path='/api/v0/chat/completion'):
        """获取 PoW challenge"""
        url = f'{self.base_url}/api/v0/chat/create_pow_challenge'
        response = requests.post(url, headers=self.headers, json={'target_path': target_path}, timeout=10)
        if response.status_code != 200:
            raise Exception(f'PoW challenge failed: {response.status_code}')
        result = response.json()
        if 'data' in result and 'biz_data' in result['data']:
            return result['data']['biz_data']['challenge']
        return result.get('data', result)

    def _solve_pow(self, challenge_data):
        """解决 PoW"""
        challenge = challenge_data.get('challenge')
        salt = challenge_data.get('salt')
        expire_at = challenge_data.get('expire_at')
        difficulty = challenge_data.get('difficulty', 144000)
        signature = challenge_data.get('signature')

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
            cwd=os.path.dirname(self.solver_path),
            timeout=30
        )

        if result.returncode != 0:
            raise Exception(f'PoW solver failed: {result.stderr}')

        solver_output = json.loads(result.stdout)
        if not solver_output.get('success'):
            raise Exception(f'PoW no solution')

        return {
            'algorithm': 'DeepSeekHashV1',
            'challenge': challenge,
            'salt': salt,
            'answer': solver_output['answer'],
            'signature': signature,
            'target_path': '/api/v0/chat/completion'
        }

    def chat(self, messages, model='default', stream=False, thinking=False, search=False):
        """
        发送聊天请求

        Args:
            messages: OpenAI 格式的消息列表 [{"role": "user", "content": "..."}]
            model: 'default' 或 'expert'
            stream: 是否流式响应
            thinking: 是否启用思考模式
            search: 是否启用联网搜索

        Returns:
            流式响应或完整响应
        """
        self._ensure_session()
        if not self.session_id:
            raise Exception('No session available')

        # 获取 PoW
        challenge = self._get_pow_challenge()
        pow_solution = self._solve_pow(challenge)

        headers = self.headers.copy()
        headers['x-ds-pow-response'] = base64.b64encode(
            json.dumps(pow_solution).encode()
        ).decode()

        # 转换消息格式
        # DeepSeek 需要 prompt 字段作为最后一条用户消息
        prompt = ''
        ds_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'user':
                prompt = content  # 最后一条用户消息作为 prompt
            ds_messages.append({'role': role, 'content': content})

        data = {
            'chat_session_id': self.session_id,
            'parent_message_id': self.parent_message_id,
            'model_type': model,
            'prompt': prompt,
            'messages': ds_messages,
            'ref_file_ids': [],
            'thinking_enabled': thinking,
            'search_enabled': search,
            'preempt': False
        }

        url = f'{self.base_url}/api/v0/chat/completion'
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=60)

        if response.status_code != 200:
            error_msg = response.text[:200]
            raise Exception(f'Chat failed: {response.status_code} - {error_msg}')

        return response

    def parse_stream(self, response):
        """解析 DeepSeek 流式响应，返回 OpenAI 格式"""
        content = ''
        message_id = None
        current_fragment_type = None

        for line in response.iter_lines(decode_unicode=True):
            if not line or line.startswith('event:'):
                continue

            if line.startswith('data:'):
                data_str = line[6:]
                if data_str == '[DONE]':
                    break

                try:
                    data = json.loads(data_str)

                    # 初始化响应
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
                        if data['v'] in ('FINISHED', 'SUCCESS', 'PENDING'):
                            continue
                        if current_fragment_type == 'RESPONSE':
                            content += data['v']

                except json.JSONDecodeError:
                    pass

        # 更新 parent_message_id
        if message_id:
            self.parent_message_id = message_id

        return content, message_id

    def stream_chunks(self, response):
        """生成 OpenAI 格式的流式 chunks"""
        content = ''
        message_id = None
        current_fragment_type = None
        chunk_id = f'chatcmpl-{int(time.time())}'

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
                        if data['v'] in ('FINISHED', 'SUCCESS', 'PENDING'):
                            continue
                        if current_fragment_type == 'RESPONSE':
                            text = data['v']
                            content += text
                            # 生成 OpenAI 格式的 chunk
                            chunk = {
                                'id': chunk_id,
                                'object': 'chat.completion.chunk',
                                'created': int(time.time()),
                                'model': 'deepseek-v3',
                                'choices': [{
                                    'index': 0,
                                    'delta': {'content': text},
                                    'finish_reason': None
                                }]
                            }
                            yield f'data: {json.dumps(chunk)}\n\n'

                except json.JSONDecodeError:
                    pass

        # 发送结束 chunk
        final_chunk = {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': int(time.time()),
            'model': 'deepseek-v3',
            'choices': [{
                'index': 0,
                'delta': {},
                'finish_reason': 'stop'
            }]
        }
        yield f'data: {json.dumps(final_chunk)}\n\n'
        yield 'data: [DONE]\n\n'

        # 更新状态
        if message_id:
            self.parent_message_id = message_id


# ==================== Proxy Server ====================

class DeepSeekProxyHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 - 转换 API 格式"""

    client = None  # 共享的 DeepSeek 客户端

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f'[Proxy] {args[0]}')

    def send_json_response(self, data, status=200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_stream_response(self, chunks_generator):
        """发送流式响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        for chunk in chunks_generator:
            self.wfile.write(chunk.encode('utf-8'))
            self.wfile.flush()

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-api-key')
        self.end_headers()

    def do_GET(self):
        """处理 GET 请求"""
        path = urlparse(self.path).path

        if path == '/health' or path == '/':
            self.send_json_response({'status': 'ok', 'service': 'deepseek-proxy'})
        elif path == '/v1/models':
            # 返回可用模型列表
            models = {
                'object': 'list',
                'data': [
                    {'id': 'deepseek-v3', 'object': 'model', 'owned_by': 'deepseek'},
                    {'id': 'deepseek-expert', 'object': 'model', 'owned_by': 'deepseek'},
                ]
            }
            self.send_json_response(models)
        else:
            self.send_json_response({'error': 'Not found'}, 404)

    def do_POST(self):
        """处理 POST 请求"""
        path = urlparse(self.path).path

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            request_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        # 解析认证
        auth_header = self.headers.get('Authorization', '')
        api_key = self.headers.get('x-api-key', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif api_key:
            token = api_key
        else:
            # 使用配置的默认 token
            token = getattr(self.server, 'default_token', None)

        if not token and not self.client:
            self.send_json_response({'error': 'No API token provided'}, 401)
            return

        # 更新客户端 token
        if token and self.client and self.client.token != token:
            self.client.token = token
            self.client.headers['Authorization'] = f'Bearer {token}'
            self.client.session_id = None  # 重置 session
            self.client._ensure_session()

        # 处理不同的端点
        if path == '/v1/messages':
            # Anthropic 格式
            self._handle_anthropic(request_data)
        elif path == '/v1/chat/completions':
            # OpenAI 格式
            self._handle_openai(request_data)
        else:
            self.send_json_response({'error': f'Unknown endpoint: {path}'}, 404)

    def _handle_anthropic(self, request_data):
        """处理 Anthropic API 格式"""
        try:
            messages = request_data.get('messages', [])
            model = request_data.get('model', 'deepseek-v3')
            stream = request_data.get('stream', False)
            max_tokens = request_data.get('max_tokens', 4096)

            # 转换模型名称
            ds_model = 'expert' if 'expert' in model.lower() else 'default'

            # 调用 DeepSeek
            response = self.client.chat(messages, model=ds_model, stream=True)

            if stream:
                # 流式响应 - 转换为 Anthropic SSE 格式
                self._send_anthropic_stream(response, model)
            else:
                # 非流式响应
                content, msg_id = self.client.parse_stream(response)
                result = {
                    'id': f'msg_{msg_id or int(time.time())}',
                    'type': 'message',
                    'role': 'assistant',
                    'content': [{'type': 'text', 'text': content}],
                    'model': model,
                    'stop_reason': 'end_turn',
                    'usage': {'input_tokens': 0, 'output_tokens': len(content)//4}
                }
                self.send_json_response(result)

        except Exception as e:
            print(f'[Proxy] Anthropic error: {e}')
            self.send_json_response({'error': {'type': 'api_error', 'message': str(e)}}, 500)

    def _send_anthropic_stream(self, response, model):
        """发送 Anthropic 格式的流式响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        content = ''
        message_id = None
        current_fragment_type = None
        msg_id = f'msg_{int(time.time())}'

        # 发送 message_start 事件
        self._send_sse_event('message_start', {
            'type': 'message_start',
            'message': {
                'id': msg_id,
                'type': 'message',
                'role': 'assistant',
                'content': [],
                'model': model,
                'stop_reason': None,
            }
        })

        # 发送 content_block_start
        self._send_sse_event('content_block_start', {
            'type': 'content_block_start',
            'index': 0,
            'content_block': {'type': 'text', 'text': ''}
        })

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
                        if data['v'] in ('FINISHED', 'SUCCESS', 'PENDING'):
                            continue
                        if current_fragment_type == 'RESPONSE':
                            text = data['v']
                            content += text
                            # 发送 content_block_delta
                            self._send_sse_event('content_block_delta', {
                                'type': 'content_block_delta',
                                'index': 0,
                                'delta': {'type': 'text_delta', 'text': text}
                            })

                except json.JSONDecodeError:
                    pass

        # 发送 content_block_stop
        self._send_sse_event('content_block_stop', {
            'type': 'content_block_stop',
            'index': 0
        })

        # 发送 message_delta
        self._send_sse_event('message_delta', {
            'type': 'message_delta',
            'delta': {'stop_reason': 'end_turn'},
            'usage': {'output_tokens': len(content)//4}
        })

        # 发送 message_stop
        self._send_sse_event('message_stop', {
            'type': 'message_stop'
        })

        if message_id:
            self.client.parent_message_id = message_id

    def _send_sse_event(self, event_type, data):
        """发送 SSE 事件"""
        event = f'event: {event_type}\ndata: {json.dumps(data)}\n\n'
        self.wfile.write(event.encode('utf-8'))
        self.wfile.flush()

    def _handle_openai(self, request_data):
        """处理 OpenAI API 格式"""
        try:
            messages = request_data.get('messages', [])
            model = request_data.get('model', 'deepseek-v3')
            stream = request_data.get('stream', False)

            # 转换模型名称
            ds_model = 'expert' if 'expert' in model.lower() else 'default'

            # 调用 DeepSeek
            response = self.client.chat(messages, model=ds_model, stream=True)

            if stream:
                # 流式响应
                self.send_stream_response(self.client.stream_chunks(response))
            else:
                # 非流式响应
                content, msg_id = self.client.parse_stream(response)
                result = {
                    'id': f'chatcmpl-{msg_id or int(time.time())}',
                    'object': 'chat.completion',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [{
                        'index': 0,
                        'message': {'role': 'assistant', 'content': content},
                        'finish_reason': 'stop'
                    }],
                    'usage': {'prompt_tokens': 0, 'completion_tokens': len(content)//4, 'total_tokens': len(content)//4}
                }
                self.send_json_response(result)

        except Exception as e:
            print(f'[Proxy] OpenAI error: {e}')
            self.send_json_response({'error': {'message': str(e), 'type': 'api_error'}}, 500)


# ==================== Main ====================

def run_proxy_server(token, port=8080, base_url='https://chat.deepseek.com'):
    """运行代理服务器"""
    # 初始化客户端
    DeepSeekProxyHandler.client = DeepSeekClient(token=token, base_url=base_url)

    server = HTTPServer(('127.0.0.1', port), DeepSeekProxyHandler)
    server.default_token = token

    print(f'')
    print(f'=' * 60)
    print(f'  DeepSeek Proxy Server')
    print(f'=' * 60)
    print(f'  Proxy URL:     http://127.0.0.1:{port}')
    print(f'  DeepSeek URL:  {base_url}')
    print(f'  Endpoints:')
    print(f'    - POST /v1/messages        (Anthropic)')
    print(f'    - POST /v1/chat/completions (OpenAI)')
    print(f'    - GET  /v1/models')
    print(f'    - GET  /health')
    print(f'')
    print(f'  Claude Code 配置:')
    print(f'    {{"env": {{"ANTHROPIC_BASE_URL": "http://127.0.0.1:{port}"}}}}')
    print(f'')
    print(f'=' * 60)
    print(f'')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[Proxy] Server stopped')
        server.shutdown()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DeepSeek OpenAI-Compatible Proxy')
    parser.add_argument('--port', type=int, default=8080, help='Proxy server port')
    parser.add_argument('--token', type=str, help='DeepSeek API token')
    parser.add_argument('--base-url', type=str, default='https://chat.deepseek.com', help='DeepSeek base URL')
    parser.add_argument('--config', type=str, help='Config JSON file path')

    args = parser.parse_args()

    # 加载 token
    token = args.token

    if not token and args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                data = json.load(f)
                token = data.get('token')
                if not args.base_url:
                    args.base_url = data.get('base_url', 'https://chat.deepseek.com')
        except Exception as e:
            print(f'Config load error: {e}')

    if not token:
        # 尝试从默认配置文件加载
        config_file = os.path.join(os.path.dirname(__file__), 'deepseek_login.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    token = data.get('token')
                    args.base_url = data.get('base_url', args.base_url)
                print(f'[Proxy] Token loaded from {config_file}')
            except Exception as e:
                print(f'[Proxy] Config load error: {e}')

    if not token:
        print('Error: No API token provided')
        print('Usage: python deepseek_proxy.py --token <your_token>')
        print('   or: python deepseek_proxy.py --config deepseek_login.json')
        sys.exit(1)

    run_proxy_server(token=token, port=args.port, base_url=args.base_url)


if __name__ == '__main__':
    main()