#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek SDK - Core API Client

A standalone module for interacting with DeepSeek chat API.
Can be reused in any Python project.

Usage:
    from deepseek_sdk import DeepSeekAPI

    api = DeepSeekAPI(token="your_token")
    api.create_session()

    # Streaming response
    for chunk in api.chat_stream("Hello"):
        print(chunk)

    # Full response
    result = api.chat("Hello")
    print(result['content'])
"""

import os
import json
import base64
import subprocess
import time
import requests
from typing import Optional, Dict, List, Generator, Any


class DeepSeekAPI:
    """DeepSeek API Client"""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://chat.deepseek.com",
        solver_path: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        """
        Initialize DeepSeek API client.

        Args:
            token: Bearer token from DeepSeek web login
            base_url: API server URL (default: https://chat.deepseek.com)
            solver_path: Path to PoW solver JS file
            config_file: Path to config JSON file (auto-load if None)
        """
        self.base_url = base_url
        self.token = token
        self.session_id: Optional[str] = None
        self.parent_message_id: Optional[int] = None
        self.messages_history: List[Dict] = []

        # Solver path
        sdk_dir = os.path.dirname(os.path.abspath(__file__))
        self.solver_path = solver_path or os.path.join(sdk_dir, "pow_solver.js")

        # Headers
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "x-app-version": "20241129.1",
            "x-client-locale": "zh_CN",
            "x-client-platform": "web",
            "x-client-timezone-offset": "28800",
            "x-client-version": "1.8.0",
        }

        # Load config if no token
        if not token and not config_file:
            config_file = os.path.join(sdk_dir, "config.json")

        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        elif token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        """Set API token."""
        self.token = token
        self.headers["Authorization"] = f"Bearer {token}"

    def set_base_url(self, base_url: str) -> None:
        """Set API base URL."""
        self.base_url = base_url
        self.headers["Origin"] = base_url
        self.headers["Referer"] = f"{base_url}/"

    def load_config(self, config_file: str) -> bool:
        """
        Load configuration from JSON file.

        Args:
            config_file: Path to config JSON file

        Returns:
            True if loaded successfully
        """
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("token")
                base_url = data.get("base_url", self.base_url)

                if token:
                    self.set_token(token)
                if base_url:
                    self.set_base_url(base_url)
                return bool(token)
        except Exception as e:
            print(f"[DeepSeek] Config load error: {e}")
        return False

    def save_config(self, config_file: Optional[str] = None) -> bool:
        """Save current configuration to file."""
        if not config_file:
            config_file = os.path.join(os.path.dirname(__file__), "config.json")

        try:
            data = {
                "token": self.token,
                "base_url": self.base_url
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[DeepSeek] Config save error: {e}")
        return False

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages_history = []
        self.parent_message_id = None
        self.session_id = None

    # ==================== PoW Methods ====================

    def get_pow_challenge(self, target_path: str = "/api/v0/chat/completion") -> Dict:
        """Get PoW challenge from server."""
        url = f"{self.base_url}/api/v0/chat/create_pow_challenge"
        resp = requests.post(url, headers=self.headers, json={"target_path": target_path}, timeout=10)

        if resp.status_code == 429:
            raise Exception("Rate Limit (429)")
        if resp.status_code != 200:
            raise Exception(f"PoW challenge failed: {resp.status_code}")

        result = resp.json()
        if "data" in result and "biz_data" in result["data"]:
            return result["data"]["biz_data"]["challenge"]
        return result.get("data", result)

    def solve_pow(self, challenge_data: Dict) -> Dict:
        """Solve PoW challenge using WASM solver."""
        challenge = challenge_data.get("challenge")
        salt = challenge_data.get("salt")
        expire_at = challenge_data.get("expire_at")
        difficulty = challenge_data.get("difficulty", 144000)
        signature = challenge_data.get("signature")
        algorithm = challenge_data.get("algorithm", "DeepSeekHashV1")
        target_path = challenge_data.get("target_path", "/api/v0/chat/completion")

        solver_input = json.dumps({
            "challenge": challenge,
            "salt": salt,
            "expire_at": expire_at,
            "difficulty": difficulty
        })

        result = subprocess.run(
            ["node", self.solver_path],
            input=solver_input,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(self.solver_path),
            timeout=30
        )

        if result.returncode != 0:
            raise Exception(f"PoW solver failed: {result.stderr}")

        solver_output = json.loads(result.stdout)
        if not solver_output.get("success"):
            raise Exception("PoW no solution found")

        return {
            "algorithm": algorithm,
            "challenge": challenge,
            "salt": salt,
            "answer": solver_output["answer"],
            "signature": signature,
            "target_path": target_path
        }

    # ==================== Session Methods ====================

    def create_session(self) -> str:
        """Create a new chat session."""
        url = f"{self.base_url}/api/v0/chat_session/create"
        resp = requests.post(url, headers=self.headers, json={}, timeout=10)

        if resp.status_code == 429:
            raise Exception("Rate Limit (429)")
        if resp.status_code != 200:
            raise Exception(f"Session creation failed: {resp.status_code}")

        result = resp.json()
        if "data" in result and "biz_data" in result["data"]:
            biz_data = result["data"]["biz_data"]
            chat_session = biz_data.get("chat_session", {})
            self.session_id = chat_session.get("id") or biz_data.get("id")
        else:
            self.session_id = result.get("data", {}).get("session_id")

        if not self.session_id:
            raise Exception("Failed to get session_id")

        return self.session_id

    def ensure_session(self) -> str:
        """Ensure session exists, create if needed."""
        if not self.session_id:
            self.create_session()
        return self.session_id

    # ==================== Chat Methods ====================

    def send_message(
        self,
        message: str,
        thinking: bool = False,
        model_type: str = "default",
        search_enabled: bool = False,
        file_ids: Optional[List[str]] = None
    ) -> requests.Response:
        """
        Send message and return streaming response.

        Args:
            message: User message
            thinking: Enable thinking mode
            model_type: "default" or "expert"
            search_enabled: Enable web search
            file_ids: List of uploaded file IDs

        Returns:
            Streaming response object
        """
        self.ensure_session()

        # PoW
        challenge = self.get_pow_challenge()
        pow_solution = self.solve_pow(challenge)

        headers = self.headers.copy()
        headers["x-ds-pow-response"] = base64.b64encode(
            json.dumps(pow_solution).encode()
        ).decode()

        # Build messages
        messages = self.messages_history.copy()
        messages.append({"role": "user", "content": message})

        data = {
            "chat_session_id": self.session_id,
            "parent_message_id": self.parent_message_id,
            "model_type": model_type,
            "prompt": message,
            "messages": messages,
            "ref_file_ids": file_ids or [],
            "thinking_enabled": thinking,
            "search_enabled": search_enabled,
            "preempt": False
        }

        url = f"{self.base_url}/api/v0/chat/completion"
        resp = requests.post(url, headers=headers, json=data, stream=True, timeout=60)

        if resp.status_code == 401:
            raise Exception("Token expired (401) - please re-login")
        if resp.status_code == 429:
            raise Exception("Rate Limit (429)")
        if resp.status_code != 200:
            raise Exception(f"Chat failed: {resp.status_code} - {resp.text[:100]}")

        return resp

    def chat_stream(
        self,
        message: str,
        thinking: bool = False,
        model_type: str = "default",
        search_enabled: bool = False,
        file_ids: Optional[List[str]] = None
    ) -> Generator[str, None, None]:
        """
        Chat with streaming response (generator).

        Yields:
            Text chunks
        """
        resp = self.send_message(message, thinking, model_type, search_enabled, file_ids)

        content = ""
        message_id = None
        fragment_type = None

        for line in resp.iter_lines(decode_unicode=True):
            if not line or line.startswith("event:"):
                continue

            if line.startswith("data:"):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)

                    if isinstance(data.get("v"), dict):
                        r = data["v"].get("response", {})
                        frags = r.get("fragments", [])
                        if frags:
                            fragment_type = frags[-1].get("type", "RESPONSE")
                        if "message_id" in r:
                            message_id = r["message_id"]

                    elif data.get("p") == "response" and data.get("o") == "BATCH":
                        for op in data.get("v", []):
                            if op.get("p") == "fragments" and op.get("o") == "APPEND":
                                new_frags = op.get("v", [])
                                if new_frags:
                                    fragment_type = new_frags[-1].get("type", "RESPONSE")

                    elif isinstance(data.get("v"), str):
                        if data["v"] in ("FINISHED", "SUCCESS", "PENDING"):
                            continue
                        if fragment_type == "RESPONSE":
                            yield data["v"]
                            content += data["v"]

                except json.JSONDecodeError:
                    pass

        # Update state
        if message_id:
            self.parent_message_id = message_id
        if content:
            self.messages_history.append({"role": "user", "content": message})
            self.messages_history.append({"role": "assistant", "content": content})

    def chat(
        self,
        message: str,
        thinking: bool = False,
        model_type: str = "default",
        search_enabled: bool = False,
        file_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Chat and return complete response.

        Returns:
            {"content": str, "message_id": int}
        """
        resp = self.send_message(message, thinking, model_type, search_enabled, file_ids)

        content = ""
        message_id = None
        fragment_type = None

        for line in resp.iter_lines(decode_unicode=True):
            if not line or line.startswith("event:"):
                continue

            if line.startswith("data:"):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)

                    if isinstance(data.get("v"), dict):
                        r = data["v"].get("response", {})
                        frags = r.get("fragments", [])
                        if frags:
                            fragment_type = frags[-1].get("type", "RESPONSE")
                        if "message_id" in r:
                            message_id = r["message_id"]

                    elif data.get("p") == "response" and data.get("o") == "BATCH":
                        for op in data.get("v", []):
                            if op.get("p") == "fragments" and op.get("o") == "APPEND":
                                new_frags = op.get("v", [])
                                if new_frags:
                                    fragment_type = new_frags[-1].get("type", "RESPONSE")

                    elif isinstance(data.get("v"), str):
                        if data["v"] in ("FINISHED", "SUCCESS", "PENDING"):
                            continue
                        if fragment_type == "RESPONSE":
                            content += data["v"]

                except json.JSONDecodeError:
                    pass

        # Update state
        if message_id:
            self.parent_message_id = message_id
        if content:
            self.messages_history.append({"role": "user", "content": message})
            self.messages_history.append({"role": "assistant", "content": content})

        return {"content": content, "message_id": message_id}

    # ==================== File Methods ====================

    def upload_file(
        self,
        file_path: str,
        wait_for_parse: bool = True,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Upload file to DeepSeek.

        Args:
            file_path: Path to file
            wait_for_parse: Wait for parsing completion
            timeout: Parse wait timeout

        Returns:
            {"file_id": str, "file_name": str, "status": str}
        """
        # PoW for upload
        challenge = self.get_pow_challenge("/api/v0/file/upload_file")
        pow_solution = self.solve_pow(challenge)

        url = f"{self.base_url}/api/v0/file/upload_file"
        headers = self.headers.copy()
        headers["x-ds-pow-response"] = base64.b64encode(
            json.dumps(pow_solution).encode()
        ).decode()
        headers.pop("Content-Type", None)

        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1].lower()

        mime_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, mime_type)}
            resp = requests.post(url, headers=headers, files=files, data={}, timeout=30)

        if resp.status_code != 200:
            raise Exception(f"Upload failed: {resp.status_code}")

        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"Upload failed: {result.get('msg')}")

        file_info = result.get("data", {}).get("biz_data", {})
        file_id = file_info.get("id")

        info = {"file_id": file_id, "file_name": file_name, "status": file_info.get("status")}

        # Wait for parsing
        if wait_for_parse and file_id:
            start = time.time()
            while time.time() - start < timeout:
                status = self.get_file_status(file_id)
                if status:
                    st = status.get("status")
                    if st in ("SUCCESS", "PARSED", "READY"):
                        info["status"] = "SUCCESS"
                        return info
                    elif st in ("FAILED", "ERROR"):
                        raise Exception("File parsing failed")
                time.sleep(2)
            raise Exception("File parsing timeout")

        return info

    def get_session_list(self, count=50):
        """获取会话历史列表"""
        url = f"{self.base_url}/api/v0/chat_session/fetch_page"
        headers = self.headers.copy()

        # GET 请求
        try:
            resp = requests.get(url, headers=headers, params={"count": count}, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    return result.get("data", {}).get("biz_data", {}).get("chat_sessions", [])
            return []
        except Exception as e:
            print(f"[Session list] Error: {e}")
            return []

    def get_chat_history(self, session_id, limit=50):
        """获取指定会话的消息历史 - GET 请求"""
        url = f"{self.base_url}/api/v0/chat/history_messages"
        headers = self.headers.copy()

        # GET 请求，参数作为 query
        params = {"chat_session_id": session_id, "limit": limit}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    return result.get("data", {}).get("biz_data", {}).get("chat_messages", [])
            return []
        except Exception as e:
            print(f"[Chat history] Error: {e}")
            return []


# Convenience function
def create_client(token: Optional[str] = None, base_url: str = "https://chat.deepseek.com") -> DeepSeekAPI:
    """Create a DeepSeek API client."""
    return DeepSeekAPI(token=token, base_url=base_url)