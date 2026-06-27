#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟完整 GUI 测试 - 验证 objectName 查找
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from PyQt6.QtWidgets import QApplication, QLabel, QFrame, QVBoxLayout

app = QApplication(sys.argv)

# 创建 MessageWidget
widget = QFrame()
layout = QVBoxLayout(widget)

role_label = QLabel('DeepSeek')
role_label.setObjectName('role_label')
layout.addWidget(role_label)

content_label = QLabel('')
content_label.setObjectName('content_label')
layout.addWidget(content_label)

print('=' * 60)
print('测试 objectName 查找')
print('=' * 60)

# 测试查找
labels = widget.findChildren(QLabel)
print(f'找到 {len(labels)} 个 QLabel')
for i, label in enumerate(labels):
    print(f'  [{i}] objectName="{label.objectName()}", text="{label.text()[:30]}..."')

# 使用 objectName 查找
content_label_found = widget.findChild(QLabel, 'content_label')
print(f'\n使用 objectName 查找 content_label: {content_label_found is not None}')

# 更新内容（包含 "DeepSeek"）
test_content = "你好！我是DeepSeek，很高兴见到你！"
content_label_found.setText(test_content)
print(f'更新后 content_label.text() = "{content_label_found.text()}"')

# 验证不会被 role_label 的检查误判
print('\n验证旧逻辑的问题:')
for label in labels:
    if 'DeepSeek' not in label.text():
        print(f'  会匹配到: objectName="{label.objectName()}"')
    else:
        print(f'  会跳过: objectName="{label.objectName()}", text="{label.text()[:30]}..."')

print('\n结论: 使用 objectName 查找解决了 "DeepSeek" 关键字冲突问题')