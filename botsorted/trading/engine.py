"""
The main loop that consumes signals from a model
and supplies the model with data via a callback
"""
import os, sys
import pandas as pd
import datetime
import time


from ..logger import get_logger
from ..ml.dr import DirectReinforcementModel
from .cli import TradingClient
from ..config import config
from ..models import Symbol
from ..db import Session, FtScores
import requests

log = get_logger(__name__)


class TradingEngineException(Exception):
    pass


class TradingEngine(object):

    """
    Main trading loop for Autoregression-based agents
    Contains method of callback for data and signals

    All variables will be picked from the database to ensure persistence
    across sessions
    """

    def __init__(
        self,
        model_path: str = config["modelLocation"],
        sym: Symbol = Symbol(base="BTC", quote="USDT"),
    ):
        self.model = DirectReinforcementModel.from_json(model_path)
        self.model_path = model_path
        log.info(f"Loaded model: {self.model_path}")
        self.client = TradingClient()
        self.sym = sym

    def run_trading_loop(self):

        next_poll_time = None
        log.info(f"Entering trading loop")
        while True:
            log.debug("Fetching candles")
            df = self.client.df_candles(self.sym, interval=config["interval"])
            log.debug(f"got {len(df)} candles")
            close_price_series = df["close"].astype(float)
            # log.info(close_price_series)
            last_index = df.index[
                -2
            ]  # it's two because the current one is an open window
            last_close = (
                df["closeTime"][last_index] / 1000
            )  # accoutn for multiplied timestamps

            log.debug(f"{last_close=}")
            log.info(
                f"last_close in iso: {datetime.datetime.fromtimestamp(last_close).isoformat()}"
            )
            next_poll_time = last_close + config["validIntervals"][config["interval"]]
            log.debug(f"{next_poll_time=}")
            log.info(
                f"next_poll_time in iso: {datetime.datetime.fromtimestamp(next_poll_time).isoformat()}"
            )

            # exe strat
            if config['execute_strat']:
                self.futures_strategy(close_price_series)
            last_ping = time.time()
            while (
                time.time() < next_poll_time + 10
            ):  # plus 10 to allow for candle update on Binance
                log.debug(
                    f"Waiting next poll time at {datetime.datetime.fromtimestamp(next_poll_time+10)}"
                )
                log.debug(f"Last checked: {datetime.datetime.now().isoformat()}")

                # say hello to stay alive
                if time.time() - last_ping > 300:
                    # nearly 30 mins ago so ping the server
                    if os.environ["DEPLOY_ENV"] == "HEROKU":
                        last_ping = time.time()
                        requests.get("https://botsorted.herokuapp.com/ping")

                time.sleep(config["sleepInterval"])

    def futures_strategy(self, close_price_series: pd.Series):
        log.info("Checking for signal")
        signal, Ft = self.model.get_signal(close_price_series)
        log.info(f"{Ft=}")
        log.info(f"{signal=}")
        last_index = close_price_series.index[-1]
        current_price = close_price_series[last_index]

        # work out what position we already have
        current_position = self.client.get_current_position(self.sym.conc())

        if signal == "BUY" and current_position != "long":
            log.info(f"OPENING POSITION: long from {current_position}")

            if current_position:
                # close existing short
                log.info("Closing short position")
                self.try_call(
                    0, "CLOSE POSITION", self.client.close_position, self.sym.conc()
                )

            log.info("Opening long position")
            self.try_call(0, "OPEN LONG", self.client.open_long, self.sym)
            log.info("TRADE COMPLETED SUCCESSFULLY")

        elif signal == "SELL" and current_position != "short":
            log.info(f"OPENING POSITION: short from {current_position}")

            if current_position:
                # close existing long
                log.info("Closing long position")
                self.try_call(
                    0, "CLOSE POSITION", self.client.close_position, self.sym.conc()
                )

            log.info("Opening short position")
            self.try_call(0, "OPEN SHORT", self.client.open_short, self.sym)

            log.info("TRADE COMPLETED SUCCESSFULLY")
        else:
            log.info(f"Holding current {current_position} position")

        # log values to db
        try:
            sess = Session()
            row = FtScores(
                modelId=self.model_path,
                timeLogged=datetime.datetime.now(),
                signalIssued=signal,
                ftValue=round(Ft, 15),
                currentPrice=round(current_price, 2),
            )
            sess.add(row)
            sess.commit()
            sess.close()
        except Exception:
            log.error(f"Failed to save {signal=} with Ft={round(Ft,15)} to db.")

    def try_call(self, try_no, action_msg: str, method, *args, **kwargs):
        if try_no > config["tradeCallMaxRetries"]:
            log.error("TOTAL FAIL - abandoning")
            raise TradingEngineException(f"Could not execute {action_msg}")
        resp = method(*args, **kwargs)
        if not (resp.status_code > 199 and resp.status_code < 300):
            log.error(f"{action_msg} FAILED - api return: {resp.json()}")
            log.error("Trying again")

            try_no += 1
            time.sleep(config["tradeCallWaitTimeSeconds"])
            return self.try_call(try_no, action_msg, method, *args, **kwargs)
        else:
            log.info(f"{action_msg} SUCCESS - api returned: {resp.json()}")
            return True

    def buy_spot_strategy(self, close_price_series: pd.Series):
        raise NotImplementedError

    # data methods
    @staticmethod
    def get_ft_scores(as_df=False):
        sess = Session()
        q = sess.query(FtScores)
        if as_df:
            return pd.read_sql(q.statement, q.session.bind)
        else:
            return q.all()
