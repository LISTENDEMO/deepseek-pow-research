#!/usr/bin/env python3
"""
Analyze WASM structure and imports
"""

import json
from pathlib import Path

wasm_path = Path(__file__).parent / "sha3_wasm.wasm"
wasm_bytes = wasm_path.read_bytes()

# Parse WASM binary format manually
# WASM format: magic number (0x00 0x61 0x73 0x6D) + version + sections

print("WASM Analysis")
print("=" * 60)
print(f"File size: {len(wasm_bytes)} bytes")
print(f"Magic: {wasm_bytes[:4].hex()} (should be 0061736d)")
print(f"Version: {wasm_bytes[4:8].hex()} (should be 01000000)")

# Section IDs:
# 0: custom
# 1: type
# 2: import
# 3: function
# 4: table
# 5: memory
# 6: global
# 7: export
# 8: start
# 9: element
# 10: code
# 11: data

def parse_sections(data):
    offset = 8  # Skip magic and version
    sections = {}

    while offset < len(data):
        section_id = data[offset]
        offset += 1

        # LEB128 size
        size = 0
        shift = 0
        while True:
            byte = data[offset]
            offset += 1
            size |= (byte & 0x7f) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7

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

print(f"\nSections found:")
for name, data in sections.items():
    print(f"  {name}: {len(data)} bytes")

# Parse imports (section 2)
if 'import' in sections:
    print("\nImport section analysis:")
    import_data = sections['import']
    idx = 0

    # Number of imports
    num_imports = import_data[idx]
    idx += 1
    print(f"  Number of imports: {num_imports}")

    for i in range(min(num_imports, 10)):
        if idx >= len(import_data):
            break

        # Module name length
        mod_len = import_data[idx]
        idx += 1

        # Module name
        mod_name = import_data[idx:idx + mod_len].decode('utf-8', errors='replace')
        idx += mod_len

        # Field name length
        field_len = import_data[idx]
        idx += 1

        # Field name
        field_name = import_data[idx:idx + field_len].decode('utf-8', errors='replace')
        idx += field_len

        # Import kind
        kind = import_data[idx]
        idx += 1

        kind_names = {0: 'func', 1: 'table', 2: 'memory', 3: 'global'}
        kind_name = kind_names.get(kind, f'unknown_{kind}')

        print(f"    Import {i}: {mod_name}.{field_name} ({kind_name})")

        if kind == 0:  # func
            # Type index (LEB128)
            type_idx = import_data[idx]
            idx += 1
            print(f"      Type index: {type_idx}")
        elif kind == 2:  # memory
            # Memory limits
            flags = import_data[idx]
            idx += 1
            min_pages = import_data[idx]
            idx += 1
            print(f"      Memory: min={min_pages} pages")

# Parse exports (section 7)
if 'export' in sections:
    print("\nExport section analysis:")
    export_data = sections['export']
    idx = 0

    # Number of exports
    num_exports = export_data[idx]
    idx += 1
    print(f"  Number of exports: {num_exports}")

    exports = []
    for i in range(num_exports):
        if idx >= len(export_data):
            break

        # Name length
        name_len = export_data[idx]
        idx += 1

        # Name
        name = export_data[idx:idx + name_len].decode('utf-8', errors='replace')
        idx += name_len

        # Export kind
        kind = export_data[idx]
        idx += 1

        # Index
        index = export_data[idx]
        idx += 1

        kind_names = {0: 'func', 1: 'table', 2: 'memory', 3: 'global'}
        kind_name = kind_names.get(kind, f'unknown_{kind}')

        exports.append((name, kind_name, index))
        print(f"    Export {i}: {name} ({kind_name}, index={index})")

# Try to load with pywasm
print("\n\nAttempting to load with pywasm...")
try:
    import pywasm

    # Need to provide imports
    def log_i32(i):
        print(f"  [WASM log] i32: {i}")

    imports = {
        'env': {
            'log_i32': log_i32,
        },
        'wbindgen': {
            # Placeholder functions
        }
    }

    runtime = pywasm.load(str(wasm_path), imports)
    print(f"Loaded successfully!")
    print(f"Exports: {list(runtime.exports.keys())}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()