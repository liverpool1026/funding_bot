import time
import boto3
import logging

import datetime as dt

from collections import defaultdict, namedtuple
from botocore.exceptions import ClientError

from funding_bot.configs.myconfig import AccountConfiguration
from funding_bot.bot.funding import FundingBot
from funding_bot.bot.tracker import Tracker

from typing import Dict, List

FUNDING_DATA = namedtuple("FUNDING_DATA", ["Date", "InitialBalance"])

MIN_FUNDING_AMOUNT = {
    "fUSD": 50,
    "fETH": 0.5,
}

CURRENCIES = ["fUSD", "fETH"]


def get_runtime(start_time: float) -> str:
    seconds = dt.datetime.now().timestamp() - start_time
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return str(dt.timedelta(hours=hours, minutes=minutes, seconds=seconds))


def get_initial_start_data(
    currency: str, table_name: str, logger: logging.Logger
) -> FUNDING_DATA:
    aws_context = boto3.resource("dynamodb", region_name="ap-southeast-2")
    try:
        initial_balance_data = aws_context.Table(table_name).get_item(
            Key={"Key": currency}
        )
    except ClientError as e:
        logger.debug(f"Failed to fetch balance for {currency}")
        return FUNDING_DATA(Date=dt.datetime.now().date(), InitialBalance=1000,)
    else:
        return FUNDING_DATA(
            Date=dt.datetime.strptime(initial_balance_data["Item"]["Date"], "%m-%d-%Y"),
            InitialBalance=float(initial_balance_data["Item"]["InitialBalance"]),
        )


def runner(logger: logging.Logger):
    start_time = dt.datetime.now().timestamp()
    run_hours = 0
    bot = FundingBot(AccountConfiguration(), logger)
    last_available_funding = defaultdict(float)
    current_available_funding = defaultdict(float)
    trackers: Dict[str, Tracker] = dict()
    initial_data: Dict[str, FUNDING_DATA] = dict()
    submitted_order: Dict[str, List[str]] = defaultdict(list)

    for currency in CURRENCIES:
        trackers[currency] = Tracker(currency=currency, logger=logger)
        initial_data[currency] = get_initial_start_data(
            currency, AccountConfiguration.get_dynamodb_table_name(), logger=logger
        )
        if initial_data[currency].InitialBalance == 1000:
            # TODO update using wallet balance
            pass

    for i in range(20):
        # Need initial value
        for currency in CURRENCIES:
            # Rate Tracker Update Rate
            tracker = trackers[currency]
            tracker.update_rates()

    while True:
        for currency in CURRENCIES:
            # Rate Tracker Update Rate
            tracker = trackers[currency]
            tracker.update_rates()

            # Check balance
            current_available_funding[currency] = bot.grab_available_funding(
                currency=currency
            )
            if current_available_funding[currency] > MIN_FUNDING_AMOUNT[currency]:
                if (
                    current_available_funding[currency]
                    != last_available_funding[currency]
                ):
                    bot.send_telegram_notification(
                        f"{currency} Available Funding: {current_available_funding[currency]}"
                    )
                    logger.info(
                        f"{currency} Available Funding: {current_available_funding[currency]}"
                    )
                    submitted_order[currency].append(
                        str(
                            bot.submit_funding_offer(
                                currency,
                                tracker.get_latest_rate_data(),
                                current_available_funding[currency],
                            )
                        )
                    )
                    current_available_funding[currency] = 0
            last_available_funding[currency] = current_available_funding[currency]

            # TODO Check offer taken
            if submitted_order[currency]:
                for active_order in bot.get_active_funding_data(currency):
                    if active_order.ID in submitted_order[currency]:
                        message = f"Order: {active_order.ID} Amount: {active_order.Amount} Rate: {active_order.Rate} executed"
                        bot.send_telegram_notification(message)
                        logger.info(message)
                        submitted_order[currency].remove(active_order.ID)

        if int((dt.datetime.now().timestamp() - start_time) / 3600) != run_hours:
            run_hours = int((dt.datetime.now().timestamp() - start_time) / 3600)
            message: str = f"Summary Report @ {dt.datetime.now().date()}\n" f"Runtime: {get_runtime(start_time)}\n"

            for currency in CURRENCIES:
                current_balance: float = bot.get_currency_balance(currency)
                roi: float = 0
                gain: float = 0
                if current_balance != -1:
                    gain = current_balance - initial_data[currency].InitialBalance
                    roi = (
                        365
                        * gain
                        / (dt.datetime.now() - initial_data[currency].Date).days
                        / initial_data[currency].InitialBalance
                    )

                message += f"\n{currency[1:]}: \n"
                message += f"Initial Balance: {initial_data[currency].InitialBalance}\n"
                message += f"Start Date: {initial_data[currency].Date}\n"
                message += f"Current Balance: {current_balance}\n"
                message += f"Gain: {gain} {currency[1:]}\n"
                message += f"ROI: {round(roi * 100, 2)} %\n"

            bot.send_telegram_notification(message)
            logger.info(message)

            bot.generate_report(CURRENCIES)

        time.sleep(5)  # RESTful API has connection limits, consider switch to Websocket


__all__ = [
    "runner",
]
