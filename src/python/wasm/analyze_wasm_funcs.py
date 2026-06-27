#!/usr/bin/env python3
"""
分析 WASM element section 和 code section
"""

from pathlib import Path

wasm_path = Path(__file__).parent / "sha3_wasm.wasm"
wasm_bytes = wasm_path.read_bytes()

def parse_leb128(data, offset):
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
    offset = 8
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

# 解析 element section
print("解析 element section:")
print("=" * 60)

if 'element' in sections:
    elem_data = sections['element']
    offset = 0
    num_elem, offset = parse_leb128(elem_data, offset)

    print(f"元素段数量: {num_elem}")

    for i in range(num_elem):
        # flags/table index
        flags = elem_data[offset]
        offset += 1

        # offset expression
        offset_expr = []
        while True:
            opcode = elem_data[offset]
            offset += 1
            if opcode == 0x41:  # i32.const
                val, offset = parse_leb128(elem_data, offset)
                offset_expr.append(('i32.const', val))
            elif opcode == 0x0B:  # end
                break
            else:
                offset_expr.append(('unknown', opcode))

        table_offset = offset_expr[0][1] if offset_expr else 0

        # number of elements
        num_funcs, offset = parse_leb128(elem_data, offset)

        # function indices
        func_indices = []
        for _ in range(num_funcs):
            idx, offset = parse_leb128(elem_data, offset)
            func_indices.append(idx)

        print(f"  Element {i}:")
        print(f"    表偏移: {table_offset}")
        print(f"    函数索引: {func_indices}")

# 解析 type section 以获取函数类型
type_data = sections['type']
offset = 0
num_types, offset = parse_leb128(type_data, offset)

types = []
for _ in range(num_types):
    form = type_data[offset]
    offset += 1
    if form == 0x60:
        num_params, offset = parse_leb128(type_data, offset)
        params = []
        for _ in range(num_params):
            param_type = type_data[offset]
            offset += 1
            params.append(param_type)
        num_results, offset = parse_leb128(type_data, offset)
        results = []
        for _ in range(num_results):
            result_type = type_data[offset]
            offset += 1
            results.append(result_type)
        types.append((params, results))

# 解析 function section (函数到类型的映射)
func_data = sections['function']
offset = 0
num_funcs, offset = parse_leb128(func_data, offset)

type_indices = []
for _ in range(num_funcs):
    idx, offset = parse_leb128(func_data, offset)
    type_indices.append(idx)

print(f"\n函数列表 ({num_funcs} 个):")
print("=" * 60)

value_type_names = {0x7F: 'i32', 0x7E: 'i64', 0x7D: 'f32', 0x7C: 'f64'}

for func_idx in range(min(num_funcs, 50)):
    type_idx = type_indices[func_idx]
    params, results = types[type_idx]
    param_names = [value_type_names.get(p, f'0x{p:02x}') for p in params]
    result_names = [value_type_names.get(r, f'0x{r:02x}') for r in results]

    print(f"  函数 {func_idx}: 类型 {type_idx}")
    print(f"    参数: {param_names}")
    print(f"    返回: {result_names}")

# 找出 wasm_solve 和 wasm_deepseek_hash_v1 对应的函数
print("\n关键函数:")
print("=" * 60)

# wasm_solve 是 export, index=1
# wasm_deepseek_hash_v1 是 export, index=6

key_funcs = [(1, 'wasm_solve'), (6, 'wasm_deepseek_hash_v1'), (23, 'error_func_23'), (36, 'error_func_36')]

for func_idx, name in key_funcs:
    if func_idx < len(type_indices):
        type_idx = type_indices[func_idx]
        params, results = types[type_idx]
        param_names = [value_type_names.get(p, f'0x{p:02x}') for p in params]
        result_names = [value_type_names.get(r, f'0x{r:02x}') for r in results]
        print(f"  {name} (index={func_idx}):")
        print(f"    类型索引: {type_idx}")
        print(f"    参数: {param_names}")
        print(f"    返回: {result_names}")

# 解析 table section
print("\n解析 table section:")
print("=" * 60)

if 'table' in sections:
    table_data = sections['table']
    offset = 0
    num_tables, offset = parse_leb128(table_data, offset)

    for i in range(num_tables):
        elem_type = table_data[offset]
        offset += 1

        flags = table_data[offset]
        offset += 1

        min_size, offset = parse_leb128(table_data, offset)

        if flags & 1:
            max_size, offset = parse_leb128(table_data, offset)
        else:
            max_size = None

        print(f"  Table {i}:")
        print(f"    元素类型: 0x{elem_type:02x} (0x70=funcref)")
        print(f"    最小大小: {min_size}")
        print(f"    最大大小: {max_size}")