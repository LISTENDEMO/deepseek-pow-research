#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Chat Client - PyQt6 GUI
使用 Node.js WASM solver 解决 PoW
"""

import sys
import os
import json
import base64
import subprocess
import threading
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QTextBrowser, QLineEdit, QPushButton, QLabel, QMessageBox,
    QSplitter, QFrame, QScrollArea, QDialog, QFileDialog, QListWidget, QListWidgetItem,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor, QAction
from io import StringIO

# 设置编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


# ==================== API Client ====================

class DeepSeekAPI:
    """DeepSeek API 客户端"""

    def __init__(self, token=None):
        self.base_url = 'https://chat.deepseek.com'
        self.token = token
        self.session_id = None
        self.parent_message_id = None  # 用于链接对话上下文
        self.messages_history = []  # 对话历史（备用）
        self.email = None  # 保存邮箱用于自动登录
        self.password = None  # 保存密码用于自动登录

        self.default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
            'Origin': 'https://chat.deepseek.com',
            'Referer': 'https://chat.deepseek.com/',
            'x-app-version': '20241129.1',
            'x-client-locale': 'zh_CN',
            'x-client-platform': 'web',
            'x-client-timezone-offset': '28800',
            'x-client-version': '1.8.0',
        }

        # 如果提供了 token，自动设置 Authorization header
        if token:
            self.default_headers['Authorization'] = f'Bearer {token}'

    def set_token(self, token):
        self.token = token
        self.default_headers['Authorization'] = f'Bearer {token}'

    def set_credentials(self, email, password):
        """保存账号密码用于自动登录"""
        self.email = email
        self.password = password

    def auto_login(self, email=None, password=None):
        """
        自动登录 DeepSeek

        Args:
            email: 邮箱（可选，使用已保存的）
            password: 密码（可选，使用已保存的）

        Returns:
            {'success': bool, 'token': str, 'error': str}
        """
        import uuid
        import time

        email = email or self.email
        password = password or self.password

        if not email or not password:
            return {'success': False, 'token': None, 'error': '未设置邮箱或密码'}

        headers = self.default_headers.copy()
        headers.pop('Authorization', None)

        data = {
            'email': email,
            'password': password,
            'device_id': str(uuid.uuid4()),
            'os': 'windows',
            'locale': 'zh_CN',
        }

        try:
            response = requests.post(
                f'{self.base_url}/api/v0/users/login',
                headers=headers,
                json=data,
                timeout=15
            )

            result = response.json()

            if result.get('code') == 0:
                user_data = result.get('data', {}).get('biz_data', {}).get('user', {})
                token = user_data.get('token')

                if token:
                    self.set_token(token)
                    self.email = email
                    self.password = password

                    # 保存到配置文件
                    config_file = os.path.join(os.path.dirname(__file__), 'deepseek_login.json')
                    try:
                        with open(config_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                'email': email,
                                'token': token,
                                'base_url': self.base_url,
                                'login_time': time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
                            }, f, indent=2)
                    except:
                        pass

                    return {'success': True, 'token': token, 'error': None}

            return {'success': False, 'token': None, 'error': result.get('msg', '登录失败')}

        except Exception as e:
            return {'success': False, 'token': None, 'error': str(e)}

    def check_token_valid(self):
        """检查当前 Token 是否有效"""
        if not self.token:
            return False

        try:
            response = requests.post(
                f'{self.base_url}/api/v0/chat_session/create',
                headers=self.default_headers.copy(),
                json={},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    def refresh_token_if_needed(self):
        """如果 Token 过期则自动刷新"""
        if not self.check_token_valid():
            if self.email and self.password:
                result = self.auto_login()
                return result.get('success', False)
        return True

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
            raise Exception('Rate Limit (429) - 请等待几分钟后再试')
        if response.status_code != 200:
            raise Exception(f'获取 challenge 失败: {response.status_code} - {response.text[:200]}')

        result = response.json()
        # API 返回结构: {data: {biz_data: {challenge: {...}}}}
        if 'data' in result and 'biz_data' in result['data']:
            return result['data']['biz_data']['challenge']
        elif 'data' in result:
            return result['data']
        else:
            return result

    def solve_pow_with_wasm(self, challenge_data):
        """使用 Node.js WASM solver 解决 PoW"""
        challenge = challenge_data.get('challenge')
        salt = challenge_data.get('salt')
        expire_at = challenge_data.get('expire_at')
        difficulty = challenge_data.get('difficulty', 144000)
        signature = challenge_data.get('signature')
        algorithm = challenge_data.get('algorithm', 'DeepSeekHashV1')
        target_path = challenge_data.get('target_path', '/api/v0/chat/completion')

        solver_path = os.path.join(os.path.dirname(__file__), 'deepseek_pow_solver.js')

        solver_input = json.dumps({
            'challenge': challenge,
            'salt': salt,
            'expire_at': expire_at,
            'difficulty': difficulty
        })

        result = subprocess.run(
            ['node', solver_path],
            input=solver_input,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )

        if result.returncode != 0:
            raise Exception(f'Solver 失败: {result.stderr}')

        solver_output = json.loads(result.stdout)
        if not solver_output.get('success'):
            raise Exception(f'未找到解: {solver_output}')

        answer = solver_output['answer']
        return {
            'algorithm': algorithm,
            'challenge': challenge,
            'salt': salt,
            'answer': answer,
            'signature': signature,
            'target_path': target_path
        }

    def create_session(self):
        """创建聊天 session"""
        url = f'{self.base_url}/api/v0/chat_session/create'
        headers = self.default_headers.copy()
        data = {}

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 429:
            raise Exception('Rate Limit (429)')
        if response.status_code != 200:
            raise Exception(f'创建 session 失败: {response.status_code} - {response.text[:200]}')

        result = response.json()
        # API 返回结构: {data: {biz_data: {chat_session: {id: "..."}}}}
        if 'data' in result and 'biz_data' in result['data']:
            biz_data = result['data']['biz_data']
            chat_session = biz_data.get('chat_session', {})
            self.session_id = chat_session.get('id') or biz_data.get('id')
        else:
            self.session_id = result.get('data', {}).get('session_id')

        if not self.session_id:
            raise Exception(f'无法获取 session_id: {result}')

        return self.session_id

    def send_message_stream(self, message, thinking=False, model_type='default', search_enabled=False, file_ids=None):
        """发送消息 (流式) - 支持对话上下文和附件"""
        url = f'{self.base_url}/api/v0/chat/completion'

        # 获取并解决 PoW
        challenge_data = self.get_pow_challenge()
        pow_solution = self.solve_pow_with_wasm(challenge_data)

        headers = self.default_headers.copy()
        headers['x-ds-pow-response'] = base64.b64encode(
            json.dumps(pow_solution).encode()
        ).decode()

        # 构建消息列表
        messages = self.messages_history.copy()
        messages.append({
            'role': 'user',
            'content': message
        })

        data = {
            'chat_session_id': self.session_id,
            'parent_message_id': self.parent_message_id,  # 链接上一条消息
            'model_type': model_type or 'default',
            'prompt': message,
            'messages': messages,
            'ref_file_ids': file_ids or [],  # 附件文件 ID 列表
            'thinking_enabled': thinking,
            'search_enabled': search_enabled,
            'preempt': False
        }

        response = requests.post(url, headers=headers, json=data, stream=True)
        if response.status_code == 429:
            raise Exception('Rate Limit (429)')
        if response.status_code != 200:
            raise Exception(f'发送消息失败: {response.status_code} - {response.text[:200]}')

        return response

    def add_to_history(self, role, content):
        """添加消息到历史"""
        self.messages_history.append({
            'role': role,
            'content': content
        })

    def set_parent_message_id(self, message_id):
        """设置上一条消息 ID"""
        self.parent_message_id = message_id

    def upload_file(self, file_path):
        """上传文件到 DeepSeek（需要 PoW）"""
        # 1. 获取 PoW challenge
        pow_challenge = self.get_pow_challenge('/api/v0/file/upload_file')
        pow_solution = self.solve_pow_with_wasm(pow_challenge)

        # 2. 构建上传请求
        url = f'{self.base_url}/api/v0/file/upload_file'
        headers = self.default_headers.copy()
        # 添加 PoW header
        headers['x-ds-pow-response'] = base64.b64encode(
            json.dumps(pow_solution).encode()
        ).decode()
        # 移除 Content-Type（multipart 会自动处理）
        headers.pop('Content-Type', None)

        file_name = os.path.basename(file_path)

        # 获取文件类型
        file_ext = os.path.splitext(file_name)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
        }
        mime_type = mime_types.get(file_ext, 'application/octet-stream')

        with open(file_path, 'rb') as f:
            files = {
                'file': (file_name, f, mime_type)
            }
            data = {}

            response = requests.post(url, headers=headers, files=files, data=data)

        if response.status_code == 429:
            raise Exception('Rate Limit (429)')
        if response.status_code != 200:
            raise Exception(f'上传失败: {response.status_code} - {response.text[:200]}')

        result = response.json()
        if result.get('code') == 0:
            file_info = result.get('data', {}).get('biz_data', {})
            file_id = file_info.get('id')
            return {
                'file_id': file_id,
                'file_name': file_name,
                'file_size': file_info.get('file_size'),
                'file_type': file_info.get('file_type'),
                'status': file_info.get('status')
            }
        else:
            raise Exception(f'上传失败: {result.get("msg", "未知错误")}')

    def get_uploaded_files(self):
        """获取已上传的文件列表"""
        headers = self.default_headers.copy()
        url = f'{self.base_url}/api/v0/file/fetch_files'

        # 使用 GET 请求
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                return result.get('data', {}).get('biz_data', {}).get('files', [])

        return []

    def get_session_list(self, page=1, page_size=50):
        """获取会话历史列表 - GET 请求"""
        url = f'{self.base_url}/api/v0/chat_session/fetch_page'
        headers = self.default_headers.copy()

        # GET 请求，参数作为 query
        params = {'count': page_size}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    sessions = result.get('data', {}).get('biz_data', {}).get('chat_sessions', [])
                    return sessions
            return []
        except Exception as e:
            print(f'[会话列表] 获取失败: {e}')
            return []

    def get_chat_history(self, session_id, limit=50):
        """获取指定会话的消息历史 - GET 请求"""
        url = f'{self.base_url}/api/v0/chat/history_messages'
        headers = self.default_headers.copy()

        # GET 请求，参数作为 query
        params = {
            'chat_session_id': session_id,
            'limit': limit
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    messages = result.get('data', {}).get('biz_data', {}).get('chat_messages', [])
                    return messages
            return []
        except Exception as e:
            print(f'[消息历史] 获取失败: {e}')
            return []

    def get_file_status(self, file_id):
        """获取单个文件的状态"""
        headers = self.default_headers.copy()

        # 正确的请求方式: GET 请求，file_ids 作为 query 参数
        url = f'{self.base_url}/api/v0/file/fetch_files'
        params = {'file_ids': file_id}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                files = result.get('data', {}).get('biz_data', {}).get('files', [])
                for f in files:
                    if f.get('id') == file_id:
                        return f

        return None

    def wait_for_file_parsed(self, file_id, timeout=30):
        """等待文件解析完成"""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            file_info = self.get_file_status(file_id)

            if file_info:
                status = file_info.get('status')
                # 成功状态
                if status in ('PARSED', 'READY', 'SUCCESS', 'COMPLETE', 'DONE', 'FINISHED'):
                    return True
                # 失败状态
                elif status in ('FAILED', 'ERROR', 'PARSE_ERROR'):
                    error_code = file_info.get('error_code') or '未知错误'
                    raise Exception(f'文件解析失败: {error_code}')

            time.sleep(2)

        raise Exception('文件解析超时')


# ==================== Worker Threads ====================

class SendMessageWorker(QThread):
    """发送消息工作线程"""

    chunk_received = pyqtSignal(str)
    message_id_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, api, message, thinking=False, model_type='default', search_enabled=False, file_ids=None):
        super().__init__()
        self.api = api
        self.message = message
        self.thinking = thinking
        self.model_type = model_type
        self.search_enabled = search_enabled
        self.file_ids = file_ids or []

    def run(self):
        try:
            response = self.api.send_message_stream(
                self.message,
                self.thinking,
                self.model_type,
                self.search_enabled,
                self.file_ids
            )

            for line in response.iter_lines(decode_unicode=True):
                if line:
                    self.chunk_received.emit(line)
                    # 解析 message_id
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            # 从初始化响应中获取 message_id
                            if isinstance(data.get('v'), dict):
                                response_obj = data['v'].get('response', {})
                                if 'message_id' in response_obj:
                                    self.message_id_signal.emit(response_obj['message_id'])
                        except:
                            pass

            self.finished_signal.emit()

        except Exception as e:
            self.error_signal.emit(str(e))


class InitSessionWorker(QThread):
    """初始化 session 工作线程"""

    success_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        try:
            session_id = self.api.create_session()
            self.success_signal.emit(session_id)
        except Exception as e:
            self.error_signal.emit(str(e))


class UploadFileWorker(QThread):
    """文件上传工作线程 - 包含等待解析"""

    success_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)

    def __init__(self, api, file_path):
        super().__init__()
        self.api = api
        self.file_path = file_path

    def run(self):
        try:
            file_name = os.path.basename(self.file_path)

            # 1. 上传文件
            self.progress_signal.emit(f'上传 {file_name}...')
            result = self.api.upload_file(self.file_path)
            file_id = result.get('file_id')

            # 2. 等待文件解析完成（在线程中等待，不阻塞 UI）
            if file_id:
                self.progress_signal.emit(f'解析 {file_name}...')
                self.api.wait_for_file_parsed(file_id, timeout=30)
                result['status'] = 'PARSED'

            self.success_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


# ==================== Chat Message Widget ====================

class MessageWidget(QFrame):
    """单条消息显示组件 - 支持 Markdown 渲染"""

    def __init__(self, content, is_user=True, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.is_user = is_user

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(6)

        # 角色标签
        role_label = QLabel('你' if is_user else 'DeepSeek')
        role_label.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        role_label.setObjectName('role_label')
        layout.addWidget(role_label)

        # 消息内容 - 使用 QTextBrowser 支持 Markdown
        self.content_browser = QTextBrowser()
        self.content_browser.setMarkdown(content)
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setFont(QFont('Microsoft YaHei', 11))
        self.content_browser.setObjectName('content_browser')
        self.content_browser.setReadOnly(True)
        self.content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.content_browser.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                color: #d0d0d0;
                border: none;
                padding: 0px;
                line-height: 1.5;
            }
        """)

        # 设置 size policy 让它能正确展开
        self.content_browser.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        layout.addWidget(self.content_browser)

        # 样式设置
        if is_user:
            self.setStyleSheet("""
                QFrame {
                    background-color: #3a4a5d;
                    border-radius: 12px;
                }
                QLabel#role_label {
                    color: #7eb8da;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #353535;
                    border-radius: 12px;
                }
                QLabel#role_label {
                    color: #9b59b6;
                }
            """)

    def resizeEvent(self, event):
        """窗口大小改变时，重新计算高度"""
        super().resizeEvent(event)
        # 避免宽度为 0 时计算错误
        width = self.content_browser.width()
        if width > 10:
            doc = self.content_browser.document()
            doc.setTextWidth(width)
            height = doc.size().height() + 20
            self.content_browser.setMinimumHeight(int(height))
            self.content_browser.setMaximumHeight(int(height))


# ==================== Main Window ====================

class DeepSeekChatWindow(QMainWindow):
    """DeepSeek 聊天主窗口"""

    def __init__(self):
        super().__init__()

        self.api = DeepSeekAPI()
        self.current_response = ""
        self.response_widget = None
        self.current_fragment_type = None  # 当前 fragment 类型: THINK 或 RESPONSE
        self.thinking_content = ""  # 思考内容

        self.init_ui()
        self.load_token()

    def init_ui(self):
        """初始化界面 - 现代灰色主题，左侧会话列表"""
        self.setWindowTitle('DeepSeek Chat')
        self.setMinimumSize(QSize(1000, 650))
        self.resize(1200, 750)

        # 全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:disabled {
                background-color: #252525;
                color: #666666;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                padding: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #5d5d5d;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QSplitter::handle {
                background-color: #3d3d3d;
                width: 2px;
            }
            QListWidget {
                background-color: #252525;
                border: none;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                background-color: #2d2d2d;
                border-radius: 6px;
                padding: 10px;
                margin: 3px;
            }
            QListWidget::item:selected {
                background-color: #4a90d9;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
            QMessageBox {
                background-color: #2d2d2d;
            }
            QDialog {
                background-color: #2d2d2d;
            }
        """)

        # 设置字体
        font = QFont('Microsoft YaHei', 11)
        QApplication.instance().setFont(font)

        # 主布局 - 使用 Splitter 分割左右
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 顶部标题栏
        header_frame = QFrame()
        header_frame.setStyleSheet('background-color: transparent;')
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 5)

        # 标题
        title_label = QLabel('DeepSeek Chat')
        title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        title_label.setStyleSheet('color: #b0b0b0;')
        header_layout.addWidget(title_label)

        # 状态指示
        self.status_label = QLabel('● 未登录')
        self.status_label.setStyleSheet('color: #ff6b6b; font-size: 12px;')
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        # Session 信息
        self.session_label = QLabel('')
        self.session_label.setStyleSheet('color: #666666; font-size: 10px;')
        header_layout.addWidget(self.session_label)

        # 设置按钮
        self.token_btn = QPushButton('⚙ 设置')
        self.token_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                padding: 6px 12px;
            }
        """)
        self.token_btn.clicked.connect(self.show_token_dialog)
        header_layout.addWidget(self.token_btn)

        main_layout.addWidget(header_frame)

        # === 左右分割区域 ===
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)

        # === 左侧：会话列表 ===
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 新会话按钮
        self.new_session_btn = QPushButton('✦ 新会话')
        self.new_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                padding: 10px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #5a9de9;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #666666;
            }
        """)
        self.new_session_btn.clicked.connect(self.create_new_session)
        self.new_session_btn.setEnabled(False)
        left_layout.addWidget(self.new_session_btn)

        # 会话列表
        self.session_list = QListWidget()
        self.session_list.setMinimumWidth(200)
        self.session_list.setMaximumWidth(350)
        self.session_list.itemClicked.connect(self.on_session_clicked)
        left_layout.addWidget(self.session_list)

        # 刷新按钮
        refresh_btn = QPushButton('🔄 刷新列表')
        refresh_btn.clicked.connect(self.load_session_list)
        left_layout.addWidget(refresh_btn)

        self.splitter.addWidget(self.left_panel)

        # === 右侧：聊天区域 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 聊天消息区域
        chat_frame = QFrame()
        chat_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
            }
        """)
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.messages_container = QWidget()
        self.messages_container.setStyleSheet('background-color: transparent;')
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(12)
        self.messages_layout.setContentsMargins(5, 5, 5, 5)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        chat_layout.addWidget(self.scroll_area)

        right_layout.addWidget(chat_frame, stretch=1)

        # 输入区域
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 12px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(12)

        # 模式选择
        mode_frame = QFrame()
        mode_frame.setStyleSheet('background-color: transparent;')
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)

        # 快速模式
        self.quick_mode_btn = QPushButton('快速')
        self.quick_mode_btn.setCheckable(True)
        self.quick_mode_btn.setChecked(True)
        self.quick_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #4a90d9;
                color: white;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:checked:hover {
                background-color: #5a9de9;
            }
        """)
        self.quick_mode_btn.clicked.connect(lambda: self.set_model_mode('default'))
        mode_layout.addWidget(self.quick_mode_btn)

        # 专家模式
        self.expert_mode_btn = QPushButton('专家')
        self.expert_mode_btn.setCheckable(True)
        self.expert_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #9b59b6;
                color: white;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:checked:hover {
                background-color: #a869c3;
            }
        """)
        self.expert_mode_btn.clicked.connect(lambda: self.set_model_mode('expert'))
        mode_layout.addWidget(self.expert_mode_btn)

        self.current_model_type = 'default'
        input_layout.addWidget(mode_frame)

        # 功能开关
        func_frame = QFrame()
        func_frame.setStyleSheet('background-color: transparent;')
        func_layout = QHBoxLayout(func_frame)
        func_layout.setContentsMargins(0, 0, 0, 0)
        func_layout.setSpacing(6)

        # 思考模式
        self.thinking_checkbox = QPushButton('思考')
        self.thinking_checkbox.setCheckable(True)
        self.thinking_checkbox.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:checked {
                background-color: #27ae60;
                color: white;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        func_layout.addWidget(self.thinking_checkbox)

        # 联网搜索
        self.search_checkbox = QPushButton('联网')
        self.search_checkbox.setCheckable(True)
        self.search_checkbox.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:checked {
                background-color: #e67e22;
                color: white;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        func_layout.addWidget(self.search_checkbox)

        # 上传附件按钮
        self.upload_btn = QPushButton('📎')
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        self.upload_btn.clicked.connect(self.select_file)
        self.upload_btn.setToolTip('上传文件附件')
        func_layout.addWidget(self.upload_btn)

        input_layout.addWidget(func_frame)

        # 附件列表显示
        self.files_frame = QFrame()
        self.files_frame.setStyleSheet('background-color: transparent;')
        self.files_layout = QHBoxLayout(self.files_frame)
        self.files_layout.setContentsMargins(0, 5, 0, 5)
        self.files_layout.setSpacing(8)
        self.files_frame.setVisible(False)  # 默认隐藏
        input_layout.addWidget(self.files_frame)

        # 存储已上传的文件
        self.uploaded_files = []  # [{file_id, file_name}]

        # 输入框
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText('输入消息...')
        self.input_edit.setMinimumHeight(45)
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                border: 2px solid #4d4d4d;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #5d5d5d;
                background-color: #4d4d4d;
            }
        """)
        self.input_edit.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_edit, stretch=1)

        # 发送按钮
        self.send_btn = QPushButton('发送')
        self.send_btn.setMinimumHeight(45)
        self.send_btn.setMinimumWidth(100)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5a9de9;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #666666;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)
        input_layout.addWidget(self.send_btn)

        right_layout.addWidget(input_frame)

        # 完成 splitter 设置
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([250, 750])  # 左侧 250px，右侧 750px

        main_layout.addWidget(self.splitter, stretch=1)

        # 保存侧边栏状态
        self.sidebar_visible = True
        self.sidebar_width = 250

        # 设置菜单
        self.create_menu()

    def create_menu(self):
        """创建菜单"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件')

        load_token_action = QAction('加载 Token 文件', self)
        load_token_action.triggered.connect(self.load_token_from_file)
        file_menu.addAction(load_token_action)

        clear_action = QAction('清空聊天', self)
        clear_action.triggered.connect(self.clear_chat)
        file_menu.addAction(clear_action)

        # 视图菜单
        view_menu = menubar.addMenu('视图')

        toggle_sidebar_action = QAction('隐藏/显示侧边栏', self)
        toggle_sidebar_action.setShortcut('Ctrl+B')
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助')

        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def toggle_sidebar(self):
        """切换侧边栏显示/隐藏"""
        if self.sidebar_visible:
            # 隐藏侧边栏
            self.sidebar_width = self.left_panel.width()
            self.left_panel.hide()
            self.sidebar_visible = False
        else:
            # 显示侧边栏
            self.left_panel.show()
            self.splitter.setSizes([self.sidebar_width, self.width() - self.sidebar_width])
            self.sidebar_visible = True

    def load_token(self):
        """从文件加载配置（token 和 base_url）"""
        config_file = os.path.join(os.path.dirname(__file__), 'deepseek_login.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    token = data.get('token', '')
                    base_url = data.get('base_url', 'https://chat.deepseek.com')
                    email = data.get('email', '')
                    password = data.get('password', '')

                    if token:
                        self.api.set_token(token)
                    if base_url:
                        self.api.base_url = base_url
                        self.api.default_headers['Origin'] = base_url
                        self.api.default_headers['Referer'] = f'{base_url}/'
                    if email:
                        self.api.email = email
                    if password:
                        self.api.password = password

                    self.update_status(bool(token))
                    self.send_btn.setEnabled(bool(token))
                    self.new_session_btn.setEnabled(bool(token))

                    # 加载会话列表
                    if token:
                        self.load_session_list()
            except Exception as e:
                QMessageBox.warning(self, '错误', f'加载配置失败: {e}')

    def load_token_from_file(self):
        """从文件选择加载配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择配置文件', '', 'JSON Files (*.json)'
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    token = data.get('token', '')
                    base_url = data.get('base_url', '')

                    if token:
                        self.api.set_token(token)
                    if base_url:
                        self.api.base_url = base_url
                        self.api.default_headers['Origin'] = base_url
                        self.api.default_headers['Referer'] = f'{base_url}/'

                    self.update_status(bool(token))
                    self.send_btn.setEnabled(bool(token))
                    self.new_session_btn.setEnabled(bool(token))
                    QMessageBox.information(self, '成功', '配置加载成功!')
            except Exception as e:
                QMessageBox.warning(self, '错误', f'加载失败: {e}')

    def show_token_dialog(self):
        """显示设置对话框 - API Key、Base URL 和自动登录"""
        dialog = QDialog(self)
        dialog.setWindowTitle('API 设置')
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 2px solid #4d4d4d;
                border-radius: 8px;
                padding: 10px;
            }
            QLineEdit:focus {
                border: 2px solid #5d5d5d;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # === 自动登录区域 ===
        auto_label = QLabel('自动登录（推荐）:')
        auto_label.setStyleSheet('font-size: 13px; font-weight: bold; color: #4a90d9;')
        layout.addWidget(auto_label)

        # 邮箱输入
        email_input = QLineEdit()
        email_input.setPlaceholderText('邮箱地址')
        email_input.setMinimumHeight(40)
        if self.api.email:
            email_input.setText(self.api.email)
        layout.addWidget(email_input)

        # 密码输入
        password_input = QLineEdit()
        password_input.setPlaceholderText('密码')
        password_input.setMinimumHeight(40)
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        if self.api.password:
            password_input.setText(self.api.password)
        layout.addWidget(password_input)

        # 自动登录按钮
        auto_login_btn = QPushButton('自动登录')
        auto_login_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 25px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)

        def do_auto_login():
            email = email_input.text().strip()
            password = password_input.text().strip()

            if not email or not password:
                QMessageBox.warning(dialog, '提示', '请输入邮箱和密码')
                return

            # 显示登录状态
            auto_login_btn.setText('登录中...')
            auto_login_btn.setEnabled(False)

            result = self.api.auto_login(email, password)

            if result['success']:
                token_input.setText(self.api.token)
                QMessageBox.information(dialog, '成功', f'登录成功！Token 已更新')
                auto_login_btn.setText('自动登录')
                auto_login_btn.setEnabled(True)
            else:
                QMessageBox.warning(dialog, '失败', f'登录失败: {result["error"]}')
                auto_login_btn.setText('自动登录')
                auto_login_btn.setEnabled(True)

        auto_login_btn.clicked.connect(do_auto_login)
        layout.addWidget(auto_login_btn)

        layout.addSpacing(15)

        # === 手动设置区域 ===
        manual_label = QLabel('手动设置 Token:')
        manual_label.setStyleSheet('font-size: 13px; font-weight: bold;')
        layout.addWidget(manual_label)

        # API Key 输入
        token_input = QLineEdit()
        token_input.setPlaceholderText('Bearer token...')
        token_input.setMinimumHeight(40)
        if self.api.token:
            token_input.setText(self.api.token)
        layout.addWidget(token_input)

        key_hint = QLabel('从 DeepSeek 网站手动获取的 Token')
        key_hint.setStyleSheet('color: #888888; font-size: 11px;')
        layout.addWidget(key_hint)

        layout.addSpacing(10)

        # Base URL 输入
        url_label = QLabel('Base URL:')
        url_label.setStyleSheet('font-size: 13px; font-weight: bold;')
        layout.addWidget(url_label)

        url_input = QLineEdit()
        url_input.setPlaceholderText('https://chat.deepseek.com')
        url_input.setMinimumHeight(40)
        url_input.setText(self.api.base_url)
        layout.addWidget(url_input)

        url_hint = QLabel('API 服务器地址，可设置代理地址')
        url_hint.setStyleSheet('color: #888888; font-size: 11px;')
        layout.addWidget(url_hint)

        layout.addSpacing(15)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        ok_btn = QPushButton('保存')
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background-color: #5a9de9;
            }
        """)
        ok_btn.clicked.connect(lambda: self.save_settings_from_dialog(
            token_input.text(), url_input.text(), email_input.text(), password_input.text(), dialog
        ))

        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def save_settings_from_dialog(self, token, base_url, email, password, dialog):
        """保存设置"""
        if token:
            self.api.set_token(token)
        if base_url:
            self.api.base_url = base_url
            self.api.default_headers['Origin'] = base_url
            self.api.default_headers['Referer'] = f'{base_url}/'
        if email:
            self.api.email = email
        if password:
            self.api.password = password

        self.update_status(bool(token))
        self.send_btn.setEnabled(bool(token))
        self.new_session_btn.setEnabled(bool(token))
        dialog.accept()

        # 保存到文件
        config_file = os.path.join(os.path.dirname(__file__), 'deepseek_login.json')
        try:
            config = {
                'token': token,
                'base_url': base_url,
                'email': email,
                'password': password if password else None  # 可选保存密码
            }
            # 移除 None 值
            config = {k: v for k, v in config.items() if v is not None}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            QMessageBox.information(self, '成功', '设置已保存!')
        except Exception as e:
            QMessageBox.warning(self, '警告', f'保存失败: {e}')

    def update_status(self, logged_in):
        """更新状态显示"""
        if logged_in:
            self.status_label.setText('● 已登录')
            self.status_label.setStyleSheet('color: #27ae60; font-size: 12px;')
        else:
            self.status_label.setText('● 未登录')
            self.status_label.setStyleSheet('color: #ff6b6b; font-size: 12px;')

    def create_new_session(self):
        """创建新 session"""
        self.new_session_btn.setEnabled(False)
        self.status_label.setText('● 连接中...')
        self.status_label.setStyleSheet('color: #f39c12; font-size: 12px;')

        self.session_worker = InitSessionWorker(self.api)
        self.session_worker.success_signal.connect(self.on_session_created)
        self.session_worker.error_signal.connect(self.on_session_error)
        self.session_worker.finished.connect(lambda: self.new_session_btn.setEnabled(True))
        self.session_worker.start()

    def on_session_created(self, session_id):
        """session 创建成功"""
        self.session_label.setText(f'#{session_id[:8]}')
        self.session_label.setStyleSheet('color: #666666; font-size: 10px;')
        self.status_label.setText('● 就绪')
        self.status_label.setStyleSheet('color: #27ae60; font-size: 12px;')
        self.send_btn.setEnabled(True)
        self.api.clear_history()  # 清空对话历史
        self.clear_files()  # 清空附件列表
        self.clear_chat()
        self.load_session_list()  # 刷新会话列表

    def on_session_error(self, error):
        """session 创建失败"""
        QMessageBox.warning(self, '错误', f'创建 session 失败: {error}')
        self.status_label.setText('● 错误')
        self.status_label.setStyleSheet('color: #ff6b6b; font-size: 12px;')

    def load_session_list(self):
        """加载会话列表"""
        if not self.api.token:
            return

        self.session_list.clear()

        try:
            sessions = self.api.get_session_list()
            for session in sessions:
                session_id = session.get('id', '')
                title = session.get('title', '新会话') or '新会话'
                created_at = session.get('inserted_at', 0)

                # 创建列表项
                item = QListWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, session_id)

                # 显示时间
                if created_at:
                    from datetime import datetime
                    try:
                        dt = datetime.fromtimestamp(created_at)
                        time_str = dt.strftime('%m-%d %H:%M')
                        item.setToolTip(f'{title}\n时间: {time_str}')
                    except:
                        pass

                self.session_list.addItem(item)

            # 高亮当前会话
            if self.api.session_id:
                for i in range(self.session_list.count()):
                    item = self.session_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == self.api.session_id:
                        self.session_list.setCurrentItem(item)
                        break

        except Exception as e:
            print(f'[会话列表] 加载失败: {e}')

    def on_session_clicked(self, item):
        """点击会话列表项"""
        session_id = item.data(Qt.ItemDataRole.UserRole)

        if session_id == self.api.session_id:
            return  # 已经是当前会话

        # 切换会话
        self.api.session_id = session_id
        self.api.clear_history()
        self.session_label.setText(f'#{session_id[:8]}')
        self.clear_chat()

        # 加载历史消息
        self.load_chat_history(session_id)

    def load_chat_history(self, session_id):
        """加载会话历史消息"""
        try:
            messages = self.api.get_chat_history(session_id)

            for msg in messages:
                role = msg.get('role', '')
                fragments = msg.get('fragments', [])

                # 从 fragments 中提取内容
                content = ''
                if role == 'USER':
                    # 用户消息: type='REQUEST'
                    for frag in fragments:
                        if frag.get('type') == 'REQUEST':
                            content = frag.get('content', '')
                            break
                elif role == 'ASSISTANT':
                    # AI消息: type='RESPONSE'
                    for frag in fragments:
                        if frag.get('type') == 'RESPONSE':
                            content = frag.get('content', '')
                            break

                if content:
                    self.add_message(content, is_user=(role == 'USER'))

        except Exception as e:
            print(f'[历史消息] 加载失败: {e}')

    def clear_chat(self):
        """清空聊天"""
        # 清除所有消息
        while self.messages_layout.count() > 1:  # 保留 stretch
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_message(self, content, is_user=True):
        """添加消息到聊天区域"""
        msg_widget = MessageWidget(content, is_user)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg_widget)

        # 滚动到底部
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def set_model_mode(self, mode):
        """设置模型模式"""
        self.current_model_type = mode
        if mode == 'default':
            self.quick_mode_btn.setChecked(True)
            self.expert_mode_btn.setChecked(False)
        elif mode == 'expert':
            self.quick_mode_btn.setChecked(False)
            self.expert_mode_btn.setChecked(True)

    def send_message(self):
        """发送消息"""
        message = self.input_edit.text().strip()
        if not message:
            return

        if not self.api.token:
            QMessageBox.warning(self, '提示', '请先设置 Token')
            return

        if not self.api.session_id:
            QMessageBox.warning(self, '提示', '请先创建会话')
            return

        # 清空输入
        self.input_edit.clear()

        # 保存用户消息到历史
        self.api.add_to_history('user', message)

        # 重置状态
        self.current_response = ""
        self.current_fragment_type = None
        self.thinking_content = ""
        self.pending_user_message = message  # 保存当前用户消息用于后续添加历史

        # 显示用户消息
        self.add_message(message, is_user=True)

        # 禁用发送按钮
        self.send_btn.setEnabled(False)
        self.status_label.setText('● 响应中...')
        self.status_label.setStyleSheet('color: #f39c12; font-size: 12px;')

        # 创建响应消息占位
        self.response_widget = MessageWidget('', is_user=False)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, self.response_widget)

        # 启动工作线程
        thinking = self.thinking_checkbox.isChecked()
        search_enabled = self.search_checkbox.isChecked()
        # 获取文件 ID 列表
        file_ids = [f['file_id'] for f in self.uploaded_files]
        worker = SendMessageWorker(
            self.api, message, thinking,
            self.current_model_type, search_enabled, file_ids
        )
        worker.chunk_received.connect(self.on_chunk_received)
        worker.message_id_signal.connect(self.on_message_id_received)
        worker.finished_signal.connect(self.on_message_finished)
        worker.error_signal.connect(self.on_message_error)
        worker.start()

        # 保存 worker 引用
        self.current_worker = worker

    def select_file(self):
        """选择文件上传"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择文件', '',
            '所有文件 (*);;PDF (*.pdf);;Word (*.doc *.docx);;Excel (*.xls *.xlsx);;'
            'PowerPoint (*.ppt *.pptx);;文本 (*.txt *.md);;图片 (*.png *.jpg *.jpeg *.gif)'
        )
        if file_path:
            self.upload_file(file_path)

    def upload_file(self, file_path):
        """上传文件"""
        if not self.api.session_id:
            QMessageBox.warning(self, '提示', '请先创建会话')
            return

        self.upload_btn.setEnabled(False)
        self.status_label.setText('● 上传中...')
        self.status_label.setStyleSheet('color: #f39c12; font-size: 12px;')

        self.upload_worker = UploadFileWorker(self.api, file_path)
        self.upload_worker.success_signal.connect(self.on_file_uploaded)
        self.upload_worker.error_signal.connect(self.on_upload_error)
        self.upload_worker.progress_signal.connect(lambda msg: self.status_label.setText(f'● {msg}'))
        self.upload_worker.finished.connect(lambda: self.upload_btn.setEnabled(True))
        self.upload_worker.start()

    def on_file_uploaded(self, file_info):
        """文件上传成功（Worker 已完成解析等待）"""
        self.uploaded_files.append(file_info)
        self.update_files_display()
        self.status_label.setText('● 就绪')
        self.status_label.setStyleSheet('color: #27ae60; font-size: 12px;')
        self.upload_btn.setEnabled(True)

    def on_upload_error(self, error):
        """文件上传失败"""
        QMessageBox.warning(self, '错误', f'上传失败: {error}')
        self.status_label.setText('● 错误')
        self.status_label.setStyleSheet('color: #ff6b6b; font-size: 12px;')
        self.upload_btn.setEnabled(True)

    def update_files_display(self):
        """更新附件列表显示"""
        # 清空现有显示
        while self.files_layout.count():
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 显示每个文件
        for file_info in self.uploaded_files:
            file_label = QPushButton(f'📎 {file_info["file_name"]}')
            file_label.setStyleSheet("""
                QPushButton {
                    background-color: #4a5568;
                    color: #e0e0e0;
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #5a6578;
                }
            """)
            file_label.setToolTip('点击移除')
            # 使用 lambda 传递参数
            file_label.clicked.connect(lambda checked, fi=file_info: self.remove_file(fi))
            self.files_layout.addWidget(file_label)

        # 显示附件框
        self.files_frame.setVisible(len(self.uploaded_files) > 0)

    def remove_file(self, file_info):
        """移除附件"""
        self.uploaded_files = [f for f in self.uploaded_files if f['file_id'] != file_info['file_id']]
        self.update_files_display()

    def clear_files(self):
        """清空所有附件"""
        self.uploaded_files = []
        self.update_files_display()

    def on_message_id_received(self, message_id):
        """收到 message_id"""
        self.api.set_parent_message_id(message_id)

    def on_chunk_received(self, chunk):
        """收到响应片段"""
        # 解析 SSE 格式
        if chunk.startswith('data: '):
            data_str = chunk[6:]
            if data_str == '[DONE]':
                return

            try:
                data = json.loads(data_str)

                # 1. 初始化响应结构: {"v":{"response":{"fragments":[{"type":"SEARCH"...}]}}}
                if 'v' in data and isinstance(data['v'], dict):
                    response = data['v'].get('response', {})
                    fragments = response.get('fragments', [])
                    if fragments:
                        # 获取当前最后一个 fragment 的类型
                        last_fragment = fragments[-1]
                        self.current_fragment_type = last_fragment.get('type', 'RESPONSE')
                        initial_content = last_fragment.get('content', '')

                        # 添加初始内容（仅 RESPONSE 类型）
                        if initial_content and self.current_fragment_type == 'RESPONSE':
                            self.current_response += initial_content
                            self._update_response_display()

                # 2. 添加新 fragment: {"p":"response/fragments","o":"APPEND","v":[{新fragment}]}
                elif data.get('p') == 'response/fragments' and data.get('o') == 'APPEND':
                    new_fragments = data.get('v', [])
                    if new_fragments:
                        last_new = new_fragments[-1]
                        self.current_fragment_type = last_new.get('type', 'RESPONSE')
                        initial_content = last_new.get('content', '')

                        if initial_content and self.current_fragment_type == 'RESPONSE':
                            self.current_response += initial_content
                            self._update_response_display()

                # 3. BATCH 批量操作: {"p":"response","o":"BATCH","v":[{嵌套操作}]}
                elif data.get('p') == 'response' and data.get('o') == 'BATCH':
                    batch_ops = data.get('v', [])
                    for op in batch_ops:
                        # 处理嵌套的 fragments APPEND 操作
                        if op.get('p') == 'fragments' and op.get('o') == 'APPEND':
                            new_fragments = op.get('v', [])
                            if new_fragments:
                                last_new = new_fragments[-1]
                                frag_type = last_new.get('type', 'RESPONSE')
                                # 更新当前 fragment 类型
                                self.current_fragment_type = frag_type
                                initial_content = last_new.get('content', '')
                                if initial_content and frag_type == 'RESPONSE':
                                    self.current_response += initial_content
                                    self._update_response_display()

                # 4. 内容更新: {"v":"text"} 或 {"p":"response/fragments/-1/content","v":"text"}
                elif 'v' in data and isinstance(data['v'], str):
                    text = data['v']
                    p = data.get('p', '')

                    # 检查是否是 fragment 内容更新
                    if p.startswith('response/fragments') or p == '':
                        # 根据当前 fragment 类型决定处理方式
                        if self.current_fragment_type == 'RESPONSE':
                            self.current_response += text
                            self._update_response_display()
                        elif self.current_fragment_type == 'THINK':
                            self.thinking_content += text
                        # SEARCH 类型忽略（只显示最终回答）

                # 兼容旧格式
                elif 'choices' in data:
                    for choice in data['choices']:
                        if 'delta' in choice and 'content' in choice['delta']:
                            text = choice['delta']['content']
                            self.current_response += text
                            self._update_response_display()

            except json.JSONDecodeError:
                pass

    def _update_response_display(self):
        """更新响应显示 - 支持 Markdown 并自动调整高度"""
        if self.response_widget:
            # 使用 objectName 查找 QTextBrowser
            content_browser = self.response_widget.findChild(QTextBrowser, 'content_browser')
            if content_browser:
                content_browser.setMarkdown(self.current_response)
                # 根据内容自动调整高度
                doc_height = content_browser.document().size().height()
                content_browser.setMinimumHeight(int(doc_height) + 10)

            # 滚动到底部
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )

    def on_message_finished(self):
        """消息完成"""
        self.send_btn.setEnabled(True)
        self.status_label.setText('● 就绪')
        self.status_label.setStyleSheet('color: #27ae60; font-size: 12px;')

        # 保存 AI 响应到历史
        if self.current_response and hasattr(self, 'pending_user_message'):
            self.api.add_to_history('assistant', self.current_response)

        # 清空附件列表
        self.clear_files()

        self.current_response = ""
        self.response_widget = None
        self.current_fragment_type = None
        self.thinking_content = ""

    def on_message_error(self, error):
        """消息发送错误"""
        QMessageBox.warning(self, '错误', f'发送失败: {error}')
        self.send_btn.setEnabled(True)
        self.status_label.setText('● 错误')
        self.status_label.setStyleSheet('color: #ff6b6b; font-size: 12px;')

        # 移除占位的响应 widget
        if self.response_widget:
            self.messages_layout.removeWidget(self.response_widget)
            self.response_widget.deleteLater()
            self.response_widget = None

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            '关于 DeepSeek Chat',
            'DeepSeek Chat Client\n\n'
            '现代灰色主题界面\n'
            '支持快速/专家模式\n'
            '支持思考模式和联网搜索\n\n'
            '版本: 1.0'
        )


# ==================== Main ====================

def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 深色主题配色
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(74, 144, 217))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = DeepSeekChatWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()