import hmac
import json
import logging
import hashlib
import tabulate
import requests
import datetime as dt

from collections import namedtuple

from typing import List, Dict, Any, Union, Optional, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from funding_bot.configs.base import Configuration
    from funding_bot.bot.tracker import RATE_DATA

Header = TypedDict(
    "Header",
    {"bfx-nonce": str, "bfx-apikey": str, "bfx-signature": str, "context-type": str},
)

FundingOrderData = TypedDict(
    "FundingOrderData",
    {
        "type": str,
        "symbol": str,
        "amount": str,
        "rate": str,
        "period": int,
        "flags": int,
    },
)

ActiveFundingData = TypedDict(
    "ActiveFundingData",
    {
        "ID": str,
        "Currency": str,
        "Amount": float,
        "Status": str,
        "Rate": float,
        "Period": int,
        "PositionPair": str,
    },
)

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

    def generate_signature(
        self, end_point: str, nonce: str, body: Dict[str, Any]
    ) -> str:
        signature = f"/api/{end_point}{nonce}{json.dumps(body)}"

        return hmac.new(
            key=self._config.get_api_secret_key().encode("utf8"),
            msg=signature.encode("utf8"),
            digestmod=hashlib.sha384,
        ).hexdigest()

    def generate_headers(self, end_point: str, body: Dict[str, Any]) -> Header:
        nonce = self.generate_nonce()
        return {
            "bfx-nonce": nonce,
            "bfx-apikey": self._config.get_api_key(),
            "bfx-signature": self.generate_signature(end_point, nonce, body),
            "content-type": "application/json",
        }

    def send_api_request(self, end_point: str, header: Header, body: Dict[str, Any]):
        response = requests.post(
            f"{self.get_api_url()}{end_point}", headers=header, data=json.dumps(body)
        )

        if response.status_code != 200:
            self._logger.error(
                f"API Request to {self.get_api_url()}{end_point} failed with {response.status_code}\n"
            )
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

    def get_currency_balance(self, currency: str) -> float:
        end_point = "v2/auth/r/wallets"
        body: Dict[str, Any] = {}
        header: Header = self.generate_headers(end_point, body)

        data = self.send_api_request(end_point, header, body)

        for row in data:
            if row[0] == "funding" and row[1] == currency[1:]:
                return float(row[2])
        return -1

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
            return tabulate.tabulate(
                data_entry, headers=["Currency", "Lending Rates", "Duration"]
            )

    def send_telegram_notification(self, msg: str):
        requests.get(f"{self._config.get_telegram_api()}{msg}")

    def generate_report(self, currencies: List[str]):
        wallet_data = self.grab_current_wallet_status()
        funding_summary = self.get_funding_summary(currencies)

        while wallet_data is None:
            wallet_data = self.grab_current_wallet_status()

        self._logger.info(wallet_data)
        self.send_telegram_notification(wallet_data)

        while funding_summary is None:
            funding_summary = self.get_funding_summary(currencies)

        self._logger.info(funding_summary)
        self.send_telegram_notification(funding_summary)

        orders: List[ActiveFundingData] = []
        for currency in currencies:
            orders = orders + self.get_active_funding_data(currency)

        order_data: List[Any] = []
        for order in orders:
            order_data.append(
                [
                    order["Currency"],
                    order["ID"],
                    order["Amount"],
                    f"{round(order['Rate'] * 10000, 4)}%",
                    order["Period"],
                    order["PositionPair"],
                ]
            )

        order_data_msg = tabulate.tabulate(
            order_data,
            headers=["Currency", "ID", "Amount", "Rate", "Period", "PositionPair"],
        )

        self._logger.info(order_data_msg)
        self.send_telegram_notification(order_data_msg)

    def submit_funding_offer(
        self, currency: str, rate_data: "RATE_DATA", amount: Union[int, float]
    ) -> int:
        end_point = "v2/auth/w/funding/offer/submit"
        offer_rate = max(rate_data.FRR, rate_data.Last)
        # if (rate_data.High - offer_rate) * 365 > 5:
        #     offer_rate = (rate_data.High - 1 / 365)

        if currency == "fUSD":
            if offer_rate < 0.0009:
                self._logger.info(f"Current Offer Rate {offer_rate} -> 0.00098")
                offer_rate = 0.00098  # TODO requires changing

        if offer_rate == 0:
            self._logger.warning("Cannot submit order with 0 offer rate, abort")
            return

        days = 2
        if offer_rate * 36500 > 36:
            days = 30
        # elif offer_rate * 365 > 25:
        #     days = 20
        # elif offer_rate * 365 > 20:
        #     days = 10

        amount = ("%.6f" % abs(amount))[
            :-1
        ]  # Truncate at 5th decimal places to avoid rounding error
        body: FundingOrderData = {
            "type": "LIMIT",
            "symbol": currency,
            "amount": amount,
            "rate": str(offer_rate),
            "period": days,
            "flags": 0,
        }

        header: Header = self.generate_headers(end_point, body)

        data = self.send_api_request(end_point, header, body)

        if data:
            self._logger.info(
                f"Order ID: {data[4][0]} {data[7]}"
            )
            self.send_telegram_notification(
                f"Order ID: {data[4][0]} {data[7]}"
            )

            return data[4][0]  # Returns Offer ID

    def get_active_funding_data(self, currency: str) -> List[ActiveFundingData]:
        end_point = f"v2/auth/r/funding/credits/{currency}"

        body: Dict[str, Any] = {}

        header: Header = self.generate_headers(end_point, body)

        data = self.send_api_request(end_point, header, body)

        order_data: List[ActiveFundingData] = []

        if data:
            for order in data:
                order_data.append(
                    ActiveFundingData(
                        ID=order[0],
                        Currency=order[1],
                        Amount=order[5],
                        Status=order[7],
                        Rate=order[11],
                        Period=order[12],
                        PositionPair=order[-1],
                    )
                )

        return order_data

    def cancel_funding_offer(self, id_: str) -> bool:
        end_point = f"v2/auth/w/funding/offer/cancel"

        body: Dict[str, Any] = {
            "id": int(id_)
        }

        header: Header = self.generate_headers(end_point, body)

        data = self.send_api_request(end_point, header, body)

        if data:
            if data[6] == "SUCCESS":
                self.send_telegram_notification(f"Order id: {id_} cancel successfully")
                self._logger.warning(f"Order id: {id_} cancel successfully")
                return True
            else:
                self.send_telegram_notification(f"Unexpected Response: {data[6]} for order id: {id_}")
                self._logger.warning(f"Unexpected Response: {data[6]} for order id: {id_}")

        return False


__all__ = [
    FundingBot,
]
