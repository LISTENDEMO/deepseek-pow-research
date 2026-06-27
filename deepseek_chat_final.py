#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Chat Client - 使用 Playwright 自动化浏览器

这是最可靠的方案，因为浏览器会自动处理：
- PoW (Proof of Work) 计算
- 动态加密 headers (x-hif-dliq, x-hif-leim)
- Cookies 管理
"""

import sys
import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont, QDesktopServices

# Playwright 安装提示
PLAYWRIGHT_INSTALLED = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_INSTALLED = True
except ImportError:
    pass

CONFIG_FILE = Path(__file__).parent / "deepseek_login.json"


class BrowserThread(QThread):
    """浏览器控制线程"""
    connected = pyqtSignal()
    disconnected = pyqtSignal(str)
    message_received = pyqtSignal(str, bool)  # text, is_user

    def __init__(self):
        super().__init__()
        self.playwright = None
        self.browser = None
        self.page = None
        self.running = True

    def run(self):
        if not PLAYWRIGHT_INSTALLED:
            self.disconnected.emit("请先安装 Playwright: pip install playwright && playwright install chromium")
            return

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False)

            # 加载保存的登录状态
            context = self.browser.new_context()
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cookies = data.get("cookies", [])
                if cookies:
                    context.add_cookies(cookies)

            self.page = context.new_page()
            self.page.goto("https://chat.deepseek.com")

            # 等待页面加载
            self.page.wait_for_load_state("networkidle", timeout=30000)

            # 检查是否已登录
            if self.page.locator('textarea, [contenteditable="true"]').count() > 0:
                self.connected.emit()
            else:
                self.disconnected.emit("请先在浏览器中登录 DeepSeek")

            # 保持运行
            while self.running and self.browser.is_connected():
                self.msleep(100)

        except Exception as e:
            self.disconnected.emit(str(e))

    def send_message(self, text: str):
        """发送消息"""
        if not self.page:
            return

        try:
            # 找到输入框
            input_box = self.page.locator('textarea, [contenteditable="true"]').first

            # 输入消息
            input_box.fill(text)
            self.message_received.emit(text, True)

            # 点击发送按钮或按 Enter
            try:
                send_btn = self.page.locator('button[type="submit"], button:has-text("发送")').first
                send_btn.click(timeout=5000)
            except:
                input_box.press("Enter")

            # 等待响应出现
            self.page.wait_for_timeout(2000)

            # 获取 AI 回复
            # DeepSeek 使用流式响应，需要等待完成
            self.page.wait_for_timeout(5000)

            # 获取最后一条消息（AI 回复）
            messages = self.page.locator('[data-role="assistant"], .assistant-message, .ai-message')
            if messages.count() > 0:
                reply = messages.last.text_content()
                self.message_received.emit(reply or "已发送", False)
            else:
                # 尝试其他方式获取
                self.page.wait_for_timeout(3000)
                content_area = self.page.locator('.markdown, .prose, .response-content')
                if content_area.count() > 0:
                    reply = content_area.last.text_content()
                    self.message_received.emit(reply or "等待响应...", False)

        except Exception as e:
            self.message_received.emit(f"错误: {str(e)}", False)

    def stop(self):
        """停止浏览器"""
        self.running = False
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass


class MessageBubble(QFrame):
    """消息气泡"""
    def __init__(self, text: str, is_user: bool):
        super().__init__()
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
        content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(content)

        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setFont(QFont("Microsoft YaHei", 8))
        time_label.setStyleSheet("color: #999; border: none; background: transparent;")
        layout.addWidget(time_label)

        self.setStyleSheet(f"""
            background-color: {'#e3f2fd' if is_user else '#f5f5f5'};
            border-radius: 12px;
            border: 1px solid {'#bbdefb' if is_user else '#e0e0e0'};
        """)
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

        self.welcome = QLabel("正在启动浏览器...")
        self.welcome.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome.setStyleSheet("color: #333; padding: 40px;")
        self.layout.addWidget(self.welcome)
        self.layout.addStretch()

        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { border: none; background-color: #fafafa; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #ccc; border-radius: 4px; min-height: 30px; }
        """)

    def add_message(self, text: str, is_user: bool):
        self.layout.takeAt(self.layout.count() - 1)

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

    def set_connected(self):
        self.welcome.setText("浏览器已连接\n请在下方输入消息或直接在浏览器中聊天")
        self.welcome.setStyleSheet("color: #28a745; padding: 40px;")

    def set_error(self, error: str):
        self.welcome.setText(f"连接失败: {error}")
        self.welcome.setStyleSheet("color: #dc3545; padding: 40px;")


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.browser_thread = None
        self.setup_ui()

        if not PLAYWRIGHT_INSTALLED:
            self.show_install_dialog()
        else:
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

        # 顶部栏
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

        self.status = QLabel("● 启动中...")
        self.status.setFont(QFont("Microsoft YaHei", 10))
        self.status.setStyleSheet("color: rgba(255,255,255,0.9); border: none;")
        header_layout.addWidget(self.status)

        # 打开浏览器按钮
        open_browser = QPushButton("打开浏览器")
        open_browser.setFont(QFont("Microsoft YaHei", 10))
        open_browser.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); border-radius: 4px; padding: 4px 12px; }
            QPushButton:hover { background: rgba(255,255,255,0.3); }
        """)
        open_browser.clicked.connect(self.open_browser_window)
        header_layout.addWidget(open_browser)

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
        self.input.setPlaceholderText("输入消息... (Ctrl+Enter 发送，或在浏览器中直接聊天)")
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

    def show_install_dialog(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("需要安装 Playwright")
        msg.setText("此程序需要 Playwright 来控制浏览器。\n\n请运行以下命令安装：\npip install playwright\nplaywright install chromium")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def start_browser(self):
        self.browser_thread = BrowserThread()
        self.browser_thread.connected.connect(self.on_connected)
        self.browser_thread.disconnected.connect(self.on_disconnected)
        self.browser_thread.message_received.connect(self.on_message)
        self.browser_thread.start()

    def on_connected(self):
        self.status.setText("● 已连接")
        self.status.setStyleSheet("color: #90ee90; border: none;")
        self.chat_area.set_connected()

    def on_disconnected(self, error: str):
        self.status.setText("● 断开")
        self.status.setStyleSheet("color: #dc3545; border: none;")
        self.chat_area.set_error(error)

    def on_message(self, text: str, is_user: bool):
        self.chat_area.add_message(text, is_user)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.input.setEnabled(True)

    def send_message(self):
        text = self.input.toPlainText().strip()
        if not text or not self.browser_thread:
            return

        self.input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("发送中...")
        self.input.setEnabled(False)

        self.browser_thread.send_message(text)

    def open_browser_window(self):
        """提示用户查看浏览器窗口"""
        QMessageBox.information(self, "提示", "浏览器窗口已在后台打开。\n你可以直接在浏览器中登录和聊天，\n也可以在此发送消息。")

    def closeEvent(self, event):
        if self.browser_thread:
            self.browser_thread.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()