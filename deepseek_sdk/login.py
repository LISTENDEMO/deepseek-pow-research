#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Auto Login Module

自动登录 DeepSeek 并获取 Token

使用:
    from deepseek_sdk.login import DeepSeekLogin

    login = DeepSeekLogin()
    token = login.login(email, password)
"""

import os
import json
import uuid
import time
import requests
from typing import Optional, Dict


class DeepSeekLogin:
    """DeepSeek 自动登录"""

    def __init__(self, config_dir: Optional[str] = None):
        self.base_url = "https://chat.deepseek.com"
        self.config_dir = config_dir or os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.config_dir, "config.json")

        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "x-client-platform": "web",
            "x-client-version": "1.8.0",
        }

    def login(self, email: str, password: str) -> Dict:
        """
        使用邮箱密码登录 DeepSeek

        Args:
            email: 邮箱地址
            password: 密码

        Returns:
            {'success': bool, 'token': str, 'user_id': str, 'error': str}
        """
        data = {
            "email": email,
            "password": password,
            "device_id": str(uuid.uuid4()),
            "os": "windows",
            "locale": "zh_CN",
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/v0/users/login",
                headers=self.headers,
                json=data,
                timeout=15
            )

            result = resp.json()

            if result.get("code") == 0:
                user_data = result.get("data", {}).get("biz_data", {}).get("user", {})
                token = user_data.get("token")
                user_id = user_data.get("id")

                if token:
                    # 保存配置
                    self.save_config(token, user_id, email)

                    return {
                        "success": True,
                        "token": token,
                        "user_id": user_id,
                        "email": email,
                        "error": None
                    }

            return {
                "success": False,
                "token": None,
                "error": result.get("msg", "登录失败")
            }

        except Exception as e:
            return {
                "success": False,
                "token": None,
                "error": str(e)
            }

    def check_token(self, token: str) -> bool:
        """检查 Token 是否有效"""
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {token}"

        try:
            resp = requests.post(
                f"{self.base_url}/api/v0/chat_session/create",
                headers=headers,
                json={},
                timeout=10
            )
            return resp.status_code == 200
        except:
            return False

    def get_valid_token(self, email: str, password: str) -> Optional[str]:
        """
        获取有效 Token - 自动检查过期并重新登录

        Args:
            email: 邮箱
            password: 密码

        Returns:
            有效 Token 或 None
        """
        # 检查现有 token
        config = self.load_config()
        if config and config.get("token"):
            if self.check_token(config["token"]):
                return config["token"]

        # 重新登录
        result = self.login(email, password)
        if result["success"]:
            return result["token"]

        return None

    def save_config(self, token: str, user_id: str, email: str) -> None:
        """保存配置"""
        config = {
            "user_id": user_id,
            "email": email,
            "token": token,
            "base_url": self.base_url,
            "login_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        }

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def load_config(self) -> Optional[Dict]:
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return None


# 便捷函数
def login(email: str, password: str) -> Optional[str]:
    """快速登录"""
    auth = DeepSeekLogin()
    result = auth.login(email, password)
    return result["token"] if result["success"] else None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    # 测试登录
    email = "920998743@qq.com"
    password = "czf520168"

    print("[测试] 自动登录...")
    auth = DeepSeekLogin()
    result = auth.login(email, password)

    if result["success"]:
        print(f"[成功] Token: {result['token'][:30]}...")
        print(f"[成功] 已保存到 config.json")

        # 验证
        if auth.check_token(result["token"]):
            print("[验证] Token 有效!")
    else:
        print(f"[失败] {result['error']}")