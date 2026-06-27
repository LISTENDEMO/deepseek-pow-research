#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Chat Client - PyQt6 GUI
"""

import sys
import json
import requests
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter


# 配置
DEEPSEEK_API_BASE = "https://chat.deepseek.com/api/v0"
TOKEN_FILE = Path(__file__).parent / "deepseek_login.json"


class ChatWorker(QThread):
    """后台聊天请求线程"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    session_created = pyqtSignal(str)  # 新会话ID信号

    def __init__(self, token: str, message: str, chat_session_id: str = None):
        super().__init__()
        self.token = token
        self.message = message
        self.chat_session_id = chat_session_id

    def run(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://chat.deepseek.com",
                "Referer": "https://chat.deepseek.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                "x-app-version": "20241129.1",
                "x-client-locale": "zh_CN",
                "x-client-platform": "web",
                "x-client-timezone-offset": "28800",
                "x-client-version": "1.8.0",
            }

            # 先创建会话（如果没有）
            if not self.chat_session_id:
                create_resp = requests.post(
                    f"{DEEPSEEK_API_BASE}/chat_session/create",
                    headers=headers,
                    json={"agent": "chat"}
                )
                if create_resp.status_code == 200:
                    create_data = create_resp.json()
                    self.chat_session_id = create_data.get("data", {}).get("biz_data", {}).get("id")
                    self.session_created.emit(self.chat_session_id)
                else:
                    self.error_occurred.emit(f"创建会话失败: {create_resp.status_code}")
                    return

            # 发送消息 - 使用正确的 API 格式
            payload = {
                "chat_session_id": self.chat_session_id,
                "prompt": self.message,
                "ref_file_ids": [],
            }

            resp = requests.post(
                f"{DEEPSEEK_API_BASE}/chat/completion",
                headers=headers,
                json=payload
            )

            if resp.status_code == 200:
                data = resp.json()
                # 解析响应
                if data.get("code") == 0:
                    biz_data = data.get("data", {}).get("biz_data", {})
                    # 提取回复内容
                    if "choices" in biz_data:
                        reply = biz_data["choices"][0].get("message", {}).get("content", "")
                    elif "messages" in biz_data:
                        # 从 messages 数组中获取 AI 回复
                        messages = biz_data.get("messages", [])
                        for msg in messages:
                            if msg.get("role") == "assistant":
                                reply = msg.get("content", "")
                                break
                        if not reply and messages:
                            reply = str(messages[-1].get("content", ""))
                    else:
                        reply = str(biz_data)
                    self.response_received.emit(reply if reply else "收到空响应")
                else:
                    self.error_occurred.emit(f"API错误: {data.get('msg', '未知错误')}")
            else:
                self.error_occurred.emit(f"请求失败: {resp.status_code} - {resp.text[:200]}")

        except Exception as e:
            self.error_occurred.emit(f"错误: {str(e)}")


class MessageBubble(QFrame):
    """消息气泡组件"""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.setup_ui(text)

    def setup_ui(self, text: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # 角色标签
        role_label = QLabel("我" if self.is_user else "DeepSeek")
        role_label.setFont(QFont("Microsoft YaHei", 9))
        role_label.setStyleSheet(f"color: {'#666' if self.is_user else '#0066cc'}; border: none; background: transparent;")
        layout.addWidget(role_label)

        # 消息内容
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text_label.setFont(QFont("Microsoft YaHei", 10))
        self.text_label.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.text_label)

        # 时间标签
        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setFont(QFont("Microsoft YaHei", 8))
        time_label.setStyleSheet("color: #999; border: none; background: transparent;")
        layout.addWidget(time_label)

        # 设置样式
        if self.is_user:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #e3f2fd;
                    border-radius: 12px;
                    border: 1px solid #bbdefb;
                }
            """)
        else:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #f5f5f5;
                    border-radius: 12px;
                    border: 1px solid #e0e0e0;
                }
            """)

        self.setMaximumWidth(600)


class ChatArea(QScrollArea):
    """聊天消息区域"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # 容器
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(16, 16, 16, 16)

        # 欢迎消息
        welcome = QLabel("欢迎使用 DeepSeek Chat")
        welcome.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet("color: #333; padding: 40px;")
        self.layout.addWidget(welcome)

        self.layout.addStretch()

        # 滚动区域设置
        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #fafafa;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #999;
            }
        """)

    def add_message(self, text: str, is_user: bool = True):
        """添加消息"""
        # 移除 stretch
        item = self.layout.takeAt(self.layout.count() - 1)
        if item and item.spacerItem():
            pass

        # 创建消息容器
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

        # 滚动到底部
        QTimer.singleShot(100, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        """滚动到底部"""
        vbar = self.verticalScrollBar()
        vbar.setValue(vbar.maximum())


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

        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部栏
        self.setup_header(main_layout)

        # 聊天区域
        self.chat_area = ChatArea()
        main_layout.addWidget(self.chat_area, 1)

        # 输入区域
        self.setup_input_area(main_layout)

        # 窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #fafafa;
            }
        """)

    def setup_header(self, parent_layout):
        """设置顶部栏"""
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a73e8, stop:1 #4285f4);
            }
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # 标题
        title = QLabel("DeepSeek Chat")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white; border: none; background: transparent;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 状态指示
        self.status_label = QLabel("● 未连接")
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.9); border: none; background: transparent;")
        header_layout.addWidget(self.status_label)

        parent_layout.addWidget(header)

    def setup_input_area(self, parent_layout):
        """设置输入区域"""
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top: 1px solid #e0e0e0;
            }
        """)
        input_frame.setFixedHeight(100)

        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 15, 20, 15)
        input_layout.setSpacing(12)

        # 输入框
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息... (Ctrl+Enter 发送)")
        self.input_field.setFont(QFont("Microsoft YaHei", 11))
        self.input_field.setMaximumHeight(70)
        self.input_field.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                background-color: #fafafa;
            }
            QTextEdit:focus {
                border-color: #1a73e8;
                background-color: white;
            }
        """)
        input_layout.addWidget(self.input_field, 1)

        # 发送按钮
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 70)
        self.send_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a73e8, stop:1 #1557b0);
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1557b0, stop:1 #0d47a1);
            }
            QPushButton:pressed {
                background: #0d47a1;
            }
            QPushButton:disabled {
                background: #ccc;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        parent_layout.addWidget(input_frame)

        # 快捷键
        self.input_field.installEventFilter(self)

    def eventFilter(self, obj, event):
        """事件过滤器 - Ctrl+Enter 发送"""
        if obj == self.input_field and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def load_token(self):
        """加载 Token"""
        try:
            if TOKEN_FILE.exists():
                with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.token = data.get("token")

                if self.token:
                    self.status_label.setText("● 已连接")
                    self.status_label.setStyleSheet("color: #90ee90; border: none; background: transparent;")
                    print(f"Token 加载成功: {self.token[:20]}...")
                else:
                    print("未能从文件中提取 Token")
        except Exception as e:
            print(f"加载 Token 失败: {e}")

    def send_message(self):
        """发送消息"""
        text = self.input_field.toPlainText().strip()
        if not text or not self.token:
            return

        # 添加用户消息
        self.chat_area.add_message(text, is_user=True)
        self.input_field.clear()

        # 禁用输入
        self.send_btn.setEnabled(False)
        self.send_btn.setText("发送中...")
        self.input_field.setEnabled(False)

        # 添加加载提示
        self.chat_area.add_message("思考中...", is_user=False)

        # 后台请求
        self.worker = ChatWorker(self.token, text, self.chat_session_id)
        self.worker.response_received.connect(self.on_response)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.session_created.connect(self.on_session_created)
        self.worker.start()

    def on_session_created(self, session_id: str):
        """会话创建成功"""
        self.chat_session_id = session_id
        print(f"会话已创建: {session_id}")

    def on_response(self, text: str):
        """收到响应"""
        # 移除加载提示 (最后一条消息)
        self.remove_last_message()

        # 添加 AI 回复
        self.chat_area.add_message(text, is_user=False)

        # 恢复输入
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def on_error(self, error: str):
        """出错"""
        self.remove_last_message()
        self.chat_area.add_message(f"❌ {error}", is_user=False)

        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.input_field.setEnabled(True)

    def remove_last_message(self):
        """移除最后一条消息"""
        count = self.chat_area.layout.count()
        if count > 1:
            item = self.chat_area.layout.takeAt(count - 2)
            if item and item.widget():
                item.widget().deleteLater()


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()