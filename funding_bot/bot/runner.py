import time
import logging

import datetime as dt

from collections import defaultdict

from funding_bot.configs.myconfig import AccountConfiguration
from funding_bot.bot.funding import FundingBot, Credentials
from funding_bot.bot.tracker import Tracker
from funding_bot.bot.account import Account, FundingData

from typing import Dict, List


def get_runtime(start_time: float) -> str:
    seconds = dt.datetime.now().timestamp() - start_time
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return str(dt.timedelta(hours=hours, minutes=minutes, seconds=seconds))


def runner(logger: logging.Logger):
    start_time = dt.datetime.now().timestamp()
    run_hours = 0
    bot = FundingBot
    funding_data_tracker = Account(AccountConfiguration(), logger)
    credentials = Credentials(
        api_key=AccountConfiguration.get_api_key(),
        api_secret_key=AccountConfiguration.get_api_secret_key(),
        telegram_api=AccountConfiguration.get_telegram_api(),
    )
    telegram_api_key = AccountConfiguration.get_telegram_api()
    rate_trackers: Dict[str, Tracker] = dict()
    submitted_orders: Dict[str, Dict[str, dt.datetime]] = defaultdict(dict)

    funding_currencies = AccountConfiguration.get_funding_currencies()

    for currency in funding_currencies:
        rate_trackers[currency] = Tracker(currency=currency, logger=logger)

    for i in range(20):
        # Need initial value
        for currency in funding_currencies:
            # Rate Tracker Update Rate
            rate_tracker = rate_trackers[currency]
            rate_tracker.update_rates()

    while True:
        for currency in funding_currencies:
            # Rate Tracker Update Rate
            rate_tracker = rate_trackers[currency]
            rate_tracker.update_rates()

            # Check balance
            funding_data_tracker.update_available_funding(
                currency=currency,
                amount=bot.grab_available_funding(
                    credentials=credentials, currency=currency, logger=logger,
                ),
            )
            funding_offer = funding_data_tracker.generate_lending_offer(
                currency, rate_tracker.determine_offer_rate()
            )
            if funding_offer:
                bot.send_telegram_notification(
                    telegram_api_key,
                    f"{currency} Available Funding for offer: {funding_offer.amount}",
                )
                logger.info(
                    f"{currency} Available Funding for offer: {funding_offer.amount}"
                )

                order = bot.submit_funding_offer(
                    credentials,
                    currency,
                    funding_offer,
                    funding_data_tracker.get_minimum_daily_lending_rate(currency),
                    logger,
                )

                if order:
                    submitted_orders[currency][str(order)] = dt.datetime.now()
                else:
                    bot.send_telegram_notification(
                        telegram_api_key,
                        f"Failed to submit {currency} order for {funding_offer.amount}",
                    )

            order_successfully_executed: List[str] = []
            if submitted_orders[currency]:
                historic_offer = bot.get_funding_offer_history(
                    credentials, currency, logger
                )

                for order_id in submitted_orders[currency]:
                    order_status = historic_offer.get(order_id, None)
                    if order_status:
                        message = f"Order: {order_id} {order_status}"
                        bot.send_telegram_notification(telegram_api_key, message)
                        logger.info(message)
                        order_successfully_executed.append(order_id)

            for order_id in order_successfully_executed:
                del submitted_orders[currency][order_id]

            order_successfully_deleted = []
            for submitted_order_id, submitted_time in submitted_orders[
                currency
            ].items():
                if dt.datetime.now() - submitted_time > dt.timedelta(hours=1):
                    message = f"Order: {submitted_order_id} yet to be executed"
                    bot.send_telegram_notification(telegram_api_key, message)
                    logger.info(message)

                    if bot.cancel_funding_offer(
                        credentials, submitted_order_id, logger
                    ):
                        order_successfully_deleted.append(submitted_order_id)

            for order_id in order_successfully_deleted:
                del submitted_orders[currency][order_id]

        if int((dt.datetime.now().timestamp() - start_time) / 3600) != run_hours:
            run_hours = int((dt.datetime.now().timestamp() - start_time) / 3600)
            message = (
                f"Summary Report @ {dt.datetime.now().date()}\n"
                f"Runtime: {get_runtime(start_time)}\n"
            )

            for currency in funding_currencies:
                current_balance: float = bot.get_currency_balance(
                    credentials, currency, logger
                )
                roi: float = 0
                gain: float = 0
                initial_balance_data: FundingData = funding_data_tracker.get_initial_balance(
                    currency
                )
                if current_balance != -1:
                    gain = current_balance - initial_balance_data.initial_balance
                    roi = (
                        365
                        * gain
                        / (dt.datetime.now().date() - initial_balance_data.date).days
                        / initial_balance_data.initial_balance
                    )

                message += f"\n{currency[1:]}: \n"
                message += f"Initial Balance: {initial_balance_data.initial_balance}\n"
                message += f"Start Date: {initial_balance_data.date}\n"
                message += f"Current Balance: {current_balance}\n"
                message += f"Gain: {gain} {currency[1:]}\n"
                message += f"ROI: {round(roi * 100, 2)} %\n"

            bot.send_telegram_notification(telegram_api_key, message)
            logger.info(message)

            bot.generate_report(credentials, funding_currencies, logger)

        time.sleep(5)  # RESTful API has connection limits, consider switch to Websocket


__all__ = [
    "runner",
]
