import datetime as dt

from .base import Configuration
from typing import Optional, List, Dict

# Please use this file as template and fill in the following configurations and rename the file to myconfig.py


class AccountConfiguration(Configuration):
    @classmethod
    def get_api_key(cls) -> str:
        # Bitfinex API Key
        return ""

    @classmethod
    def get_api_secret_key(cls) -> str:
        # Bitfinex API Secret Key
        return ""

    @classmethod
    def get_telegram_chat_id(cls) -> Optional[str]:
        return None

    @classmethod
    def get_dynamodb_table_name(cls) -> Optional[str]:
        return None

    @classmethod
    def get_funding_start_date(cls) -> Optional["dt.date"]:
        # Must be supplied unless dynamodb is setup to contain the initial balance info
        return None

    @classmethod
    def get_initial_balance(cls) -> Dict[str, float]:
        # Must be supplied unless dynamodb is setup to contain the initial balance info
        # The dict key must be what is returned from `get_funding_currencies`
        return {}

    @classmethod
    def get_telegram_api_key(cls) -> Optional[str]:
        return None

    @classmethod
    def get_funding_currencies(cls) -> List[str]:
        # Returns a list of all the currencies that the bot should keep track of
        # CURRENCIES = ["fUSD", "fETH", "fBTC"]
        return []

    @classmethod
    def get_minimum_lending_rate(cls) -> Dict[str, int]:
        # As an annual rate, that's the minimum rate for a day will equal this value / 365.
        # In percent form. So a return value of 20 means 20% per year == 20/365 % a day
        # The dictionary key must be defined in get_funding_currencies
        # For any entries in get_funding_currencies but not defined will be assumed to be no limit
        return {}

    @classmethod
    def get_maximum_lending_amount(cls) -> Dict[str, int]:
        # The total amount that can be lend out
        # The dictionary key must be defined in get_funding_currencies
        # For any entries in get_funding_currencies but not defined will be assumed to be no limit
        return {}

    @classmethod
    def get_sentry_dsn(cls) -> Optional[str]:
        return None


__all__ = [
    "AccountConfiguration",
]
