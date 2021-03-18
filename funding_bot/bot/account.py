import boto3
import logging

import datetime as dt

from botocore.exceptions import ClientError, NoCredentialsError

from typing import List, Dict, NamedTuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from funding_bot.configs.base import Configuration
    from funding_bot.bot.funding import ActiveFundingData, ActiveFundingOfferData


class FundingData(NamedTuple):
    date: dt.date
    initial_balance: float


class LendingOffer(NamedTuple):
    currency: str
    amount: str
    rate: float
    period: int


DEFAULT_VALUE = {
    "fUSD": 1000,
    "fBTC": 0.1,
    "fETH": 1,
}

MIN_FUNDING_AMOUNT = {
    "fUSD": 50,
    "fETH": 0.5,
    "fBTC": 0.01,
}


def get_initial_start_data(
    currency: str, table_name: Optional[str], logger: logging.Logger
) -> Optional[FundingData]:
    if table_name:
        aws_context = boto3.resource("dynamodb", region_name="ap-southeast-2")
        try:
            initial_balance_data = aws_context.Table(table_name).get_item(
                Key={"Key": currency}
            )

            return FundingData(
                date=dt.datetime.strptime(
                    initial_balance_data["Item"]["Date"], "%m-%d-%Y"
                ).date(),
                initial_balance=float(initial_balance_data["Item"]["InitialBalance"]),
            )
        except ClientError as e:
            logger.debug(f"Failed to fetch balance for {currency}")
            return None
        except NoCredentialsError:
            logger.debug("No AWS Credential Setup")
            return None

    return None


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
        self._available_fundings: Dict[str, float] = dict()
        self._initial_balance = {
            currency: get_initial_start_data(
                currency, configuration.get_dynamodb_table_name(), logger
            )
            or FundingData(
                date=configuration.get_funding_start_date()
                if configuration.get_funding_start_date() is not None
                else dt.datetime.now().date(),
                initial_balance=configuration.get_initial_balance()[currency],
            )
            for currency in configuration.get_funding_currencies()
        }

    def get_initial_balance(self, currency: str) -> FundingData:
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
            [active_funding.amount for active_funding in self.get_active_funding_data()]
        )

    def _repopulate_pending_amount(self):
        self._current_pending_amount = sum(
            [pending_offer.amount for pending_offer in self.get_pending_funding()]
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

    def generate_lending_offer(
        self, currency: str, offer_rate: float
    ) -> Optional[LendingOffer]:
        if self.get_funding_for_offer(currency) >= MIN_FUNDING_AMOUNT[currency]:
            days = 2
            if offer_rate * 36500 > 30:
                days = 30
            elif offer_rate * 36500 > 25:
                days = 20
            elif offer_rate * 36500 > 20:
                days = 10
            elif offer_rate * 36500 > 15:
                days = 5

            amount = self.get_funding_for_offer(currency)

            if amount / MIN_FUNDING_AMOUNT[currency] > 2 and offer_rate * 36500 < 15:
                amount = MIN_FUNDING_AMOUNT[currency]

            amount_str = ("%.6f" % abs(amount))[
                :-1
            ]  # Truncate at 5th decimal places to avoid rounding error

            return LendingOffer(
                currency=currency, amount=amount_str, rate=offer_rate, period=days,
            )

        return None

    def regenerate_lending_offer(
        self, currency: str, offer_rate: float, funding_amount: str
    ) -> Optional[LendingOffer]:
        if float(funding_amount) >= MIN_FUNDING_AMOUNT[currency]:
            days = 2
            if offer_rate * 36500 > 30:
                days = 30
            elif offer_rate * 36500 > 25:
                days = 20
            elif offer_rate * 36500 > 20:
                days = 10
            elif offer_rate * 36500 > 15:
                days = 5

            amount = float(funding_amount)

            if amount / MIN_FUNDING_AMOUNT[currency] > 2 and offer_rate * 36500 < 15:
                amount = MIN_FUNDING_AMOUNT[currency]

            amount_str = ("%.6f" % abs(amount))[
                :-1
            ]  # Truncate at 5th decimal places to avoid rounding error

            return LendingOffer(
                currency=currency, amount=amount_str, rate=offer_rate, period=days,
            )

        return None
