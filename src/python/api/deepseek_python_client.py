#!/usr/bin/env python3
"""
DeepSeek 客户端 - 使用 Node.js WASM 计算 PoW
由于 Python 无法直接运行 WASM（wbindgen 需要特定环境），
我们通过子进程调用 Node.js 来完成 PoW 计算
"""

import subprocess
import json
import requests
import base64
import time
from pathlib import Path

class DeepSeekPowSolver:
    """使用 Node.js WASM 解决 PoW"""

    def __init__(self, node_script_path: str = None):
        self.node_path = Path(__file__).parent / "solve_pow_wasm.js"
        if node_script_path:
            self.node_path = Path(node_script_path)

        # 检查 Node.js 是否可用
        self.node_available = self._check_node()

    def _check_node(self):
        """检查 Node.js 是否安装"""
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def solve(self, challenge_data: dict) -> int:
        """
        解决 PoW challenge
        challenge_data: 从 API 返回的 challenge 信息
        """
        if not self.node_available:
            raise RuntimeError("Node.js 未安装，无法使用 WASM PoW solver")

        # 调用 Node.js 脚本
        input_data = json.dumps(challenge_data)

        result = subprocess.run(
            ["node", str(self.node_path)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=60  # 60秒超时
        )

        if result.returncode != 0:
            raise RuntimeError(f"PoW solver error: {result.stderr}")

        output = json.loads(result.stdout)
        return output.get("answer")


class DeepSeekClient:
    """DeepSeek Chat 客户端"""

    def __init__(self):
        self.base_url = "https://chat.deepseek.com"
        self.session = requests.Session()
        self.pow_solver = DeepSeekPowSolver()

        self.token = None
        self.chat_session_id = None

        self._load_config()

    def _load_config(self):
        """加载配置"""
        config_file = Path(__file__).parent / "deepseek_login.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.token = data.get("token")

            if self.token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "x-app-version": "20241129.1",
                    "x-client-locale": "zh_CN",
                    "x-client-platform": "web",
                })

    def get_pow_challenge(self, target_path: str = "/api/v0/chat/completion"):
        """获取 PoW challenge"""
        url = f"{self.base_url}/api/v0/chat/create_pow_challenge"
        data = {"target_path": target_path}

        response = self.session.post(url, json=data)

        if response.status_code == 429:
            raise Exception("Rate limit exceeded, please wait")

        result = response.json()
        if result.get("code") == 0:
            return result["data"]["biz_data"]["challenge"]
        else:
            raise Exception(f"Failed to get challenge: {result.get('message')}")

    def solve_pow(self, challenge_data: dict):
        """使用 WASM 解决 PoW"""
        return self.pow_solver.solve(challenge_data)

    def build_pow_response(self, challenge_data: dict, answer: int):
        """构建 x-ds-pow-response header"""
        pow_response = {
            "algorithm": challenge_data.get("algorithm", "DeepSeekHashV1"),
            "challenge": challenge_data.get("challenge"),
            "salt": challenge_data.get("salt"),
            "answer": answer,
            "signature": challenge_data.get("signature"),
            "target_path": "/api/v0/chat/completion"
        }

        json_str = json.dumps(pow_response, separators=(',', ':'))
        return base64.b64encode(json_str.encode()).decode()

    def create_session(self):
        """创建聊天会话"""
        url = f"{self.base_url}/api/v0/chat/session/create"
        data = {"agent": "chat"}

        response = self.session.post(url, json=data)
        result = response.json()

        if result.get("code") == 0:
            self.chat_session_id = result["data"]["biz_data"]["id"]
            return self.chat_session_id
        else:
            raise Exception(f"Failed to create session: {result.get('message')}")

    def send_message(self, message: str):
        """发送消息"""
        # 创建会话
        if not self.chat_session_id:
            self.create_session()

        # 获取 PoW challenge
        challenge = self.get_pow_challenge()

        # 使用 WASM 解决 PoW
        answer = self.solve_pow(challenge)

        # 构建请求
        pow_response = self.build_pow_response(challenge, answer)

        url = f"{self.base_url}/api/v0/chat/completion"
        headers = self.session.headers.copy()
        headers["x-ds-pow-response"] = pow_response

        data = {
            "chat_session_id": self.chat_session_id,
            "parent_message_id": None,
            "messages": [{"role": "user", "content": message}]
        }

        response = self.session.post(url, json=data, headers=headers, stream=True)

        # 处理流式响应
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8').replace("data: ", ""))
                    if chunk.get("type") == "answer":
                        full_response += chunk.get("content", "")
                except:
                    pass

        return full_response


def main():
    print("DeepSeek Python Client")
    print("=" * 60)

    # 检查依赖
    print("\n检查依赖...")

    client = DeepSeekClient()

    if not client.pow_solver.node_available:
        print("错误: Node.js 未安装")
        print("请安装 Node.js: https://nodejs.org/")
        return

    print("Node.js 已安装")

    if not client.token:
        print("错误: 未找到登录 token")
        print("请先登录并保存 deepseek_login.json")
        return

    print(f"Token 已加载: {client.token[:20]}...")

    # 测试
    print("\n测试 PoW solver...")

    try:
        challenge = client.get_pow_challenge()
        print(f"Challenge: {challenge['challenge'][:30]}...")
        print(f"Salt: {challenge['salt']}")
        print(f"Expire_at: {challenge['expire_at']}")

        # 注意：由于 PoW 算法验证问题，这里可能无法正确计算
        print("\nPoW 算法验证仍在研究中...")

    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()