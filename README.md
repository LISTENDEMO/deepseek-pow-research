# DeepSeek PoW 算法逆向工程研究

## 项目概述

本项目是对 DeepSeek Chat API 的 Proof of Work (PoW) 算法的逆向工程研究。通过分析 WASM 二进制文件、破解 Keccak hash 算法、实现 PoW solver，展示了逆向分析、算法破解和多语言协作能力。

## 系统架构

### 逆向工程流程

```mermaid
graph TB
    A[DeepSeek Chat Website] --> B[捕获 WASM 文件<br/>sha3_wasm.wasm]
    
    B --> C[WASM 二进制分析]
    C --> D[函数签名识别<br/>wasm_solve, wasm_deepseek_hash_v1]
    C --> E[内存布局分析<br/>offset 0: status, offset 8: answer]
    C --> F[数据流追踪<br/>challenge → hash → answer]
    
    D --> G[算法逆向]
    E --> G
    F --> G
    
    G --> H[Keccak Hash 算法破解]
    H --> I[PoW Challenge 解决]
    I --> J[Python/Node.js 实现]
    
    J --> K[PyQt6 GUI 开发]
    K --> L[完整 PoW Solver]
    
    L --> M[API Client 封装]
    M --> N[DeepSeek API 调用]
    
    N --> O[聊天功能实现<br/>流式响应 + 思考模式]
    
    style A fill:#FF6B6B,color:#fff
    style C fill:#FFA500,color:#fff
    style H fill:#50C878,color:#fff
    style K fill:#4A90E2,color:#fff
    style N fill:#00CED1,color:#fff
```

### WASM 逆向分析架构

```mermaid
graph LR
    A[WASM 文件<br/>sha3_wasm.wasm] --> B[二进制解析]
    
    B --> C[函数表提取]
    B --> D[全局变量分析]
    B --> E[内存段识别]
    
    C --> F[函数签名<br/>wasm_solve<br/>wasm_deepseek_hash_v1]
    D --> G[全局变量<br/>memory buffer<br/>hash state]
    E --> H[内存布局<br/>offset 0: int32<br/>offset 8: float64]
    
    F --> I[参数推断<br/>challenge<br/>salt<br/>expire_at<br/>difficulty]
    G --> I
    H --> I
    
    I --> J[调用约定分析<br/>i32, i32, i32, i32, i32, f64]
    
    J --> K[算法逻辑推断<br/>Keccak sponge<br/>PoW iteration]
    
    K --> L[Python/JS 实现<br/>算法复现]
    
    style A fill:#FFD700,color:#fff
    style B fill:#FFA500,color:#fff
    style J fill:#50C878,color:#fff
    style L fill:#4A90E2,color:#fff
```

### PoW 算法破解流程

```mermaid
graph TB
    A[DeepSeek API<br/>返回 Challenge] --> B[解析 Challenge 数据]
    
    B --> C[Challenge 参数]
    C --> D[challenge: hex string]
    C --> E[salt: random string]
    C --> F[expire_at: timestamp]
    C --> G[difficulty: integer]
    
    D --> H[PoW Solver]
    E --> H
    F --> H
    G --> H
    
    H --> I[Keccak Hash 计算]
    I --> J[迭代尝试<br/>0 → difficulty]
    
    J --> K[计算 hash<br/>challenge + answer]
    K --> L[验证 hash < difficulty]
    
    L --> M{满足条件?}
    M -->|是| N[返回 answer]
    M -->|否| O[继续迭代]
    O --> J
    
    N --> P[构造 API 请求<br/>challenge + answer]
    P --> Q[发送到 DeepSeek API]
    Q --> R[获得响应<br/>聊天内容]
    
    style A fill:#FF6B6B,color:#fff
    style H fill:#FFA500,color:#fff
    style I fill:#50C878,color:#fff
    style N fill:#4A90E2,color:#fff
```

### Keccak Hash 算法实现

```mermaid
graph TB
    A[Keccak-256 Hash] --> B[Sponge Construction]
    
    B --> C[Absorb Phase<br/>吸收输入数据]
    C --> D[Padding<br/>补位到 block size]
    D --> E[Block Processing<br/>处理 1088-bit blocks]
    
    E --> F[Permutation<br/>Keccak-f&#91;1600&#93;]
    F --> G[24 Rounds<br/>θ, ρ, π, χ, ι]
    
    G --> H[Squeeze Phase<br/>挤压输出]
    H --> I[Output 256-bit Hash<br/>32 bytes]
    
    I --> J[Hash Comparison<br/>hash < difficulty]
    
    J --> K{满足 PoW?}
    K -->|是| L[Success]
    K -->|否| M[Increment answer]
    M --> N[Rehash]
    N --> F
    
    style A fill:#FFD700,color:#fff
    style F fill:#FFA500,color:#fff
    style I fill:#50C878,color:#fff
    style L fill:#4A90E2,color:#fff
```

### PyQt6 GUI 架构

```mermaid
graph TB
    A[PyQt6 GUI<br/>deepseek_gui.py] --> B[Token 管理]
    
    B --> C[Token 输入框]
    B --> D[Token 加载/保存]
    B --> E[Token 验证]
    
    A --> F[会话管理]
    F --> G[新建会话]
    F --> H[会话列表]
    F --> I[会话切换]
    
    A --> J[聊天界面]
    J --> K[用户消息输入]
    J --> L[助手消息显示]
    J --> M[思考模式切换]
    
    A --> N[PoW Solver<br/>Node.js WASM]
    N --> O[Challenge 接收]
    N --> P[自动求解]
    N --> Q[Answer 返回]
    
    A --> R[流式响应处理]
    R --> S[实时显示]
    R --> T[Markdown 渲染]
    R --> U[代码块高亮]
    
    style A fill:#61DAFB,color:#fff
    style N fill:#FFA500,color:#fff
    style R fill:#50C878,color:#fff
```

### 多语言协作架构

```mermaid
graph LR
    A[Python<br/>主程序 + GUI] --> B[PyQt6<br/>用户界面]
    
    A --> C[Python Client<br/>API 封装]
    C --> D[requests<br/>HTTP 调用]
    
    A --> E[Node.js<br/>WASM Solver]
    E --> F[WASM Binary<br/>sha3_wasm.wasm]
    
    F --> G[Keccak Hash<br/>算法实现]
    G --> H[PoW Solver<br/>challenge 解决]
    
    H --> I[answer<br/>返回 Python]
    I --> C
    
    C --> J[DeepSeek API<br/>聊天请求]
    J --> K[响应内容<br/>返回 GUI]
    
    style A fill:#4A90E2,color:#fff
    style E fill:#FFA500,color:#fff
    style F fill:#FFD700,color:#fff
    style J fill:#50C878,color:#fff
```

### 核心技术栈

```mermaid
graph TB
    A[技术栈] --> B[逆向工程工具]
    
    B --> C[WASM 分析<br/>wasm2wat, wasm-objdump]
    B --> D[二进制分析<br/>Python struct, hexdump]
    B --> E[调试工具<br/>Node.js WASM runtime]
    
    A --> F[算法实现]
    F --> G[Keccak Hash<br/>Python, JavaScript, WASM]
    F --> H[PoW Solver<br/>Node.js + WASM]
    F --> I[API Client<br/>Python requests]
    
    A --> J[前端界面]
    J --> K[PyQt6<br/>桌面应用]
    J --> L[流式渲染<br/>Markdown + 代码高亮]
    
    A --> M[测试验证]
    M --> N[Unit Tests<br/>pytest, unittest]
    M --> O[Integration Tests<br/>API + PoW]
    M --> P[验证脚本<br/>verify_pow.py]
    
    style A fill:#00CED1,color:#fff
    style B fill:#FFA500,color:#fff
    style F fill:#50C878,color:#fff
    style J fill:#4A90E2,color:#fff
```

### WASM 函数调用流程

```mermaid
sequenceDiagram
    participant Python as Python Client
    participant Node as Node.js Runtime
    participant WASM as WASM Module
    participant API as DeepSeek API
    
    Python->>API: 发送聊天请求
    API->>Python: 返回 challenge
    
    Python->>Node: 调用 PoW Solver<br/>challenge + salt + difficulty
    Node->>WASM: 加载 sha3_wasm.wasm
    
    loop 迭代求解
        Node->>WASM: wasm_solve<br/>challenge, answer
        WASM->>WASM: Keccak hash<br/>challenge + answer
        WASM->>Node: 返回 hash 结果
        Node->>Node: 检查 hash < difficulty
    end
    
    Node->>Python: 返回 answer
    Python->>API: 发送 answer
    API->>Python: 返回聊天响应
    
    Python->>Python: 流式渲染<br/>Markdown + 代码高亮
```

### PoW Challenge 数据结构

```mermaid
graph LR
    A[Challenge JSON] --> B[challenge<br/>hex string<br/>32 bytes]
    
    A --> C[salt<br/>random string<br/>20 bytes]
    A --> D[expire_at<br/>timestamp<br/>unix time]
    A --> E[difficulty<br/>integer<br/>144000]
    
    B --> F[Keccak Input<br/>challenge + answer]
    C --> F
    
    F --> G[Hash Calculation]
    G --> H[256-bit Output]
    
    H --> I[Comparison<br/>hash < difficulty]
    
    I --> J{满足条件?}
    J -->|是| K[返回 answer]
    J -->|否| L[迭代 +1]
    
    style A fill:#FFD700,color:#fff
    style F fill:#FFA500,color:#fff
    style I fill:#50C878,color:#fff
```

### WASM 内存布局

```mermaid
graph TB
    A[WASM Memory Layout] --> B[offset 0<br/>int32<br/>status code]
    
    A --> C[offset 8<br/>float64<br/>answer]
    A --> D[offset 16<br/>bytes<br/>hash output]
    
    B --> E[status: 0<br/>成功]
    B --> F[status: 1<br/>失败]
    
    C --> G[answer<br/>PoW 解<br/>0 - difficulty]
    
    D --> H[hash<br/>Keccak-256<br/>32 bytes]
    
    style A fill:#FFD700,color:#fff
    style B fill:#FFA500,color:#fff
    style C fill:#50C878,color:#fff
    style D fill:#4A90E2,color:#fff
```

### 测试验证体系

```mermaid
graph TB
    A[测试验证] --> B[WASM 测试]
    
    B --> C[函数调用测试<br/>wasm_test.js]
    B --> D[Hash 输出测试<br/>wasm_hash_test.js]
    B --> E[内存布局测试<br/>wasm_export_memory.js]
    
    A --> F[Keccak 测试]
    F --> G[基础测试<br/>test_sha3_basic.py]
    F --> H[变体测试<br/>test_hash_variants.js]
    F --> I[正确性验证<br/>test_keccak_direct.js]
    
    A --> J[PoW 测试]
    J --> K[已知 PoW<br/>test_known_pow.py]
    J --> L[实时 PoW<br/>test_live_pow.py]
    J --> M[完整流程<br/>test_full_flow.py]
    
    A --> N[API 测试]
    N --> O[请求测试<br/>test_api.py]
    N --> P[响应测试<br/>test_raw_response.py]
    N --> Q[流式测试<br/>test_stream_parse.py]
    
    style A fill:#00CED1,color:#fff
    style B fill:#FFA500,color:#fff
    style F fill:#50C878,color:#fff
    style J fill:#4A90E2,color:#fff
```

## 核心模块说明

### 🔍 WASM 逆向分析模块

**文件**：
- `analyze_wasm.py` - WASM 二进制分析
- `analyze_wasm_binary.py` - 函数签名识别
- `analyze_wasm_funcs.py` - 函数表提取
- `analyze_wasm_globals.py` - 全局变量分析

**能力**：
- ✅ WASM 二进制解析
- ✅ 函数签名推断
- ✅ 内存布局分析
- ✅ 数据流追踪

### 🔐 Keccak Hash 实现

**文件**：
- `keccak_sponge.py` - Sponge 构造实现
- `deepseek_keccak.py` - Keccak-256 实现
- `exact_js_keccak.js` - JavaScript 版本

**能力**：
- ✅ Keccak-256 hash 计算
- ✅ Sponge construction
- ✅ 24 rounds permutation
- ✅ FIPS-202 标准

### ⚡ PoW Solver

**文件**：
- `deepseek_pow_solver.js` - Node.js WASM solver
- `solve_pow_wasm.js` - WASM 调用封装
- `wasm_solver.py` - Python WASM 调用

**能力**：
- ✅ Challenge 解析
- ✅ Keccak hash 计算
- ✅ 迭代求解
- ✅ 验证 hash < difficulty

### 🖥️ PyQt6 GUI

**文件**：
- `deepseek_gui.py` - 主界面

**功能**：
- ✅ Token 管理（输入/加载/保存）
- ✅ 会话管理（新建/切换/列表）
- ✅ 聊天界面（用户/助手消息）
- ✅ 思考模式切换
- ✅ 流式响应显示
- ✅ Markdown 渲染

### 📡 API Client

**文件**：
- `deepseek_api.py` - Python API client
- `deepseek_python_client_v2.py` - 增强版本

**能力**：
- ✅ 聊天请求封装
- ✅ PoW challenge 处理
- ✅ 流式响应解析
- ✅ 文件上传支持

## 技术亮点

### 1. 逆向工程能力
- **WASM 二进制分析**：解析 WASM 文件，提取函数签名和内存布局
- **算法推断**：通过输入输出分析推断算法逻辑
- **内存布局破解**：识别 WASM 内存段和数据结构

### 2. 算法实现能力
- **Keccak-256**：实现 SHA-3 标准 hash 算法
- **PoW Solver**：破解 Proof of Work challenge
- **多语言协作**：Python + Node.js + WASM

### 3. 应用开发能力
- **PyQt6 GUI**：完整的桌面应用界面
- **API Client**：封装 DeepSeek API 调用
- **流式渲染**：实时显示响应内容

## 验证结果

```
WASM Solver 测试:
  Challenge: af70a1634457...
  Salt: 811e05c93d1b71993710
  Expected answer: 69992

  Success: True ✓
  Answer: 69992 ✓
  Match: True ✓
```

## 使用方法

### 1. 运行 GUI

```bash
python deepseek_gui.py
```

### 2. 测试 WASM solver

```bash
python test_gui_setup.py
```

或直接调用 Node.js:

```bash
echo '{"challenge":"xxx","salt":"xxx","expire_at":xxx,"difficulty":144000}' | node deepseek_pow_solver.js
```

## 技术架构

```
用户 → PyQt6 GUI → Python API Client → Node.js WASM Solver → DeepSeek API
                                                    ↓
                                              PoW 解决
                                                    ↓
                                              返回答案
```

## 文件结构

```
DeepSeek/
├── src/                          # 源码目录
│   ├── python/                   # Python 模块
│   │   ├── wasm/                 # WASM 分析工具 (10 files)
│   │   │   ├── analyze_wasm*.py  # WASM 二进制分析
│   │   │   ├── parse_wasm*.py    # WASM 类型解析
│   │   │   └── wasm_*.py         # WASM Python 调用
│   │   ├── hash/                 # Keccak Hash 实现 (5 files)
│   │   │   ├── deepseek_keccak*.py  # 多版本实现
│   │   │   └── keccak_sponge.py     # Sponge 构造
│   │   ├── api/                  # API Client (10 files)
│   │   │   ├── deepseek_api.py      # API 封装
│   │   │   ├── deepseek_client*.py  # 多版本客户端
│   │   │   ├── deepseek_chat*.py    # 聊天功能
│   │   │   └ deepseek_proxy.py      # 代理支持
│   │   │   └ debug_api.py           # API 调试工具
│   │   └── gui/                  # GUI 界面 (1 file)
│   │       └ deepseek_gui.py        # PyQt6 主界面
│   │
│   ├── javascript/               # JavaScript 模块
│   │   ├── wasm/                 # WASM 相关 (13 files)
│   │   │   ├── wasm_*.js         # WASM 测试和分析
│   │   │   ├── analyze_*.js      # Hash 函数分析
│   │   │   ├── deepseek_worker*.js  # Web Worker
│   │   │   └ deepseek_main.js       # 主入口
│   │   ├── keccak/               # Keccak 实现 (10 files)
│   │   │   ├── exact_js_keccak.js   # 精确实现
│   │   │   ├── test_*keccak*.js     # 多版本测试
│   │   │   └ verify_js_sha3.js      # SHA-3 验证
│   │   └── solver/               # PoW Solver (7 files)
│   │       ├── deepseek_pow_solver.js  # 主 Solver
│   │       ├── pow_solver*.js          # 多版本实现
│   │       └ solve_pow*.js             # 求解脚本
│   │
│   └ wasm/                       # WASM 二进制 (reserved)
│
├── tests/                        # 测试目录
│   ├── python/                   # Python 测试 (25 files)
│   │   ├── test_api*.py          # API 测试
│   │   ├── test_pow*.py          # PoW 测试
│   │   ├── test_keccak*.py       # Hash 测试
│   │   ├── test_full*.py         # 完整流程测试
│   │   └ verify_pow*.py          # PoW 验证脚本
│   └ javascript/                 # JavaScript 测试 (reserved)
│
├── examples/                     # 示例代码 (reserved)
│
├── deepseek_sdk/                 # SDK 目录
│   ├── config.json.example       # 配置示例
│   └ sha3_wasm.wasm              # DeepSeek WASM
│
├── sha3_wasm.wasm                # WASM 二进制 (根目录副本)
├── README.md                     # 项目文档
├── USAGE.md                      # 使用说明
└ CLAUDE.md                       # Claude Code 配置
└ .gitignore                      # Git 忽略规则
└ package.json                   # Node.js 依赖
```

**模块分类说明**：
- **WASM 分析工具** (src/python/wasm) - WASM 二进制解析、函数签名推断、内存布局分析
- **Keccak Hash 实现** (src/python/hash, src/javascript/keccak) - SHA-3 标准 hash 算法实现
- **PoW Solver** (src/javascript/solver) - Proof of Work challenge 求解器
- **API Client** (src/python/api) - DeepSeek API 封装和聊天功能
- **GUI 界面** (src/python/gui) - PyQt6 桌面应用界面
- **测试体系** (tests/python) - 完整的测试验证脚本

## 注意事项

1. **需要 Node.js**: WASM solver 通过 Node.js 运行
2. **需要有效 Token**: 从 `deepseek_sdk/config.json.example` 复制配置
3. **Rate Limit**: API 可能返回 429，需要等待几分钟
4. **首次使用**: 点击"新建会话"创建聊天 session
5. **不包含登录凭证**: 已删除敏感文件，需要自行配置 Token

## WASM 函数签名

| 函数 | 签名 | 说明 |
|------|------|------|
| wasm_solve | `(i32, i32, i32, i32, i32, f64) -> ()` | 解决 PoW |
| wasm_deepseek_hash_v1 | `(i32, i32, i32) -> ()` | 计算 hash |

输出布局:
- offset 0: int32 (状态码)
- offset 8: float64 (答案)

## 学习价值

本项目展示了：
1. ✅ **逆向工程能力** - WASM 二进制分析和算法破解
2. ✅ **算法实现能力** - Keccak hash 和 PoW solver
3. ✅ **多语言协作** - Python + Node.js + WASM
4. ✅ **应用开发能力** - PyQt6 GUI 和 API client
5. ✅ **测试验证能力** - 完整的测试体系

适合面试展示逆向分析、算法破解和多语言协作能力。

## License

MIT - 仅供学习和研究使用