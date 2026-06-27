#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Chat Client - 使用 Playwright 控制浏览器
"""

import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont

from playwright.sync_api import sync_playwright

# 配置
DEEPSEEK_URL = "https://chat.deepseek.com"
CONFIG_FILE = Path(__file__).parent / "deepseek_login.json"


class BrowserWorker(QThread):
    """浏览器工作线程"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    browser_ready = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.browser = None
        self.page = None
        self.playwright = None

    def run(self):
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=False,  # 显示浏览器窗口
                args=['--start-maximized']
            )

            # 创建上下文，加载 cookies
            context = self.browser.new_context()

            # 加载保存的 cookies
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cookies = data.get("cookies", [])
                if cookies:
                    context.add_cookies(cookies)

            self.page = context.new_page()

            # 打开 DeepSeek
            self.page.goto(DEEPSEEK_URL)

            self.browser_ready.emit()

            # 保持浏览器运行
            while self.browser.is_connected():
                self.msleep(100)

        except Exception as e:
            self.error_occurred.emit(f"浏览器错误: {str(e)}")

    def send_message(self, message: str):
        """发送消息到浏览器"""
        try:
            if not self.page:
                self.error_occurred.emit("浏览器未初始化")
                return

            # 等待页面加载
            self.page.wait_for_selector('textarea, [contenteditable="true"]', timeout=5000)

            # 找到输入框并输入消息
            input_box = self.page.locator('textarea, [contenteditable="true"]').first
            input_box.fill(message)

            # 点击发送按钮
            send_btn = self.page.locator('button:has-text("发送"), button[type="submit"]').first
            send_btn.click()

            # 等待响应
            self.page.wait_for_timeout(2000)

            # 获取回复
            # DeepSeek 的回复通常在消息列表的最后一条
            responses = self.page.locator('.message-content, .chat-message, [data-role="assistant"]')
            if responses.count() > 0:
                last_response = responses.last.text_content()
                self.response_received.emit(last_response or "获取回复失败")
            else:
                # 尝试其他方式获取
                self.page.wait_for_timeout(3000)
                all_text = self.page.locator('.prose, .markdown, .response-text').last.text_content()
                self.response_received.emit(all_text or "等待响应...")

        except Exception as e:
            self.error_occurred.emit(f"发送失败: {str(e)}")

    def stop_browser(self):
        """停止浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


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

        welcome = QLabel("正在启动浏览器...")
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

    def clear_welcome(self):
        """清除欢迎消息"""
        if self.layout.count() > 1:
            item = self.layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.browser_worker = None
        self.setup_ui()
        self.start_browser()

    def setup_ui(self):
        self.setWindowTitle("DeepSeek Chat (浏览器模式)")
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

        self.status = QLabel("● 启动浏览器...")
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

    def start_browser(self):
        """启动浏览器"""
        self.browser_worker = BrowserWorker()
        self.browser_worker.browser_ready.connect(self.on_browser_ready)
        self.browser_worker.response_received.connect(self.on_response)
        self.browser_worker.error_occurred.connect(self.on_error)
        self.browser_worker.start()

    def on_browser_ready(self):
        """浏览器就绪"""
        self.status.setText("● 已连接")
        self.status.setStyleSheet("color: #90ee90; border: none;")
        self.chat_area.clear_welcome()
        self.chat_area.add_message("浏览器已启动，可以直接在浏览器中聊天，或在此发送消息", is_user=False)

    def on_response(self, text: str):
        """收到响应"""
        self.chat_area.add_message(text, is_user=False)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.input.setEnabled(True)

    def on_error(self, error: str):
        """错误"""
        self.chat_area.add_message(f"❌ {error}", is_user=False)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.input.setEnabled(True)

    def send_message(self):
        """发送消息"""
        text = self.input.toPlainText().strip()
        if not text:
            return

        self.chat_area.add_message(text, is_user=True)
        self.input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("发送中...")
        self.input.setEnabled(False)

        if self.browser_worker:
            self.browser_worker.send_message(text)

    def closeEvent(self, event):
        """关闭窗口"""
        if self.browser_worker:
            self.browser_worker.stop_browser()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()