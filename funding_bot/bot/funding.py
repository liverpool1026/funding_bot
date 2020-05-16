import hmac
import json
import logging
import hashlib
import tabulate
import requests
import datetime as dt

from collections import namedtuple

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from funding_bot.configs.base import Configuration

Header = TypedDict("Header", {"bfx-nonce": str, "bfx-apikey": str, "bfx-signature": str, "context-type": str})
LendingSummary = namedtuple("LendingSummary", ("Yield", "Duration"))


class FundingBot(object):
    def __init__(self, configuration: "Configuration", logger: logging.Logger):
        self._config = configuration
        self._logger = logger

    @classmethod
    def get_api_url(cls) -> str:
        return "https://api.bitfinex.com/"

    @classmethod
    def generate_nonce(cls) -> str:
        return str(int(dt.datetime.now().timestamp() * 1000000))

    def generate_signature(self, end_point: str, nonce: str, body: Dict[str, Any]) -> str:
        signature = f"/api/{end_point}{nonce}{json.dumps(body)}"

        return hmac.new(key=self._config.get_api_secret_key().encode('utf8'), msg=signature.encode('utf8'), digestmod=hashlib.sha384).hexdigest()

    def generate_headers(self, end_point: str, body: Dict[str, Any]) -> Header:
        nonce = self.generate_nonce()
        return {
            "bfx-nonce": nonce,
            "bfx-apikey": self._config.get_api_key(),
            "bfx-signature": self.generate_signature(end_point, nonce, body),
            "content-type": "application/json"
        }

    def send_api_request(self, end_point: str, header: Header, body: Dict[str, Any]):
        response = requests.post(f"{self.get_api_url()}{end_point}", headers=header, data=json.dumps(body))

        if response.status_code != 200:
            self._logger.error(f"API Request to {self.get_api_url()}{end_point} failed with {response.status_code}\n")
        else:
            return json.loads(response.content.decode())

    def grab_current_wallet_status(self) -> Optional[str]:
        end_point = "v2/auth/r/wallets"
        body: Dict[str, Any] = {}
        header: Header = self.generate_headers(end_point, body)

        data = self.send_api_request(end_point, header, body)

        if data:
            data = [row[:3] for row in data]
            return tabulate.tabulate(data, headers=["Type", "Currency", "Amount"])

    def grab_available_funding(self, currency: str = "fUSD") -> float:
        end_point = "v2/auth/calc/order/avail"
        body: Dict[str, Any] = {
            "symbol": currency,
            "type": "FUNDING",
        }
        header: Header = self.generate_headers(end_point, body)

        data = self.send_api_request(end_point, header, body)

        if data:
            # Somehow the return value is negative
            return abs(data[0])

        return -1.0

    def get_funding_summary(self, currencies: List[str]) -> str:
        data_entry = []
        for currency in currencies:
            end_point = f"v2/auth/r/info/funding/{currency}"
            header: Header = self.generate_headers(end_point, {})

            data = self.send_api_request(end_point, header, {})

            if data:
                rate = f"{round(data[2][1] * 36500, 4)}%"
                duration = f"{int(data[2][3])} days"
                data_entry.append([currency, rate, duration])

        if data_entry:
            return tabulate.tabulate(data_entry, headers=["Currency", "Lending Rates", "Duration"])

    def send_telegram_notification(self, msg: str):
        requests.get(f"{self._config.get_telegram_api()}{msg}")

    def generate_report(self, currencies: List[str]):
        wallet_data = self.grab_current_wallet_status()
        funding_summary = self.get_funding_summary(currencies)

        while wallet_data is None:
            wallet_data = self.grab_current_wallet_status()

        self.send_telegram_notification(wallet_data)

        while funding_summary is None:
            funding_summary = self.get_funding_summary(currencies)

        self.send_telegram_notification(funding_summary)




__all__ = [
    FundingBot,
]