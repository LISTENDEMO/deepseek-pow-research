# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepSeek Chat Client - PyQt6 GUI application for DeepSeek AI chat service with:
- Pure Python/requests API integration (no browser automation)
- WASM PoW solver via Node.js subprocess
- Conversation context support via `parent_message_id`
- Multiple chat modes (quick/expert, thinking, web search)
- File upload with background parsing (non-blocking UI)
- Markdown rendering for responses

## Primary Files

| File | Purpose |
|------|---------|
| `deepseek_gui.py` | Main PyQt6 GUI application (single file, contains all classes) |
| `deepseek_pow_solver.js` | Node.js WASM PoW solver |
| `sha3_wasm.wasm` | DeepSeek WASM binary |
| `deepseek_login.json` | Token storage (auto-loaded on startup) |

## Commands

### Run GUI
```bash
python deepseek_gui.py
```

### Test Commands
```bash
# Test PoW Solver
python test_gui_setup.py

# Test Full API Flow
python test_api_fix.py

# Test Context (parent_message_id)
python test_parent_id.py

# Test File Upload
python test_upload.py

# Test Model Modes
python test_model_modes.py

# Test Search Parsing
python test_search_parse.py

# Test Markdown Rendering
python test_markdown.py
```

### Direct WASM Solver Call
```bash
echo '{"challenge":"...","salt":"...","expire_at":...,"difficulty":144000}' | node deepseek_pow_solver.js
```

## Architecture

### Main Components (all in `deepseek_gui.py`)

**DeepSeekAPI class** - HTTP client for DeepSeek API:
- Token management with auto-authorization header
- Session creation via `/api/v0/chat_session/create`
- PoW challenge acquisition and solving
- Message streaming with `parent_message_id` for context linking
- File upload with status polling

**Worker Threads** - Background operations to avoid UI blocking:
- `SendMessageWorker`: Streams chat responses, parses SSE fragments
- `InitSessionWorker`: Creates new chat session
- `UploadFileWorker`: Uploads file + waits for parsing completion

**MessageWidget** - Single message display with Markdown rendering via QTextBrowser

**DeepSeekChatWindow** - Main window with modern dark theme UI

### Streaming Response Parsing

DeepSeek uses SSE streaming with fragment-based structure:
```
{"v":{"response":{"fragments":[{"type":"THINK/RESPONSE/SEARCH"...}]}}}
```

Fragment types:
- `THINK`: AI reasoning process (stored but not displayed)
- `RESPONSE`: Final answer text (displayed)
- `SEARCH`: Web search results (intermediate, ignored)

BATCH operations may append new fragments:
```
{"p":"response","o":"BATCH","v":[{"p":"fragments","o":"APPEND","v":[...]}]}
```

### Conversation Context

Uses `parent_message_id` to link messages:
- Each AI response has `message_id` (e.g., 2, 4, 6...)
- Next user message passes `parent_message_id` = previous response's `message_id`
- API retrieves conversation history based on this chain

### File Upload Flow

1. Upload file with PoW header → returns `file_id` and status `PENDING`
2. Poll file status via GET `/api/v0/file/fetch_files?file_ids=<id>`
3. Wait for status = `SUCCESS` (done in UploadFileWorker thread)
4. Include `ref_file_ids` in chat completion request

### PoW Algorithm
```
algorithm: DeepSeekHashV1
prefix = salt + "_" + expire_at + "_"
answer = search(0 to difficulty)
hash = sha3_256(prefix + String(answer))
validation: hash === challenge
```

WASM solver output layout:
- offset 0: int32 (status code)
- offset 8: float64 (answer)

## API Endpoints

```
Base URL: https://chat.deepseek.com

POST /api/v0/chat/create_pow_challenge  - Get PoW challenge
POST /api/v0/chat_session/create        - Create session (empty body)
POST /api/v0/chat/completion            - Send message (requires PoW header)
POST /api/v0/file/upload_file           - Upload file (requires PoW header)
GET  /api/v0/file/fetch_files?file_ids=<id> - Query file status (use query param)
```

## Required Headers

```
Authorization: Bearer <token>
Content-Type: application/json
x-app-version: 20241129.1
x-client-locale: zh_CN
x-client-platform: web
x-client-timezone-offset: 28800
x-client-version: 1.8.0
x-ds-pow-response: <base64-encoded JSON>
```

## Message Request Body

```json
{
  "chat_session_id": "<session_id>",
  "parent_message_id": <previous_response_message_id>,
  "model_type": "default|expert",
  "prompt": "<message>",
  "messages": [{"role": "user", "content": "..."}],
  "ref_file_ids": ["file-xxx"],  // optional: uploaded file IDs
  "thinking_enabled": true|false,
  "search_enabled": true|false
}
```

## Known Issues

1. **Rate Limiting (429)**: API returns 429 after too many requests. Wait 5+ minutes.

2. **WASM wbindgen**: Python WASM runtimes cannot initialize wbindgen. Must use Node.js.

3. **Search Response Format**: Web search uses SEARCH fragment first, then BATCH to append RESPONSE.

4. **File Status Query**: Must use GET request with `file_ids` query parameter, not POST with JSON body.

## Dependencies

- Python: PyQt6, requests
- Node.js: Required for WASM PoW solver

## Using with Claude Code

可以通过代理服务器让 Claude Code 直接调用 DeepSeek：

### 1. 启动代理服务器

```bash
python deepseek_proxy.py --port 8080
```

### 2. 配置 Claude Code settings.json

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8080",
    "ANTHROPIC_AUTH_TOKEN": "<deepseek_token>"
  }
}
```

### 代理服务器端点

- `POST /v1/messages` - Anthropic API 格式
- `POST /v1/chat/completions` - OpenAI API 格式
- `GET /v1/models` - 获取模型列表
- `GET /health` - 健康检查

### 注意事项

- 代理需要 PoW solver (`deepseek_pow_solver.js`)
- Token 会从 `deepseek_login.json` 自动加载
- 支持流式和非流式响应