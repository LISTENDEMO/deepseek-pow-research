#!/usr/bin/env python3
"""
分析 WASM 二进制，提取 Keccak 算法细节
"""

import struct

def read_wasm(filepath):
    """读取 WASM 文件并分析结构"""
    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"WASM 文件大小: {len(data)} bytes")

    # WASM 魔数
    magic = data[0:4]
    if magic != b'\x00asm':
        print(f"警告: 魔数不是标准 WASM: {magic.hex()}")
    else:
        print("魔数: \\x00asm (标准 WASM)")

    # 版本
    version = struct.unpack('<I', data[4:8])[0]
    print(f"版本: {version}")

    # 解析 sections
    pos = 8
    sections = {}

    section_names = {
        0: 'Custom',
        1: 'Type',
        2: 'Import',
        3: 'Function',
        4: 'Table',
        5: 'Memory',
        6: 'Global',
        7: 'Export',
        8: 'Start',
        9: 'Element',
        10: 'Code',
        11: 'Data',
        12: 'DataCount',
    }

    while pos < len(data):
        section_id = data[pos]
        pos += 1

        # LEB128 编码的 section 大小
        size = 0
        shift = 0
        while True:
            byte = data[pos]
            pos += 1
            size |= (byte & 0x7f) << shift
            if byte & 0x80 == 0:
                break
            shift += 7

        section_data = data[pos:pos+size]
        pos += size

        name = section_names.get(section_id, f'Section_{section_id}')
        sections[section_id] = (name, section_data)
        print(f"Section {section_id} ({name}): {size} bytes")

    # 分析 Export section (找到导出的函数)
    if 7 in sections:
        print("\n导出函数分析:")
        export_data = sections[7][1]
        analyze_exports(export_data)

    # 分析 Code section (找到函数实现)
    if 10 in sections:
        print("\n函数代码分析 (前几个函数):")
        code_data = sections[10][1]
        analyze_code(code_data[:2000])  # 只分析前 2000 bytes

    return sections

def analyze_exports(data):
    """分析导出 section"""
    pos = 0

    # 导出数量 (LEB128)
    count = read_leb128(data, pos)
    pos += leb128_len(data, pos)

    print(f"  导出数量: {count}")

    exports = []
    for i in range(count):
        # 名称长度
        name_len = read_leb128(data, pos)
        pos += leb128_len(data, pos)

        # 名称
        name = data[pos:pos+name_len].decode('utf-8')
        pos += name_len

        # 类型 (0=func, 1=table, 2=memory, 3=global)
        kind = data[pos]
        pos += 1

        # 索引
        index = read_leb128(data, pos)
        pos += leb128_len(data, pos)

        exports.append((name, kind, index))
        print(f"    - {name} (类型={kind}, 索引={index})")

    return exports

def analyze_code(data):
    """分析代码 section"""
    pos = 0

    # 函数数量
    count = read_leb128(data, pos)
    pos += leb128_len(data, pos)

    print(f"  函数数量: {count}")

    # 分析第一个函数
    if count > 0:
        # 函数体大小
        body_size = read_leb128(data, pos)
        pos += leb128_len(data, pos)

        print(f"  函数 0 代码大小: {body_size} bytes")

        # Local declarations
        local_count = read_leb128(data, pos)
        pos += leb128_len(data, pos)

        print(f"  函数 0 local 块数量: {local_count}")

        for i in range(local_count):
            n = read_leb128(data, pos)
            pos += leb128_len(data, pos)
            t = data[pos]
            pos += 1
            print(f"    - {n} 个类型 {t} 的 local")

        # 显示一些指令
        print(f"  函数 0 前 50 bytes 指令:")
        instructions = data[pos:pos+50]
        for i, byte in enumerate(instructions[:30]):
            print(f"    {i}: 0x{byte:02x}")

def read_leb128(data, pos):
    """读取 LEB128 无符号整数"""
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        result |= (byte & 0x7f) << shift
        pos += 1
        if byte & 0x80 == 0:
            break
        shift += 7
    return result

def leb128_len(data, pos):
    """计算 LEB128 编码的长度"""
    length = 0
    while True:
        byte = data[pos + length]
        length += 1
        if byte & 0x80 == 0:
            break
    return length

# 运行分析
if __name__ == '__main__':
    sections = read_wasm('sha3_wasm.wasm')