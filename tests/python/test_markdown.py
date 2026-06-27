#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Markdown 渲染效果
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from PyQt6.QtWidgets import QApplication, QTextBrowser, QWidget, QVBoxLayout

app = QApplication(sys.argv)

widget = QWidget()
layout = QVBoxLayout(widget)

browser = QTextBrowser()
browser.setStyleSheet("""
    QTextBrowser {
        background-color: #353535;
        color: #d0d0d0;
        border: none;
        padding: 10px;
        font-size: 12px;
    }
""")

# 测试 Markdown 内容
test_markdown = """
**加粗文本** 和 *斜体文本*

## 标题二

### 标题三

- 列表项 1
- 列表项 2
- 列表项 3

1. 有序列表 1
2. 有序列表 2

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A   | B   | C   |
| D   | E   | F   |

`代码块`

> 引用文本

[链接](https://example.com)
"""

browser.setMarkdown(test_markdown)
layout.addWidget(browser)

widget.resize(500, 400)
widget.setWindowTitle('Markdown 渲染测试')
widget.show()

print('测试 Markdown 渲染:')
print('  加粗: **加粗文本**')
print('  斜体: *斜体文本*')
print('  标题: ## 标题二')
print('  列表: - 列表项')
print('  表格: | 列1 | 列2 | 列3 |')
print('  代码: `代码块`')
print('  引用: > 引用文本')
print('  链接: [链接](url)')
print('\n请检查窗口显示效果')
print('关闭窗口退出')

sys.exit(app.exec())