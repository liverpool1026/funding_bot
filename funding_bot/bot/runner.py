import time
import logging

import datetime as dt

from collections import defaultdict

from funding_bot.configs.myconfig import AccountConfiguration
from funding_bot.bot.funding import FundingBot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MIN_FUNDING_AMOUNT = {
    "fUSD": 50,
    "fETH": 0.5,
}

CURRENCIES = ["fUSD", "fETH"]


def runner():
    start_time = dt.datetime.now().timestamp()
    last_report_date = dt.datetime.now().date()
    bot = FundingBot(AccountConfiguration(), logger)
    last_available_funding = defaultdict(float)
    current_available_funding = defaultdict(float)

    while True:
        for currency in CURRENCIES:
            current_available_funding[currency] = bot.grab_available_funding(currency=currency)
            if current_available_funding[currency] > MIN_FUNDING_AMOUNT[currency]:
                # TODO Got available funding, time to lend it out
                if current_available_funding[currency] != last_available_funding[currency]:
                    bot.send_telegram_notification(f"{currency} Available Funding: {current_available_funding[currency]}")
                    last_available_funding[currency] = current_available_funding[currency]

        # Send a daily report
        if dt.datetime.now().date() != last_report_date:
            last_report_date = dt.datetime.now().date()
            bot.generate_report(CURRENCIES)
        time.sleep(30)  # RESTful API has connection limits, consider switch to Websocket


__all__ = [
    "runner",
]