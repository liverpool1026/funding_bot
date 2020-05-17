import time
import logging

import datetime as dt

from collections import defaultdict

from funding_bot.configs.myconfig import AccountConfiguration
from funding_bot.bot.funding import FundingBot
from funding_bot.bot.tracker import Tracker

from typing import Dict


MIN_FUNDING_AMOUNT = {
    "fUSD": 50,
    "fETH": 0.5,
}

CURRENCIES = ["fUSD", "fETH"]


def get_runtime(start_time: float) -> str:
    seconds = dt.datetime.now().timestamp() - start_time
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return'{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))


def runner(logger: logging.Logger):
    start_time = dt.datetime.now().timestamp()
    run_hours = 0
    last_report_date = dt.datetime.now().date()
    bot = FundingBot(AccountConfiguration(), logger)
    last_available_funding = defaultdict(float)
    current_available_funding = defaultdict(float)
    trackers: Dict[str, Tracker] = dict()

    for currency in CURRENCIES:
        trackers[currency] = Tracker(currency=currency, logger=logger)

    while True:
        for currency in CURRENCIES:
            # Rate Tracker Update Rate
            tracker = trackers[currency]
            tracker.update_rates()

            # Check balance
            current_available_funding[currency] = bot.grab_available_funding(currency=currency)
            if current_available_funding[currency] > MIN_FUNDING_AMOUNT[currency]:
                if current_available_funding[currency] != last_available_funding[currency]:
                    bot.send_telegram_notification(f"{currency} Available Funding: {current_available_funding[currency]}")
                    logger.info(f"{currency} Available Funding: {current_available_funding[currency]}")
                    bot.submit_funding_offer(currency, tracker.get_latest_rate_data(), current_available_funding[currency])
                    current_available_funding[currency] = 0
            last_available_funding[currency] = current_available_funding[currency]

            # TODO Check offer taken

        # Send a daily report
        if dt.datetime.now().date() != last_report_date:
            last_report_date = dt.datetime.now().date()
            bot.send_telegram_notification(f"Summary Report @ {dt.datetime.now().date()}\n"
                                           f"Runtime: {get_runtime(start_time)}")
            logger.info(f"Summary Report @ {dt.datetime.now().date()}\n"
                                           f"Runtime: {get_runtime(start_time)}")
            bot.generate_report(CURRENCIES)

        if int((dt.datetime.now().timestamp() - start_time) / 3600) != run_hours:
            run_hours = int((dt.datetime.now().timestamp() - start_time) / 3600) != run_hours
            bot.send_telegram_notification(f"Summary Report @ {dt.datetime.now().date()}\n"
                                           f"Runtime: {get_runtime(start_time)}")
            logger.info(f"Summary Report @ {dt.datetime.now().date()}\n"
                        f"Runtime: {get_runtime(start_time)}")
            bot.generate_report(CURRENCIES)

        time.sleep(30)  # RESTful API has connection limits, consider switch to Websocket


__all__ = [
    "runner",
]