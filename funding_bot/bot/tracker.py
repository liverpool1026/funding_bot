import json
import logging
import requests

from collections import namedtuple

from typing import List

RATE_DATA = namedtuple("RATE_DATE", ("FRR", "Bid", "Ask", "Last", "High", "Low"))


class Tracker(object):
    def __init__(self, currency: str, logger: logging.Logger):
        self._logger = logger
        self._currency = currency
        self._rate_data: List[RATE_DATA] = []
        self._current_rate_data: RATE_DATA = RATE_DATA(
            FRR=0, Bid=0, Ask=0, Last=0, High=0, Low=0
        )

    def get_api(self) -> str:
        return f"https://api-pub.bitfinex.com/v2/tickers?symbols={self._currency}"

    def update_rates(self):
        response = requests.get(self.get_api())
        if response.status_code == 200:
            value = json.loads(response.content.decode())

            self._rate_data.append(
                RATE_DATA(
                    FRR=value[0][1],
                    Bid=value[0][2],
                    Ask=value[0][5],
                    Last=value[0][10],
                    High=value[0][12],
                    Low=value[0][13],
                )
            )

            if len(self._rate_data) == 15:
                self.aggregate_rate_data()

    def get_latest_rate_data(self) -> RATE_DATA:
        return self._current_rate_data

    def aggregate_rate_data(self):
        FRR = 0
        bid = 0
        ask = 0
        last = 0
        high = 0
        low = 0

        for i in self._rate_data:
            FRR += i.FRR
            bid += i.Bid
            ask += i.Ask
            last += i.Last
            high += i.High
            low += i.Low

        # TODO need to store data in db
        self._current_rate_data = RATE_DATA(
            FRR=FRR / 15,
            Bid=bid / 15,
            Ask=ask / 15,
            Last=last / 15,
            High=high / 15,
            Low=low / 15,
        )

        self._rate_data = []

        self._logger.info(
            f"Current Rate Data: FRR: {self._current_rate_data.FRR} Bid: {self._current_rate_data.Bid} Ask: {self._current_rate_data.Ask} Last: {self._current_rate_data.Last} High: {self._current_rate_data.High} Low: {self._current_rate_data.Low}"
        )
