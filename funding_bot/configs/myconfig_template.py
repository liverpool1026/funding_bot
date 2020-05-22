from .base import Configuration
from typing import Optional, List


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

    @classmethod
    def get_funding_currencies(cls) -> List[str]:
        return []

    @classmethod
    def get_minimum_lending_rate(cls) -> int:
        return 5

    @classmethod
    def get_maximum_lending_amount(cls) -> int:
        return -1


__all__ = [
    "AccountConfiguration",
]
