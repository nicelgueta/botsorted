import pandas as pd
from typing import List, Any
import os, sys
import datetime

from ..binance.futures import FuturesClient
from ..binance.conn import USE_LIVE, make_request

from ..logger import get_logger

from ..config import config
from ..models import Symbol

log = get_logger(__name__)


class TradingClientException(Exception):
    pass


# #temp: throw error if not using test version
# if USE_LIVE:
#     raise TradingClientException('Not ready to run for real. Stay in test mode')


class TradingClient(FuturesClient):
    def __init__(self):
        super().__init__()

    def get_non_margin_cash_balance(self) -> float:
        ac = self.account().json()
        # log.debug(ac)
        return float(ac["totalMarginBalance"])

    def get_total_balance(self, asset) -> float:
        bal = self.balance().json()
        try:
            ac = [a for a in bal if a["asset"] == asset][0]
        except IndexError:
            m = f'Asset "{asset}" not found in account balances'
            log.error(m)
            raise TradingClientException(m)
        return float(ac["balance"])

    def open_long(self, sym: Symbol):
        """
        This method deliberately has no parameters as it assumes control
        over the whole account.
        It works out the required params for order and makes the order
        """
        if sym.quote != "USDT":
            raise NotImplementedError("Not ready to trade any other quote than usdt")

        total_quote = self.get_non_margin_cash_balance()

        # make sure to only take up to the maxmium allowed for trading
        tradable_usdt = min([config["maxTradeSizeUSDT"], total_quote])

        px = self.get_price(sym)
        base_qty = self.get_base_qty(tradable_usdt, px)
        base_qty = round(base_qty, config["quantityPrecision"])
        return self.new_order(sym.conc(), "BUY", base_qty)

    def open_short(self, sym: Symbol):
        """
        This method deliberately has no parameters as it assumes control
        over the whole account.
        It works out the required params for order and makes the order.
        """
        if sym.quote != "USDT":
            raise NotImplementedError("Not ready to trade any other quote than usdt")

        # amount order must be no bigger than what we can cover in initial margin
        total_quote = self.get_non_margin_cash_balance()

        # make sure to only take up to the maxmium allowed for trading
        tradable_usdt = min([config["maxTradeSizeUSDT"], total_quote])

        px = self.get_price(sym)
        base_qty = self.get_base_qty(tradable_usdt, px)
        base_qty = round(base_qty, config["quantityPrecision"])
        return self.new_order(sym.conc(), "SELL", base_qty)

    def df_candles(
        self,
        sym: Symbol,
        interval: str = "1d",
        limit: int = 500,
        startTime: int = None,
        endTime: int = None,
    ) -> pd.DataFrame:
        resp = self.get_candles(
            symbol=sym.conc(),
            interval=interval,
            limit=limit,
            startTime=startTime,
            endTime=endTime,
        )
        try:
            df = pd.DataFrame(resp.json())
        except ValueError as e:
            raise TradingClientException(
                (
                    f"::Failed getting candles::"
                    f"Could not create df from json response. "
                    f"Api returned: {resp.json()}"
                )
            )
        df.columns = config["candleColumns"]

        # binance uses milliseconds
        df["openTimeIso"] = [
            datetime.datetime.fromtimestamp(t / 1000).isoformat()
            for t in df["openTime"]
        ]
        df["closeTimeIso"] = [
            datetime.datetime.fromtimestamp(t / 1000).isoformat()
            for t in df["closeTime"]
        ]
        return df

    def get_position_details(self, sym: Symbol):
        ac = self.account().json()
        return [p for p in ac["positions"] if p["symbol"] == sym.conc()][0]

    def get_price(self, sym: Symbol):
        return float(self.mark_price(sym.conc()).json()["markPrice"])

    def get_quote_qty(self, base_qty: float, px: float) -> dict:
        return base_qty * px

    def get_base_qty(self, quote_qty: float, px: float) -> dict:
        log.debug(f"Raw base qty: {(quote_qty/px)}")
        baseQty = (quote_qty / px) * config["tradeMarginRatio"]
        log.debug(f"{baseQty=}")
        return baseQty
