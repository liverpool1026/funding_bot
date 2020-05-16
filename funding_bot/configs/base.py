from typing import Optional


class Configuration(object):
    @classmethod
    def get_api_key(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_api_secret_key(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_telegram_api(cls) -> Optional[str]:
        return None


__all__ = [
    "Configuration",
]
