import json
import logging
import requests

from typing import List, NamedTuple


class RateData(NamedTuple):
    flash_return_rate: float
    bid: float
    bid_period: int
    ask: float
    ask_period: int
    last: float
    high: float
    low: float


class CandleData(NamedTuple):
    high: float
    low: float
    open: float
    close: float


class Tracker(object):
    def __init__(self, currency: str, logger: logging.Logger):
        self._logger = logger
        self._currency = currency
        self._rate_data: List[RateData] = []
        self._current_rate_data: RateData = RateData(
            flash_return_rate=0.0, bid=0.0, ask=0.0, last=0.0, high=0.0, low=0.0, bid_period=0, ask_period=0
        )
        self._candle_data: CandleData = CandleData(high=0, low=0, open=0, close=0)

    def get_api(self) -> str:
        return f"https://api-pub.bitfinex.com/v2/tickers?symbols={self._currency}"

    def get_candle_api(self, period: int, duration: int) -> str:
        return f"https://api-pub.bitfinex.com/v2/candles/trade:{duration}m:{self._currency}:p{period}/last"

    def update_rates(self):
        response = requests.get(self.get_api())
        if response.status_code == 200:
            value = json.loads(response.content.decode())

            self._rate_data.append(
                RateData(
                    flash_return_rate=value[0][1],
                    bid=value[0][2],
                    bid_period=value[0][3],
                    ask=value[0][5],
                    ask_period=value[0][6],
                    last=value[0][10],
                    high=value[0][12],
                    low=value[0][13],
                )
            )

            if len(self._rate_data) == 15:
                self.aggregate_rate_data()

        # Update candle data
        response = requests.get(self.get_candle_api(duration=5, period=2))
        if response.status_code == 200:
            value = json.loads(response.content.decode())

            if value:
                self._candle_data = CandleData(
                    open=value[1],
                    close=value[2],
                    high=value[3],
                    low=value[4],
                )

    def get_latest_rate_data(self) -> RateData:
        return self._current_rate_data

    def get_candle_data(self) -> CandleData:
        return self._candle_data

    def aggregate_rate_data(self):
        # TODO need to store data in db
        self._current_rate_data = RateData(
            flash_return_rate=self._rate_data[-1].flash_return_rate,
            bid=self._rate_data[-1].bid,
            bid_period=self._rate_data[-1].bid_period,
            ask=self._rate_data[-1].ask,
            ask_period=self._rate_data[-1].ask_period,
            last=self._rate_data[-1].last,
            high=min([data.high for data in self._rate_data]),
            low=max([data.low for data in self._rate_data]),
        )

        self._rate_data = []

        self._logger.info(
            f"Current Rate Data:\n"
            f"FRR: {self._current_rate_data.flash_return_rate}\n"
            f"Bid: {self._current_rate_data.bid} for {self._current_rate_data.bid_period} days\n"
            f"Ask: {self._current_rate_data.ask} for {self._current_rate_data.ask_period} days\n"
            f"Last: {self._current_rate_data.last}\n"
            f"High: {self._current_rate_data.high}\n"
            f"Low: {self._current_rate_data.low}"
        )

    def determine_offer_rate(self) -> float:
        # Determines lending offer rate
        candle_data: CandleData = self.get_candle_data()
        rate_data: RateData = self.get_latest_rate_data()

        return candle_data.high * 0.98  # Return the high in the 5 minutes


