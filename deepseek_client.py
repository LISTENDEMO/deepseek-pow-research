#!/usr/bin/env python3
"""
DeepSeek Chat Client - Python/requests 实现
"""

import requests
import hashlib
import json
import base64
import time
from pathlib import Path

# 配置
CONFIG_FILE = Path(__file__).parent / "deepseek_login.json"

class DeepSeekClient:
    def __init__(self):
        self.base_url = "https://chat.deepseek.com"
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        self.chat_session_id = None

        self.load_config()

        if self.token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "x-app-version": "20241129.1",
                "x-client-locale": "zh_CN",
                "x-client-platform": "web",
            })

    def load_config(self):
        """加载登录配置"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.token = data.get("token")
                self.user_id = data.get("user_id")
                self.email = data.get("email")
                print(f"已加载配置: {self.email}")

    def save_config(self, data):
        """保存登录配置"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"配置已保存")

    def login(self, email: str, password: str):
        """登录 DeepSeek"""
        print("正在登录...")

        url = f"{self.base_url}/api/v0/user/login"
        data = {
            "email": email,
            "password": password
        }

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                user_data = result.get("data", {})
                self.token = user_data.get("token")
                self.user_id = user_data.get("user_id")
                self.email = email

                self.session.headers["Authorization"] = f"Bearer {self.token}"

                # 保存配置
                self.save_config({
                    "user_id": self.user_id,
                    "email": email,
                    "token": self.token,
                    "login_time": time.strftime("%Y-%m-%d %H:%M:%S")
                })

                print("登录成功!")
                return True
            else:
                print(f"登录失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"登录错误: {e}")
            return False

    def create_chat_session(self):
        """创建聊天会话"""
        print("创建聊天会话...")

        url = f"{self.base_url}/api/v0/chat/session/create"
        data = {
            "agent": "chat"
        }

        try:
            response = self.session.post(url, json=data)
            result = response.json()

            if result.get("code") == 0:
                self.chat_session_id = result.get("data", {}).get("biz_data", {}).get("id")
                print(f"会话 ID: {self.chat_session_id}")
                return self.chat_session_id
            else:
                print(f"创建会话失败: {result.get('message')}")
                return None

        except Exception as e:
            print(f"错误: {e}")
            return None

    def get_pow_challenge(self, target_path: str = "/api/v0/chat/completion"):
        """获取 PoW challenge"""
        print("获取 PoW challenge...")

        url = f"{self.base_url}/api/v0/chat/create_pow_challenge"
        data = {
            "target_path": target_path
        }

        try:
            response = self.session.post(url, json=data)
            result = response.json()

            if result.get("code") == 0:
                challenge_data = result.get("data", {}).get("biz_data", {}).get("challenge")
                print(f"Challenge: {challenge_data.get('challenge')[:30]}...")
                print(f"Salt: {challenge_data.get('salt')}")
                print(f"Difficulty: {challenge_data.get('difficulty')}")
                print(f"Expire_at: {challenge_data.get('expire_at')}")
                return challenge_data
            else:
                print(f"获取 challenge 失败: {result.get('message')}")
                return None

        except Exception as e:
            print(f"错误: {e}")
            return None

    def solve_pow(self, challenge_data: dict):
        """解决 PoW challenge"""
        print("\n开始解决 PoW...")

        challenge = challenge_data.get("challenge")
        salt = challenge_data.get("salt")
        expire_at = challenge_data.get("expire_at")
        difficulty = challenge_data.get("difficulty")
        signature = challenge_data.get("signature")

        # Prefix 格式: salt + "_" + expire_at + "_"
        prefix = f"{salt}_{expire_at}_"

        print(f"Prefix: {prefix}")
        print(f"搜索范围: 0 - {difficulty}")

        start_time = time.time()

        # 使用 SHA3-256 搜索
        answer = None
        for i in range(difficulty):
            test_str = prefix + str(i)
            hash_result = hashlib.sha3_256(test_str.encode('utf-8')).hexdigest()

            if hash_result == challenge:
                answer = i
                break

            # 每 10000 次显示进度
            if i % 10000 == 0:
                elapsed = time.time() - start_time
                print(f"  进度: {i}/{difficulty} ({i/difficulty*100:.1f}%), 耗时: {elapsed:.2f}s")

        elapsed = time.time() - start_time

        if answer:
            print(f"\n找到答案: {answer}")
            print(f"耗时: {elapsed:.2f}s")

            # 验证
            verify_str = prefix + str(answer)
            verify_hash = hashlib.sha3_256(verify_str.encode()).hexdigest()
            print(f"验证: hash('{verify_str}') = {verify_hash}")
            print(f"目标: {challenge}")
            print(f"匹配: {verify_hash == challenge}")
        else:
            print(f"\n未找到答案，耗时: {elapsed:.2f}s")

        return answer

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

        # Base64 编码
        json_str = json.dumps(pow_response, separators=(',', ':'))
        b64_encoded = base64.b64encode(json_str.encode()).decode()

        return b64_encoded

    def send_message(self, message: str):
        """发送消息"""
        print(f"\n发送消息: {message[:50]}...")

        # 1. 创建会话（如果没有）
        if not self.chat_session_id:
            self.create_chat_session()

        # 2. 获取 PoW challenge
        challenge_data = self.get_pow_challenge()
        if not challenge_data:
            print("无法获取 challenge")
            return None

        # 3. 解决 PoW
        answer = self.solve_pow(challenge_data)
        if answer is None:
            print("无法解决 PoW")
            return None

        # 4. 构建请求
        pow_response = self.build_pow_response(challenge_data, answer)

        url = f"{self.base_url}/api/v0/chat/completion"
        headers = self.session.headers.copy()
        headers["x-ds-pow-response"] = pow_response

        data = {
            "chat_session_id": self.chat_session_id,
            "parent_message_id": None,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        }

        print("\n发送请求...")

        try:
            response = self.session.post(url, json=data, headers=headers, stream=True)

            print(f"响应状态: {response.status_code}")

            if response.status_code == 200:
                # 流式响应
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8').replace("data: ", ""))
                            if chunk.get("type") == "answer":
                                content = chunk.get("content", "")
                                full_response += content
                                print(content, end="", flush=True)
                        except:
                            pass

                print("\n")
                return full_response
            else:
                print(f"请求失败: {response.status_code}")
                print(f"响应: {response.text[:500]}")
                return None

        except Exception as e:
            print(f"发送错误: {e}")
            return None

def main():
    client = DeepSeekClient()

    # 如果没有 token，需要登录
    if not client.token:
        print("请先登录")
        email = input("邮箱: ")
        password = input("密码: ")
        client.login(email, password)

    # 测试发送消息
    if client.token:
        # 先测试 PoW 算法
        print("\n" + "=" * 60)
        print("测试 PoW 算法")
        print("=" * 60)

        challenge_data = client.get_pow_challenge()
        if challenge_data:
            answer = client.solve_pow(challenge_data)

            if answer:
                print("\nPoW 算法验证成功!")

                # 尝试发送消息
                print("\n" + "=" * 60)
                print("发送测试消息")
                print("=" * 60)

                response = client.send_message("你好")
                if response:
                    print(f"\n回复: {response}")
            else:
                print("\nPoW 算法验证失败，请检查实现")

if __name__ == "__main__":
    main()