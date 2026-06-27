#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek SDK

A standalone Python SDK for DeepSeek chat API with auto login support.
"""

from .api import DeepSeekAPI, create_client
from .login import DeepSeekLogin, login as auto_login

__version__ = "1.1.0"
__all__ = ["DeepSeekAPI", "create_client", "DeepSeekLogin", "auto_login"]