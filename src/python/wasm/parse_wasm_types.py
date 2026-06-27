#!/usr/bin/env python3
"""
分析 WASM Type section 获取函数签名
"""

import struct

def read_leb128(data, pos):
    """读取 LEB128 无符号整数"""
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if byte & 0x80 == 0:
            break
        shift += 7
    return result, pos

def leb128_len(data, pos):
    """计算 LEB128 编码的长度"""
    length = 0
    while True:
        byte = data[pos + length]
        length += 1
        if byte & 0x80 == 0:
            break
    return length

def parse_wasm_types(filepath):
    """解析 WASM Type section"""
    with open(filepath, 'rb') as f:
        data = f.read()

    # 找到 sections
    pos = 8  # skip magic and version
    sections = {}

    while pos < len(data):
        section_id = data[pos]
        pos += 1

        size, new_pos = read_leb128(data, pos)
        pos = new_pos

        section_data = data[pos:pos+size]
        pos += size

        sections[section_id] = section_data

    # 解析 Type section (section_id = 1)
    print("=== Type Section (函数类型) ===")
    type_data = sections[1]

    num_types, p = read_leb128(type_data, 0)
    print(f"类型数量: {num_types}")

    types = []
    for i in range(num_types):
        # 类型标记 (应该是 0x60 = function)
        kind = type_data[p]
        p += 1

        if kind != 0x60:
            print(f"  类型 {i}: 不是 function (kind={kind:02x})")
            continue

        # 参数数量
        num_params, p = read_leb128(type_data, p)
        params = []
        for j in range(num_params):
            param_type = type_data[p]
            p += 1
            params.append(param_type)

        # 返回值数量
        num_returns, p = read_leb128(type_data, p)
        returns = []
        for j in range(num_returns):
            return_type = type_data[p]
            p += 1
            returns.append(return_type)

        types.append((params, returns))

        # 解码类型
        type_names = {
            0x7f: 'i32',
            0x7e: 'i64',
            0x7d: 'f32',
            0x7c: 'f64',
            0x7b: 'v128',
        }
        param_str = ', '.join([type_names.get(t, f'?{t:02x}') for t in params])
        return_str = ', '.join([type_names.get(t, f'?{t:02x}') for t in returns])

        print(f"  类型 {i} ({kind:02x}): ({param_str}) -> ({return_str})")

    # 解析 Function section (section_id = 3) - 获取函数索引对应的类型
    print("\n=== Function Section (函数索引 -> 类型) ===")
    func_data = sections[3]

    num_funcs, p = read_leb128(func_data, 0)
    print(f"函数数量: {num_funcs}")

    func_types = []
    for i in range(num_funcs):
        type_idx, p = read_leb128(func_data, p)
        func_types.append(type_idx)

    # 解析 Export section (section_id = 7)
    print("\n=== Export Section (导出函数) ===")
    export_data = sections[7]

    num_exports, p = read_leb128(export_data, 0)
    print(f"导出数量: {num_exports}")

    exports = []
    for i in range(num_exports):
        name_len, p = read_leb128(export_data, p)
        name = export_data[p:p+name_len].decode('utf-8')
        p += name_len

        kind = export_data[p]
        p += 1

        index, p = read_leb128(export_data, p)

        exports.append((name, kind, index))

        if kind == 0:  # function export
            func_type_idx = func_types[index]
            params, returns = types[func_type_idx]
            type_names = {
                0x7f: 'i32',
                0x7e: 'i64',
                0x7d: 'f32',
                0x7c: 'f64',
            }
            param_str = ', '.join([type_names.get(t, f'?{t:02x}') for t in params])
            return_str = ', '.join([type_names.get(t, f'?{t:02x}') for t in returns])
            print(f"  {name}: func[{index}] = type[{func_type_idx}] ({param_str}) -> ({return_str})")
        else:
            print(f"  {name}: kind={kind} index={index}")

    return types, func_types, exports

if __name__ == '__main__':
    types, func_types, exports = parse_wasm_types('sha3_wasm.wasm')