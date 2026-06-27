# DeepSeek SDK

独立 Python SDK，用于调用 DeepSeek 聊天 API。

## 文件结构

```
deepseek_sdk/
├── __init__.py      # 包入口
├── api.py           # 核心 API 客户端
├── pow_solver.js    # PoW solver (Node.js)
├── sha3_wasm.wasm   # WASM 二进制
├── config.json      # 配置文件 (token + base_url)
└── README.md        # 使用说明
```

## 安装依赖

```bash
pip install requests
# Node.js 用于 PoW solver
```

## 快速使用

### 方式 1: 配置文件

创建 `config.json`:
```json
{
  "token": "Bearer xxx...",
  "base_url": "https://chat.deepseek.com"
}
```

```python
from deepseek_sdk import DeepSeekAPI

api = DeepSeekAPI()  # 自动加载 config.json
api.create_session()

result = api.chat("你好")
print(result['content'])
```

### 方式 2: 直接配置

```python
from deepseek_sdk import DeepSeekAPI

api = DeepSeekAPI(
    token="Bearer xxx...",
    base_url="https://chat.deepseek.com"
)
```

### 方式 3: 便捷函数

```python
from deepseek_sdk import create_client

api = create_client(token="Bearer xxx...")
```

## API 方法

### 聊天

```python
# 流式响应
for chunk in api.chat_stream("你好"):
    print(chunk, end="", flush=True)

# 完整响应
result = api.chat("你好")
print(result['content'])  # 响应内容
print(result['message_id'])  # 消息 ID
```

### 模式选择

```python
# 快速模式 (默认)
api.chat("你好", model_type="default")

# 专家模式 (深度思考)
api.chat("你好", model_type="expert")

# 思考模式 (显示推理过程)
api.chat("你好", thinking=True)

# 联网搜索
api.chat("今天天气", search_enabled=True)
```

### 文件上传

```python
# 上传文件
file_info = api.upload_file("document.pdf")
print(file_info['file_id'])

# 带文件聊天
result = api.chat("分析这个文件", file_ids=[file_info['file_id']])
```

### 对话管理

```python
# 清空历史
api.clear_history()

# 创建新 session
api.create_session()

# 保存配置
api.save_config("config.json")
```

## 获取 Token

Token 来自 DeepSeek 网站登录：
1. 登录 https://chat.deepseek.com
2. 从浏览器开发者工具获取 Authorization header 中的 Bearer token
3. 或使用第三方工具获取

## 注意事项

- PoW solver 需要 Node.js 环境
- Token 有效期有限，需要定期更新
- Rate Limit (429) 时需等待几分钟
- 文件上传后需等待解析完成

## 在其他项目使用

复制整个 `deepseek_sdk` 文件夹到你的项目：

```python
from deepseek_sdk import DeepSeekAPI

api = DeepSeekAPI(config_file="path/to/config.json")
result = api.chat("Hello")
```

或作为子模块：

```python
import sys
sys.path.append("path/to/deepseek_sdk")
from api import DeepSeekAPI
```