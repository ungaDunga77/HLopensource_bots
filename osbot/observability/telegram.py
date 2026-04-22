"""Telegram ops controls (stub for M0). allowed_chat_id enforcement in M3."""

from __future__ import annotations


class TelegramOps:
    def __init__(self, bot_token: str, allowed_chat_id: str) -> None:
        self.bot_token = bot_token
        self.allowed_chat_id = allowed_chat_id
