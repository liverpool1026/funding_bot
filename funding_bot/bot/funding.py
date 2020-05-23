import hmac
import json
import logging
import hashlib
import tabulate
import requests
import datetime as dt

from typing import List, Dict, Any, Optional, NamedTuple, TYPE_CHECKING
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from funding_bot.bot.account import LendingOffer

Header = TypedDict(
    "Header",
    {"bfx-nonce": str, "bfx-apikey": str, "bfx-signature": str, "content-type": str},
)


class Credentials(NamedTuple):
    api_key: str
    api_secret_key: str
    telegram_api: Optional[str]


class FundingOrderData(TypedDict):
    type: str
    symbol: str
    amount: str
    rate: str
    period: int
    flags: int


class ActiveFundingData(NamedTuple):
    id: str
    currency: str
    amount: float
    status: str
    rate: float
    period: int
    position_pair: str


class ActiveFundingOfferData(NamedTuple):
    id: str
    currency: str
    amount: float
    status: str
    rate: float
    period: int


class FundingBot(object):
    @classmethod
    def get_api_url(cls) -> str:
        return "https://api.bitfinex.com/"

    @classmethod
    def generate_nonce(cls) -> str:
        return str(int(dt.datetime.now().timestamp() * 1000000))

    @classmethod
    def generate_signature(
        cls, credentials: Credentials, end_point: str, nonce: str, body: Dict[str, Any]
    ) -> str:
        signature = f"/api/{end_point}{nonce}{json.dumps(body)}"

        return hmac.new(
            key=credentials.api_secret_key.encode("utf8"),
            msg=signature.encode("utf8"),
            digestmod=hashlib.sha384,
        ).hexdigest()

    @classmethod
    def generate_headers(
        cls, credentials: Credentials, end_point: str, body: Dict[str, Any]
    ) -> Header:
        nonce = cls.generate_nonce()
        return {
            "bfx-nonce": nonce,
            "bfx-apikey": credentials.api_key,
            "bfx-signature": cls.generate_signature(
                credentials, end_point, nonce, body
            ),
            "content-type": "application/json",
        }

    @classmethod
    def send_api_request(
        cls,
        end_point: str,
        header: Header,
        body: Dict[str, Any],
        logger: logging.Logger,
    ):
        response = requests.post(
            f"{cls.get_api_url()}{end_point}", headers=header, data=json.dumps(body)
        )

        if response.status_code != 200:
            logger.error(
                f"API Request to {cls.get_api_url()}{end_point} failed with {response.status_code}\n"
            )
        else:
            return json.loads(response.content.decode())

    @classmethod
    def grab_current_wallet_status(
        cls, credentials: Credentials, logger: logging.Logger
    ) -> Optional[str]:
        end_point = "v2/auth/r/wallets"
        body: Dict[str, Any] = {}
        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        if data:
            data = [row[:3] for row in data]
            return tabulate.tabulate(data, headers=["Type", "Currency", "Amount"])
        return None

    @classmethod
    def get_currency_balance(
        cls, credentials: Credentials, currency: str, logger: logging.Logger
    ) -> float:
        end_point = "v2/auth/r/wallets"
        body: Dict[str, Any] = {}
        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        for row in data:
            if row[0] == "funding" and row[1] == currency[1:]:
                return float(row[2])
        return -1

    @classmethod
    def grab_available_funding(
        cls, credentials: Credentials, currency: str, logger: logging.Logger
    ) -> float:
        end_point = "v2/auth/calc/order/avail"
        body: Dict[str, Any] = {
            "symbol": currency,
            "type": "FUNDING",
        }
        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        if data:
            # Somehow the return value is negative
            return abs(data[0])

        return -1.0

    @classmethod
    def get_funding_summary(
        cls, credentials: Credentials, currencies: List[str], logger: logging.Logger
    ) -> Optional[str]:
        data_entry = []
        for currency in currencies:
            end_point = f"v2/auth/r/info/funding/{currency}"
            header: Header = cls.generate_headers(credentials, end_point, {})

            data = cls.send_api_request(end_point, header, {}, logger)

            if data:
                rate = f"{round(data[2][1] * 36500, 4)}%"
                duration = f"{int(data[2][3])} days"
                data_entry.append([currency, rate, duration])

        if data_entry:
            return tabulate.tabulate(
                data_entry, headers=["Currency", "Lending Rates", "Duration"]
            )
        return None

    @classmethod
    def submit_funding_offer(
        cls,
        credentials: Credentials,
        currency: str,
        lending_data: "LendingOffer",
        minimum_lending_rate: float,
        logger: logging.Logger,
    ) -> Optional[int]:
        end_point = "v2/auth/w/funding/offer/submit"
        telegram_api_key = credentials.telegram_api
        offer_rate = lending_data.rate
        days = lending_data.period

        if offer_rate <= 0:
            logger.error(f"Cannot submit order with {offer_rate} offer rate, abort")
            cls.send_telegram_notification(
                telegram_api_key,
                f"Cannot submit order with {offer_rate} offer rate, abort",
            )
            return None

        if offer_rate * 365 * 100 < minimum_lending_rate:
            logger.info(
                f"Cannot submit order with {offer_rate} offer rate, as the offered rate is smaller than the allowed minimum lending rate\n"
            )
            cls.send_telegram_notification(
                telegram_api_key,
                f"Cannot submit order with {offer_rate} offer rate, as the offered rate is smaller than the allowed minimum lending rate\n",
            )
            return None

        body: Dict = {
            "type": "LIMIT",
            "symbol": currency,
            "amount": lending_data.amount,
            "rate": str(offer_rate),
            "period": days,
            "flags": 0,
        }

        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        if data:
            logger.info(f"Order ID: {data[4][0]} {data[7]}")
            cls.send_telegram_notification(
                telegram_api_key, f"Order ID: {data[4][0]} {data[7]}"
            )

            return data[4][0]  # Returns Offer ID

        return None

    @classmethod
    def get_active_funding_data(
        cls, credentials: Credentials, currency: str, logger: logging.Logger
    ) -> List[ActiveFundingData]:
        end_point = f"v2/auth/r/funding/credits/{currency}"

        body: Dict[str, Any] = {}

        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        order_data: List[ActiveFundingData] = []

        if data:
            for order in data:
                order_data.append(
                    ActiveFundingData(
                        id=order[0],
                        currency=order[1],
                        amount=order[5],
                        status=order[7],
                        rate=order[11],
                        period=order[12],
                        position_pair=order[-1],
                    )
                )

        return order_data

    @classmethod
    def get_funding_offer_history(
        cls, credentials: Credentials, currency: str, logger: logging.Logger
    ) -> Dict[str, str]:
        end_point = f"v2/auth/r/funding/offers/{currency}/hist"

        body: Dict[str, Any] = {}

        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        if data:
            return {str(offer[0]): offer[10] for offer in data}
        return dict()

    @classmethod
    def get_active_funding_offer_data(
        cls, credentials: Credentials, currency: str, logger: logging.Logger
    ) -> List[ActiveFundingOfferData]:
        end_point = f"v2/auth/r/funding/offers/{currency}"

        body: Dict[str, Any] = {}

        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        order_data: List[ActiveFundingOfferData] = []

        if data:
            for order in data:
                order_data.append(
                    ActiveFundingOfferData(
                        id=order[0],
                        currency=order[1],
                        amount=order[5],
                        status=order[10],
                        rate=order[14],
                        period=order[15],
                    )
                )

        return order_data

    @classmethod
    def cancel_funding_offer(
        cls, credentials: Credentials, id_: str, logger: logging.Logger
    ) -> bool:
        end_point = f"v2/auth/w/funding/offer/cancel"
        telegram_api_key = credentials.telegram_api

        body: Dict[str, Any] = {"id": int(id_)}

        header: Header = cls.generate_headers(credentials, end_point, body)

        data = cls.send_api_request(end_point, header, body, logger)

        if data:
            if data[6] == "SUCCESS":
                cls.send_telegram_notification(
                    telegram_api_key, f"Order id: {id_} cancel successfully"
                )
                logger.info(f"Order id: {id_} cancel successfully")
                return True
            else:
                cls.send_telegram_notification(
                    telegram_api_key,
                    f"Unexpected Response: {data[6]} for order id: {id_}",
                )
                logger.warning(f"Unexpected Response: {data[6]} for order id: {id_}")

        return False

    @classmethod
    def send_telegram_notification(cls, telegram_api_key: Optional[str], msg: str):
        if telegram_api_key:
            requests.get(f"{telegram_api_key}{msg}")

    @classmethod
    def generate_report(
        cls, credentials: Credentials, currencies: List[str], logger: logging.Logger
    ):
        telegram_api_key = credentials.telegram_api
        wallet_data = cls.grab_current_wallet_status(credentials, logger)
        funding_summary = cls.get_funding_summary(credentials, currencies, logger)

        while wallet_data is None:
            wallet_data = cls.grab_current_wallet_status(credentials, logger)

        logger.info(wallet_data)
        cls.send_telegram_notification(telegram_api_key, wallet_data)

        while funding_summary is None:
            funding_summary = cls.get_funding_summary(credentials, currencies, logger)

        logger.info(funding_summary)
        cls.send_telegram_notification(telegram_api_key, funding_summary)

        orders: List[ActiveFundingData] = []
        for currency in currencies:
            orders = orders + cls.get_active_funding_data(credentials, currency, logger)

        order_data: List[Any] = []
        for order in orders:
            order_data.append(
                [
                    order.currency,
                    order.id,
                    order.amount,
                    f"{round(order.rate * 100, 4)}%",
                    order.period,
                    order.position_pair,
                ]
            )

        order_data_msg = tabulate.tabulate(
            order_data,
            headers=["Currency", "ID", "Amount", "Rate", "Period", "PositionPair"],
        )

        logger.info(order_data_msg)
        cls.send_telegram_notification(telegram_api_key, order_data_msg)


__all__ = [
    "FundingBot",
    "Credentials",
]
