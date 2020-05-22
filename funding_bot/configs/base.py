from typing import Optional, List


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
    def get_dynamodb_table_name(cls) -> Optional[str]:
        return None

    @classmethod
    def get_telegram_api(cls) -> Optional[str]:
        chat_id = cls.get_telegram_chat_id()
        api_key = cls.get_telegram_api_key()

        if chat_id and api_key:
            return f"https://api.telegram.org/bot{api_key}/sendMessage?chat_id={chat_id}&text="
        return None

    @classmethod
    def get_minimum_lending_rate(cls) -> int:
        # As an annual rate, that's the minimum rate for a day will equal this value / 365.
        # In percent form. So a return value of 20 means 20% per year == 20/365 % a day
        raise NotImplementedError

    @classmethod
    def get_maximum_lending_amount(cls) -> int:
        # The total amount that can be lend out
        # -1 means no limit
        return -1

    @classmethod
    def get_funding_currencies(cls) -> List[str]:
        # Returns a list of all the currencies that the bot should keep track of
        # CURRENCIES = ["fUSD", "fETH", "fBTC"]
        raise NotImplementedError


__all__ = [
    "Configuration",
]
