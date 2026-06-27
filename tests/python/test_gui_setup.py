#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 WASM solver 和 API 集成
"""

import sys
import os
import json
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

# 测试 WASM solver
print("=" * 60)
print("测试 WASM Solver")
print("=" * 60)

solver_path = os.path.join(os.path.dirname(__file__), 'deepseek_pow_solver.js')

test_input = json.dumps({
    'challenge': 'af70a16344572354132d73d8e5e756df45e8450179e6b640978a03bca765ddbd',
    'salt': '811e05c93d1b71993710',
    'expire_at': 1776153216159,
    'difficulty': 144000
})

print(f"测试数据:")
print(f"  Challenge: af70a163...")
print(f"  Salt: 811e05c93d1b71993710")
print(f"  Expected answer: 69992")

print(f"\n调用 Node.js WASM solver...")
result = subprocess.run(
    ['node', solver_path],
    input=test_input,
    capture_output=True,
    text=True,
    cwd=os.path.dirname(__file__)
)

print(f"  Return code: {result.returncode}")

if result.returncode == 0:
    output = json.loads(result.stdout)
    print(f"  Success: {output.get('success')}")
    print(f"  Answer: {output.get('answer')}")
    print(f"  Expected: 69992")
    print(f"  Match: {output.get('answer') == 69992}")

    if output.get('answer') == 69992:
        print("\n✓ WASM solver 工作正常!")
    else:
        print("\n✗ WASM solver 返回错误答案")
else:
    print(f"  Error: {result.stderr}")
    print("\n✗ WASM solver 失败")

# 测试 PyQt6
print("\n" + "=" * 60)
print("测试 PyQt6")
print("=" * 60)

try:
    from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
    print("  PyQt6 导入成功")

    # 创建简单测试窗口
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    label = QLabel("PyQt6 测试成功!")
    layout.addWidget(label)
    window.setWindowTitle("DeepSeek GUI Test")
    window.resize(300, 100)
    window.show()
    print("  窗口创建成功")

    # 不阻塞，只测试创建
    print("\n✓ PyQt6 准备就绪!")
    print("\n运行完整 GUI:")
    print("  python deepseek_gui.py")

except ImportError as e:
    print(f"  Error: {e}")
    print("\n✗ PyQt6 未安装")
    print("  安装: pip install PyQt6")