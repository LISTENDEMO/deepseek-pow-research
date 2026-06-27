#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Chat Client - 纯 Python 实现 PoW 算法
"""

import sys
import json
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont


# 配置
DEEPSEEK_API_BASE = "https://chat.deepseek.com/api/v0"
CONFIG_FILE = Path(__file__).parent / "deepseek_login.json"


def keccak256_hex(data: str) -> str:
    """计算 Keccak256 (SHA-3) hash，返回十六进制字符串"""
    # Python hashlib 的 sha3_256 就是 Keccak256
    return hashlib.sha3_256(data.encode('utf-8')).hexdigest()


def solve_pow_challenge(challenge: str, salt: str, difficulty: int, expire_at: int) -> int:
    """
    解决 DeepSeek PoW 挑战
    找到满足: Keccak256(salt + "_" + expire_at + "_" + answer) == challenge 的 answer

    Args:
        challenge: 目标 hash (十六进制)
        salt: 盐值
        difficulty: 最大尝试次数 (答案范围 0 ~ difficulty)
        expire_at: 过期时间戳

    Returns:
        answer: 满足条件的整数答案
    """
    prefix = f"{salt}_{expire_at}_"

    # 使用多线程加速搜索
    chunk_size = max(10000, difficulty // 100)

    def search_range(start: int, end: int) -> int:
        for i in range(start, end):
            if keccak256_hex(prefix + str(i)) == challenge:
                return i
        return -1

    # 分块并行搜索
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for start in range(0, difficulty, chunk_size):
            end = min(start + chunk_size, difficulty)
            futures.append(executor.submit(search_range, start, end))

        for future in as_completed(futures):
            result = future.result()
            if result >= 0:
                # 取消其他任务
                for f in futures:
                    f.cancel()
                return result

    raise ValueError(f"未找到 PoW 答案 (difficulty={difficulty})")


class ChatWorker(QThread):
    """后台聊天请求线程"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    session_created = pyqtSignal(str)

    def __init__(self, token: str, message: str, chat_session_id: str = None):
        super().__init__()
        self.token = token
        self.message = message
        self.chat_session_id = chat_session_id

    def get_headers(self) -> dict:
        """获取请求 headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://chat.deepseek.com",
            "Referer": "https://chat.deepseek.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "x-app-version": "20241129.1",
            "x-client-locale": "zh_CN",
            "x-client-platform": "web",
            "x-client-timezone-offset": "28800",
            "x-client-version": "1.8.0",
        }

    def get_pow_challenge(self, target_path: str) -> dict:
        """获取 PoW 挑战"""
        resp = requests.post(
            f"{DEEPSEEK_API_BASE}/chat/create_pow_challenge",
            headers=self.get_headers(),
            json={"target_path": target_path}
        )
        if resp.status_code != 200:
            raise Exception(f"获取 PoW 挑战失败: {resp.status_code}")

        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"API 错误: {data.get('msg')}")

        return data["data"]["biz_data"]["challenge"]

    def solve_and_build_pow_header(self, challenge_data: dict) -> str:
        """解决 PoW 并构建 header"""
        # 解决挑战
        answer = solve_pow_challenge(
            challenge=challenge_data["challenge"],
            salt=challenge_data["salt"],
            difficulty=challenge_data["difficulty"],
            expire_at=challenge_data["expire_at"]
        )

        # 构建 PoW response header
        pow_response = {
            "algorithm": challenge_data["algorithm"],
            "challenge": challenge_data["challenge"],
            "salt": challenge_data["salt"],
            "answer": answer,
            "signature": challenge_data["signature"],
            "target_path": challenge_data["target_path"]
        }

        return json.dumps(pow_response)

    def run(self):
        try:
            headers = self.get_headers()

            # 创建会话（如果需要）
            if not self.chat_session_id:
                create_resp = requests.post(
                    f"{DEEPSEEK_API_BASE}/chat_session/create",
                    headers=headers,
                    json={}
                )
                if create_resp.status_code == 200:
                    create_data = create_resp.json()
                    self.chat_session_id = create_data.get("data", {}).get("biz_data", {}).get("chat_session", {}).get("id")
                    if self.chat_session_id:
                        self.session_created.emit(self.chat_session_id)
                else:
                    self.error_occurred.emit(f"创建会话失败: {create_resp.status_code}")
                    return

            # 获取 PoW 挑战
            pow_challenge = self.get_pow_challenge("/api/v0/chat/completion")

            # 解决 PoW
            pow_header = self.solve_and_build_pow_header(pow_challenge)

            # 添加 PoW header
            headers["x-ds-pow-response"] = pow_header

            # 发送消息
            payload = {
                "chat_session_id": self.chat_session_id,
                "parent_message_id": None,
                "model_type": "default",
                "prompt": self.message,
                "ref_file_ids": [],
                "thinking_enabled": True,
                "search_enabled": True,
                "preempt": False
            }

            resp = requests.post(
                f"{DEEPSEEK_API_BASE}/chat/completion",
                headers=headers,
                json=payload
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    # 解析响应 - DeepSeek 使用 SSE 流式响应
                    # 这里简化处理，直接显示响应
                    biz_data = data.get("data", {}).get("biz_data", {})
                    reply = biz_data.get("text") or str(biz_data)
                    self.response_received.emit(reply if reply else "响应已接收")
                else:
                    self.error_occurred.emit(f"API 错误: {data.get('msg')}")
            else:
                self.error_occurred.emit(f"请求失败: {resp.status_code} - {resp.text[:200]}")

        except Exception as e:
            self.error_occurred.emit(f"错误: {str(e)}")


class MessageBubble(QFrame):
    """消息气泡"""

    def __init__(self, text: str, is_user: bool = True):
        super().__init__()
        self.setup_ui(text, is_user)

    def setup_ui(self, text: str, is_user: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        role = QLabel("我" if is_user else "DeepSeek")
        role.setFont(QFont("Microsoft YaHei", 9))
        role.setStyleSheet(f"color: {'#666' if is_user else '#0066cc'}; border: none; background: transparent;")
        layout.addWidget(role)

        content = QLabel(text)
        content.setWordWrap(True)
        content.setFont(QFont("Microsoft YaHei", 10))
        content.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(content)

        time = QLabel(datetime.now().strftime("%H:%M"))
        time.setFont(QFont("Microsoft YaHei", 8))
        time.setStyleSheet("color: #999; border: none; background: transparent;")
        layout.addWidget(time)

        if is_user:
            self.setStyleSheet("background-color: #e3f2fd; border-radius: 12px; border: 1px solid #bbdefb;")
        else:
            self.setStyleSheet("background-color: #f5f5f5; border-radius: 12px; border: 1px solid #e0e0e0;")
        self.setMaximumWidth(600)


class ChatArea(QScrollArea):
    """聊天区域"""

    def __init__(self):
        super().__init__()
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(16, 16, 16, 16)

        welcome = QLabel("欢迎使用 DeepSeek Chat")
        welcome.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet("color: #333; padding: 40px;")
        self.layout.addWidget(welcome)
        self.layout.addStretch()

        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { border: none; background-color: #fafafa; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #ccc; border-radius: 4px; min-height: 30px; }
        """)

    def add_message(self, text: str, is_user: bool = True):
        item = self.layout.takeAt(self.layout.count() - 1)

        msg_container = QWidget()
        msg_layout = QHBoxLayout(msg_container)
        msg_layout.setContentsMargins(0, 0, 0, 0)

        bubble = MessageBubble(text, is_user)
        if is_user:
            msg_layout.addStretch()
            msg_layout.addWidget(bubble)
        else:
            msg_layout.addWidget(bubble)
            msg_layout.addStretch()

        self.layout.addWidget(msg_container)
        self.layout.addStretch()
        QTimer.singleShot(100, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.token = None
        self.chat_session_id = None
        self.worker = None
        self.setup_ui()
        self.load_token()

    def setup_ui(self):
        self.setWindowTitle("DeepSeek Chat")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a73e8, stop:1 #4285f4);")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("DeepSeek Chat")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white; border: none;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.status = QLabel("● 未连接")
        self.status.setFont(QFont("Microsoft YaHei", 10))
        self.status.setStyleSheet("color: rgba(255,255,255,0.9); border: none;")
        header_layout.addWidget(self.status)
        layout.addWidget(header)

        # 聊天区域
        self.chat_area = ChatArea()
        layout.addWidget(self.chat_area, 1)

        # 输入区域
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: white; border-top: 1px solid #e0e0e0;")
        input_frame.setFixedHeight(100)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 15, 20, 15)
        input_layout.setSpacing(12)

        self.input = QTextEdit()
        self.input.setPlaceholderText("输入消息... (Ctrl+Enter 发送)")
        self.input.setFont(QFont("Microsoft YaHei", 11))
        self.input.setMaximumHeight(70)
        self.input.setStyleSheet("""
            QTextEdit { border: 2px solid #e0e0e0; border-radius: 8px; padding: 8px; background: #fafafa; }
            QTextEdit:focus { border-color: #1a73e8; background: white; }
        """)
        self.input.installEventFilter(self)
        input_layout.addWidget(self.input, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 70)
        self.send_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.send_btn.setStyleSheet("""
            QPushButton { background: #1a73e8; color: white; border: none; border-radius: 8px; }
            QPushButton:hover { background: #1557b0; }
            QPushButton:disabled { background: #ccc; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        layout.addWidget(input_frame)

    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def load_token(self):
        """加载 Token"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.token = data.get("token")
                if self.token:
                    self.status.setText("● 已连接")
                    self.status.setStyleSheet("color: #90ee90; border: none;")
        except Exception as e:
            print(f"加载 Token 失败: {e}")

    def send_message(self):
        """发送消息"""
        text = self.input.toPlainText().strip()
        if not text or not self.token:
            return

        self.chat_area.add_message(text, is_user=True)
        self.input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("计算 PoW...")
        self.input.setEnabled(False)

        self.worker = ChatWorker(self.token, text, self.chat_session_id)
        self.worker.response_received.connect(self.on_response)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.session_created.connect(self.on_session_created)
        self.worker.start()

    def on_session_created(self, session_id: str):
        """会话创建成功"""
        self.chat_session_id = session_id
        print(f"会话 ID: {session_id}")

    def on_response(self, text: str):
        """收到响应"""
        self.chat_area.add_message(text, is_user=False)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.input.setEnabled(True)
        self.input.setFocus()

    def on_error(self, error: str):
        """错误"""
        self.chat_area.add_message(f"❌ {error}", is_user=False)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.input.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()