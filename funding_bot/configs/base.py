from typing import Optional


class Configuration(object):
    @classmethod
    def get_api_key(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_api_secret_key(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_telegram_api_key(cls) -> Optional[str]:
        return None

    @classmethod
    def get_telegram_chat_id(cls) -> Optional[str]:
        return None
    
    @classmethod
    def get_telegram_api(cls) -> Optional[str]:
        chat_id = cls.get_telegram_chat_id()
        api_key = cls.get_telegram_api_key()
        
        if chat_id and api_key:
            return f"https://api.telegram.org/bot{api_key}/sendMessage?chat_id={chat_id}&text="
        return None


__all__ = [
    "Configuration",
]
