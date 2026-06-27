#!/usr/bin/env python3
"""
分析 WASM 全局变量和数据段
"""

from pathlib import Path
import struct

wasm_path = Path(__file__).parent / "sha3_wasm.wasm"
wasm_bytes = wasm_path.read_bytes()

def parse_leb128(data, offset):
    """解析无符号 LEB128"""
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7f) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, offset

def parse_sections(data):
    offset = 8  # 跳过魔数和版本
    sections = {}

    while offset < len(data):
        section_id = data[offset]
        offset += 1

        size, offset = parse_leb128(data, offset)
        section_data = data[offset:offset + size]
        offset += size

        section_names = {
            0: 'custom', 1: 'type', 2: 'import', 3: 'function',
            4: 'table', 5: 'memory', 6: 'global', 7: 'export',
            8: 'start', 9: 'element', 10: 'code', 11: 'data'
        }
        name = section_names.get(section_id, f'unknown_{section_id}')
        sections[name] = section_data

    return sections

sections = parse_sections(wasm_bytes)

# 解析 global section
print("解析 global section:")
print("=" * 60)

global_data = sections['global']
offset = 0
num_globals, offset = parse_leb128(global_data, offset)

print(f"全局变量数量: {num_globals}")

value_type_names = {
    0x7F: 'i32', 0x7E: 'i64', 0x7D: 'f32', 0x7C: 'f64'
}

globals_list = []
for i in range(num_globals):
    val_type = global_data[offset]
    offset += 1
    type_name = value_type_names.get(val_type, f'unknown_{val_type}')

    # mutability
    mutable = global_data[offset]
    offset += 1

    # init expression
    # 常见的初始化指令: i32.const, i64.const, global.get, end
    init_expr = []
    while True:
        opcode = global_data[offset]
        offset += 1

        if opcode == 0x41:  # i32.const
            val, offset = parse_leb128(global_data, offset)
            init_expr.append(('i32.const', val))
        elif opcode == 0x42:  # i64.const
            val, offset = parse_leb128(global_data, offset)
            init_expr.append(('i64.const', val))
        elif opcode == 0x23:  # global.get
            idx, offset = parse_leb128(global_data, offset)
            init_expr.append(('global.get', idx))
        elif opcode == 0x0B:  # end
            init_expr.append(('end', None))
            break
        else:
            init_expr.append(('unknown_opcode', opcode))

    globals_list.append({
        'index': i,
        'type': type_name,
        'mutable': mutable == 1,
        'init': init_expr
    })

    print(f"  Global {i}:")
    print(f"    类型: {type_name}")
    print(f"    可变: {mutable == 1}")
    print(f"    初始化: {init_expr}")

# 解析 data section
print("\n解析 data section:")
print("=" * 60)

data_section = sections['data']
offset = 0
num_data, offset = parse_leb128(data_section, offset)

print(f"数据段数量: {num_data}")

for i in range(num_data):
    # flags/memory index
    flags = data_section[offset]
    offset += 1

    # offset expression
    offset_expr = []
    while True:
        opcode = data_section[offset]
        offset += 1

        if opcode == 0x41:  # i32.const
            val, offset = parse_leb128(data_section, offset)
            offset_expr.append(('i32.const', val))
        elif opcode == 0x0B:  # end
            offset_expr.append(('end', None))
            break
        else:
            offset_expr.append(('unknown', opcode))

    # data size
    data_size, offset = parse_leb128(data_section, offset)

    # data bytes
    data_bytes = data_section[offset:offset + data_size]
    offset += data_size

    memory_offset = offset_expr[0][1] if offset_expr[0][0] == 'i32.const' else 0

    print(f"  Data segment {i}:")
    print(f"    内存偏移: {memory_offset}")
    print(f"    大小: {data_size} 字节")
    print(f"    前32字节: {data_bytes[:32].hex()}")
    print(f"    ASCII (前50): {data_bytes[:50]}")

    # 如果是字符串数据，显示更多
    try:
        text = data_bytes.decode('utf-8', errors='replace')
        if text.isprintable() or len(text) < 100:
            print(f"    内容: {text[:100]}...")
    except:
        pass

# 解析 memory section
print("\n解析 memory section:")
print("=" * 60)

mem_data = sections['memory']
offset = 0
num_mem, offset = parse_leb128(mem_data, offset)

for i in range(num_mem):
    flags = mem_data[offset]
    offset += 1

    min_pages, offset = parse_leb128(mem_data, offset)

    if flags & 1:  # has max
        max_pages, offset = parse_leb128(mem_data, offset)
    else:
        max_pages = None

    print(f"  Memory {i}:")
    print(f"    最小页数: {min_pages} (每页 64KB)")
    print(f"    最大页数: {max_pages}")
    print(f"    内存大小: {min_pages * 64} KB")

# 解析 start section (如果有)
if 'start' in sections:
    print("\n解析 start section:")
    print("=" * 60)
    start_data = sections['start']
    func_idx = parse_leb128(start_data, 0)[0]
    print(f"  启动函数索引: {func_idx}")