# DeepSeek GUI 使用说明

## 功能概述

DeepSeek Chat Client 提供 PyQt6 GUI 界面，支持：
- **快速模式** (default) - 快速响应
- **专家模式** (expert) - 深度思考，更详细的回答
- **思考模式** - 显示 AI 思考过程
- **联网搜索** - 实时搜索互联网信息
- **对话上下文** - 自动保持对话历史（通过 parent_message_id）
- **文件上传** - 上传附件供 AI 分析（已修复，不阻塞 UI）

## 问题修复总结

已修复以下问题：
1. ✅ API 数据结构解析 (`data.biz_data.challenge`)
2. ✅ Session 数据结构解析 (`data.biz_data.chat_session.id`)
3. ✅ Worker 线程引用保存
4. ✅ WASM solver 集成
5. ✅ Session 创建端点 (`/api/v0/chat_session/create`)
6. ✅ Completion 端点 (`/api/v0/chat/completion`)
7. ✅ Authorization header 自动设置
8. ✅ 流式响应解析 (支持 THINK/RESPONSE fragment 类型)
9. ✅ 使用 objectName 查找 content_label 避免关键字冲突
10. ✅ 对话上下文 (使用 parent_message_id 链接消息)
11. ✅ 文件上传 (支持 PDF、Word、Excel、文本、图片等)
12. ✅ 文件状态查询 (GET 请求 + query 参数)
13. ✅ UI 不阻塞 (等待解析在 Worker 线程中执行)

## 文件上传功能

支持的文件类型：
- PDF 文件 (.pdf)
- Word 文档 (.doc, .docx)
- Excel 表格 (.xls, .xlsx)
- PowerPoint (.ppt, .pptx)
- 文本文件 (.txt, .md)
- 图片 (.png, .jpg, .jpeg, .gif)

上传流程：
1. 点击 📎 按钮选择文件
2. 系统自动上传，状态显示 "上传中..."
3. 后台线程等待解析完成，状态显示 "解析中..."（不阻塞 UI）
4. 解析完成后文件显示在输入框上方
5. 点击文件名可移除附件
6. 发送消息时自动附带文件

技术细节：
- 上传 API 需要 PoW header（与聊天 API 相同）
- 文件状态查询：GET `/api/v0/file/fetch_files?file_ids=<id>`
- 状态值：PENDING → PARSING → SUCCESS
- 解析等待在 UploadFileWorker 线程中执行

注意：
- 文件需要解析完成后才能使用（约 2-10 秒）
- 单个文件最大 100MB

## 对话上下文原理

DeepSeek 通过 `parent_message_id` 维护对话上下文：
- 每条消息都有唯一的 `message_id`
- 发送新消息时，将上一条 AI 响应的 `message_id` 作为 `parent_message_id`
- API 会据此获取之前的对话历史

## API 端点

| 功能 | 端点 |
|------|------|
| PoW Challenge | `/api/v0/chat/create_pow_challenge` |
| 创建 Session | `/api/v0/chat_session/create` |
| 发送消息 | `/api/v0/chat/completion` |

## 模式说明

| 模式 | model_type | 说明 |
|------|------------|------|
| 快速 | default | 快速响应，适合日常对话 |
| 专家 | expert | 深度思考，更详细的回答 |

| 功能 | 参数 | 说明 |
|------|------|------|
| 思考 | thinking_enabled | 显示 AI 思考过程 |
| 联网 | search_enabled | 实时搜索互联网 |

## 运行方式

```bash
python deepseek_gui.py
```

## 使用流程

1. **启动后自动加载 Token** - 从 `deepseek_login.json`
2. **选择模式** - 快速/专家、思考、联网
3. **点击"新会话"** - 创建聊天 session，清空历史
4. **输入消息** - 发送聊天请求，自动保持上下文

## 当前限制

- **Rate Limit (429)** - API 可能暂时限制请求
  - 解决方案：等待 5-10 分钟后重试

## 文件列表

| 文件 | 功能 |
|------|------|
| deepseek_gui.py | PyQt6 GUI 主程序 |
| deepseek_pow_solver.js | Node.js WASM solver |
| sha3_wasm.wasm | DeepSeek WASM |
| deepseek_login.json | Token 文件 |
| test_parent_id.py | 上下文测试脚本 |

## 测试命令

```bash
# 测试完整流程
python test_api_fix.py

# 测试上下文功能
python test_parent_id.py

# 测试模式功能
python test_model_modes.py

# 测试 WASM solver
python test_gui_setup.py
```

## 错误处理

| 错误 | 解决方案 |
|------|----------|
| Rate Limit (429) | 等待 5-10 分钟 |
| Token 文件不存在 | 点击"设置"手动输入 |
| WASM solver 失败 | 确保安装 Node.js |
| Session 创建失败 | 检查 Token 是否有效 |