#!/usr/bin/env python3
"""
Parse WASM function signatures from type section
"""

from pathlib import Path
import struct

wasm_path = Path(__file__).parent / "sha3_wasm.wasm"
wasm_bytes = wasm_path.read_bytes()

# WASM value types:
# 0x7F = i32
# 0x7E = i64
# 0x7D = f32
# 0x7C = f64
# 0x7B = v128
# 0x70 = funcref
# 0x6F = externref

value_type_names = {
    0x7F: 'i32',
    0x7E: 'i64',
    0x7D: 'f32',
    0x7C: 'f64',
    0x7B: 'v128',
    0x70: 'funcref',
    0x6F: 'externref',
}

def parse_leb128(data, offset):
    """Parse unsigned LEB128"""
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

def parse_signed_leb128(data, offset):
    """Parse signed LEB128"""
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7f) << shift
        shift += 7
        if (byte & 0x80) == 0:
            if shift < 32 and (byte & 0x40):
                result |= (~0 << shift)
            break
    return result, offset

def parse_type_section(data):
    """Parse type section (section 1)"""
    offset = 0
    num_types, offset = parse_leb128(data, offset)

    types = []
    for i in range(num_types):
        form = data[offset]
        offset += 1

        if form == 0x60:  # func type
            # Parameters
            num_params, offset = parse_leb128(data, offset)
            params = []
            for _ in range(num_params):
                param_type = data[offset]
                offset += 1
                params.append(value_type_names.get(param_type, f'unknown_{param_type:02x}'))

            # Results
            num_results, offset = parse_leb128(data, offset)
            results = []
            for _ in range(num_results):
                result_type = data[offset]
                offset += 1
                results.append(value_type_names.get(result_type, f'unknown_{result_type:02x}'))

            types.append(('func', params, results))

    return types

def parse_function_section(data):
    """Parse function section (section 3) - maps functions to types"""
    offset = 0
    num_funcs, offset = parse_leb128(data, offset)

    type_indices = []
    for _ in range(num_funcs):
        type_idx, offset = parse_leb128(data, offset)
        type_indices.append(type_idx)

    return type_indices

def parse_export_section(data, type_indices, types):
    """Parse export section (section 7)"""
    offset = 0
    num_exports, offset = parse_leb128(data, offset)

    exports = []
    for _ in range(num_exports):
        # Name
        name_len, offset = parse_leb128(data, offset)
        name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        # Kind
        kind = data[offset]
        offset += 1

        # Index
        index, offset = parse_leb128(data, offset)

        kind_names = {0: 'func', 1: 'table', 2: 'memory', 3: 'global'}
        kind_name = kind_names.get(kind, f'unknown_{kind}')

        # Get signature if it's a function
        sig = None
        if kind == 0 and index < len(type_indices):
            type_idx = type_indices[index]
            if type_idx < len(types):
                sig = types[type_idx]

        exports.append((name, kind_name, index, sig))

    return exports

# Parse sections
def parse_sections(data):
    offset = 8  # Skip magic and version
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

print("Parsing WASM sections...")
sections = parse_sections(wasm_bytes)

# Parse type section
types = parse_type_section(sections['type'])
print(f"\nType section ({len(types)} function types):")
for i, t in enumerate(types):
    print(f"  Type {i}: {t}")

# Parse function section
type_indices = parse_function_section(sections['function'])
print(f"\nFunction section ({len(type_indices)} functions):")
print(f"  Type indices: {type_indices[:10]}...")

# Parse export section with signatures
exports = parse_export_section(sections['export'], type_indices, types)
print(f"\nExport section ({len(exports)} exports):")
for name, kind, index, sig in exports:
    if sig:
        params, results = sig[1], sig[2]
        print(f"  {name} ({kind}, index={index}):")
        print(f"    params: {params}")
        print(f"    returns: {results}")
    else:
        print(f"  {name} ({kind}, index={index})")