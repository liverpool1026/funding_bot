from .base import Configuration
from typing import Optional


# Please use this file as template and fill in the following configurations and rename the file to myconfig.py

class AccountConfiguration(Configuration):
    @classmethod
    def get_api_key(cls) -> str:
        return ""

    @classmethod
    def get_api_secret_key(cls) -> str:
        return ""

    @classmethod
    def get_telegram_chat_id(cls) -> Optional[str]:
        return None

    @classmethod
    def get_telegram_api_key(cls) -> Optional[str]:
        return None


__all__ = [
    "AccountConfiguration",
]
