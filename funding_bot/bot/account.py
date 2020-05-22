import boto3
import logging

import datetime as dt

from collections import namedtuple

from botocore.exceptions import ClientError

from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from funding_bot.configs.base import Configuration
    from funding_bot.bot.funding import ActiveFundingData, ActiveFundingOfferData


FUNDING_DATA = namedtuple("FUNDING_DATA", ["Date", "InitialBalance"])

DEFAULT_VALUE = {
    "fUSD": 1000,
    "fBTC": 0.1,
    "fETH": 1,
}


def get_initial_start_data(
    currency: str, table_name: str, logger: logging.Logger
) -> Optional[FUNDING_DATA]:
    aws_context = boto3.resource("dynamodb", region_name="ap-southeast-2")
    try:
        initial_balance_data = aws_context.Table(table_name).get_item(
            Key={"Key": currency}
        )
    except ClientError as e:
        logger.debug(f"Failed to fetch balance for {currency}")
        return None
    else:
        return FUNDING_DATA(
            Date=dt.datetime.strptime(initial_balance_data["Item"]["Date"], "%m-%d-%Y"),
            InitialBalance=float(initial_balance_data["Item"]["InitialBalance"]),
        )


class Account(object):
    def __init__(self, configuration: "Configuration", logger: logging.Logger):
        self._maximum_lending_amount = configuration.get_maximum_lending_amount()
        self._minimum_lending_rate = {
            currency: round(rate / 36500, 7)
            for currency, rate in configuration.get_minimum_lending_rate().items()
        }
        self._current_active_funding: List["ActiveFundingData"] = []
        self._current_pending_funding: List["ActiveFundingOfferData"] = []

        self._current_lend_amount: float = 0
        self._current_pending_amount: float = 0
        self._available_fundings = dict()
        self._initial_balance = {
            currency: get_initial_start_data(
                currency, configuration.get_dynamodb_table_name(), logger
            )
            or FUNDING_DATA(
                Date=dt.datetime.now().date(), InitialBalance=DEFAULT_VALUE[currency]
            )
            for currency in configuration.get_funding_currencies()
        }

    def get_initial_balance(self, currency: str) -> FUNDING_DATA:
        return self._initial_balance[currency]

    def get_minimum_daily_lending_rate(self, currency: str) -> float:
        return self._minimum_lending_rate.get(currency, -1)

    def get_maximum_lending_amount(self, currency: str) -> float:
        return self._maximum_lending_amount.get(currency, -1)

    def get_active_funding_data(self) -> List["ActiveFundingData"]:
        return list(self._current_active_funding)

    def get_pending_funding(self) -> List["ActiveFundingOfferData"]:
        return list(self._current_pending_funding)

    def update_current_active_funding(
        self, active_funding_data: List["ActiveFundingData"]
    ):
        self._current_active_funding = active_funding_data
        self._repopulate_lending_amount()

    def update_current_pending_offers(
        self, active_offer_data: List["ActiveFundingOfferData"]
    ):
        self._current_pending_funding = active_offer_data
        self._repopulate_pending_amount()

    def _repopulate_lending_amount(self):
        self._current_lend_amount = sum(
            [
                active_funding["Amount"]
                for active_funding in self.get_active_funding_data()
            ]
        )

    def _repopulate_pending_amount(self):
        self._current_pending_amount = sum(
            [pending_offer["Amount"] for pending_offer in self.get_pending_funding()]
        )

    def get_available_fundings(self) -> Dict[str, float]:
        return dict(self._available_fundings)

    def get_funding_for_offer(self, currency: str) -> float:
        available_funding = self._available_fundings.get(currency, 0)
        maximum_lending_amount = self._maximum_lending_amount.get(currency)

        if maximum_lending_amount:
            available_funding = min(
                available_funding,
                maximum_lending_amount
                - self._current_lend_amount
                - self._current_pending_amount,
            )
            if available_funding < 0:
                return 0
            return available_funding
        return available_funding

    def update_available_funding(self, currency: str, amount: float):
        self._available_fundings[currency] = amount
