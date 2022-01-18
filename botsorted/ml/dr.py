"""
Implementation of a direct reinforcement learning model using
autoregressive parameters for cryptocurrencies for the Botsorted engine.

Main algorithm implemented is based on work by Koker and 
Koutmos 2020:
@article{koker2020cryptocurrency,
  title={Cryptocurrency Trading Using Machine Learning},
  author={Koker, Thomas E and Koutmos, Dimitrios},
  journal={Journal of Risk and Financial Management},
  volume={13},
  number={8},
  pages={178},
  year={2020},
  publisher={Multidisciplinary Digital Publishing Institute}
}

"""
from typing import Iterable, Tuple, Optional
import json
import numpy as np
import pandas as pd
import datetime


class DirectReinforcementModel(object):
    def __init__(self, **kwargs):

        for k, v in kwargs.items():
            setattr(self, k, v)

    def load_initial_data(self, srs: pd.Series) -> None:
        """
        Initial data that the model is loaded with to baseline
        its Ft calcs before being used for predictions
        """

        assert len(srs) >= len(self.theta), (
            f"X input series must be longer than current theta"
            f" values. Got {len(srs)} but expected >={len(self.theta)}"
        )
        assert not self.theta is None, (
            f"Theta value not set. Model must be trained"
            "before being initialised for making predictions"
        )

        # preprocess
        self.X = self.get_x(srs)
        self.Ft = self.calc_Ft(self.X, self.theta)

    def get_signal(self, close_price_series: pd.Series) -> Tuple[str, float]:
        """
        main method that will give a long/short signal

        :returns:
        - signal: str: BUY or SELL
        - ftValue: float: Ft value attributed to the prediction
        """
        assert not self.theta is None, (
            f"Theta value not set. Model must be trained"
            "before being initialised for making predictions"
        )

        X = self.get_x(close_price_series)
        FtArr = self.calc_Ft(X, self.theta)
        Ft = FtArr[-1]
        if Ft < 0:
            sig = "SELL"
        else:
            sig = "BUY"
        return sig, Ft

    def save_model(self, filepath: str):
        model_data = self.__dict__

        # set nparrays to list
        model_data = {
            k: (list(v) if isinstance(v, np.ndarray) else v)
            for k, v in model_data.items()
        }
        model_data = {
            k: (list(v) if isinstance(v, pd.Series) else v)
            for k, v in model_data.items()
        }
        with open(filepath, "w") as f:
            f.write(json.dumps(model_data))

    @classmethod
    def from_json(cls, json_path: str):
        with open(json_path, "r") as f:
            jsonStr = f.read()
        data = json.loads(jsonStr)

        # set back to nparrrays
        data = {k: (np.array(v) if isinstance(v, list) else v) for k, v in data.items()}
        # print(data.keys())
        # if to keep backwards compat
        if "train_series" in data.keys():
            data["train_series"] = pd.Series(data["train_series"])
        return cls(**data)

    # making static to remove state from single calcs
    @staticmethod
    def calc_Ft(x, theta):
        M = len(theta) - 2
        T = len(x)
        Ft = np.zeros(T)
        for t in range(M, T):
            xt = np.concatenate([[1], x[t - M : t], [Ft[t - 1]]])
            Ft[t] = np.tanh(np.dot(theta, xt))
        return Ft

    @staticmethod
    def returns(Ft, x, delta):
        T = len(x)
        rets = Ft[0 : T - 1] * x[1:T] - delta * np.abs(Ft[1:T] - Ft[0 : T - 1])
        return np.concatenate([[0], rets])

    def get_x(
        self,
        series: pd.Series,
        train_test_split: bool = False,
        N: int = None,
        P: int = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        rets = series.diff()[1:]
        x = np.array(rets)
        if train_test_split:
            x_train = x[-(N + P) : -P]  # pylint: disable=invalid-unary-operand-type
            x_test = x[-P:]  # pylint: disable=invalid-unary-operand-type
            self.std = np.std(x_train)
            self.mean = np.mean(x_train)
            x_train = (x_train - self.mean) / self.std
            x_test = (x_test - self.mean) / self.std
            return x_train, x_test
        else:
            assert not self.mean is None and not self.std is None, (
                f"Train mean and std values not set"
                "Model must be trained before making predictions"
            )
            x = (x - self.mean) / self.std
        return x

    def gradient(self, x, theta, delta):
        Ft = self.calc_Ft(x, theta)
        R = self.returns(Ft, x, delta)
        T = len(x)
        M = len(theta) - 2

        A = np.mean(R)
        B = np.mean(np.square(R))
        S = A / np.sqrt(B - A ** 2)

        dSdA = S * (1 + S ** 2) / A
        dSdB = -(S ** 3) / 2 / A ** 2
        dAdR = 1.0 / T
        dBdR = 2.0 / T * R

        grad = np.zeros(M + 2)  # initialize gradient
        dFpdtheta = np.zeros(M + 2)  # for storing previous dFdtheta

        for t in range(M, T):
            xt = np.concatenate([[1], x[t - M : t], [Ft[t - 1]]])
            dRdF = -delta * np.sign(Ft[t] - Ft[t - 1])
            dRdFp = x[t] + delta * np.sign(Ft[t] - Ft[t - 1])
            dFdtheta = (1 - Ft[t] ** 2) * (xt + theta[-1] * dFpdtheta)
            dSdtheta = (dSdA * dAdR + dSdB * dBdR[t]) * (
                dRdF * dFdtheta + dRdFp * dFpdtheta
            )
            grad = grad + dSdtheta
            dFpdtheta = dFdtheta

        return grad, S

    def train(
        self,
        train_series: pd.Series,
        train_date_series: pd.Series,
        train_dataset_name: str,
        epochs=2500,
        M=15,
        commission=0.001,
        learning_rate=0.3,
        N=1000,
        P=200,
        seed=0,
        usingIpy=True,
    ):
        if usingIpy:
            from IPython.display import clear_output
        np.random.seed(seed)
        self.train_series = train_series
        self.x_train, self.x_test = self.get_x(
            train_series, train_test_split=True, N=N, P=P
        )
        theta = np.random.rand(M + 2)

        sharpes = np.zeros(epochs)  # store sharpes over time
        for it, i in enumerate(range(epochs)):
            if usingIpy:
                clear_output(wait=True)
            grad, sharpe = self.gradient(self.x_train, theta, commission)
            theta = theta + grad * learning_rate

            sharpes[i] = sharpe
            print(f"Training...{it+1} of {epochs} epochs")

        print("Finished training")
        self.theta = theta
        self.sharpes = sharpes
        self.N = N
        self.P = P
        self.epochs = epochs
        self.M = M
        self.commission = commission
        self.learning_rate = learning_rate
        self.train_date_series = train_date_series
        self.train_dataset_name = train_dataset_name

    def sharpe_ratio(self, rets):
        return rets.mean() / rets.std()

    def test_set_futures_simulation(
        self, test_data: pd.Series = pd.Series(), save=False
    ):

        portfolio_start_funds = 1000  # USD

        current_balance = portfolio_start_funds
        current_btc_balance = 0

        test_start = datetime.datetime.now()
        buy_data = pd.DataFrame()
        if test_data.empty:
            buy_data["close"] = self.train_series.tail(self.P).reset_index(drop=True)
        else:
            buy_data["close"] = test_data.reset_index(drop=True)
        total_intervals = len(buy_data)
        start_price = buy_data["close"][0]
        buy_hold_start_btc = (current_balance / start_price) * (1 - self.commission)

        long_btc_amount = 0
        short_btc_amount = 0
        purchased_usd = 0

        isLong = False
        isShort = False

        trading_start_index = len(self.theta) + 2
        for i in range(trading_start_index, total_intervals):

            close_price_series = buy_data["close"][: i + 1]

            signal, Ft = self.get_signal(close_price_series)

            current_price = buy_data["close"][
                i - 1
            ]  # close price of the last interval is the
            # open of this interval

            if signal == "BUY" and not isLong:
                if isShort:
                    # currently holding a short position, this must be closed out
                    # in a short scenario, btc is borrowed and used to purchase
                    # USD, so on the long signal we buy back btc by using all our
                    # originally purchased USD to buy BTC.
                    # We then subtract the original BTC amount from the new btc
                    # and add the remainder to our BTC balance
                    # by substracting the original purchase from the current value

                    # buy back btc
                    win_los_btc = (purchased_usd / current_price) * (
                        1 - self.commission
                    )

                    # get remainder of btc and add to balance
                    remainder = win_los_btc - short_btc_amount
                    current_btc_balance += remainder

                    short_btc_amount = 0

                    isShort = False
                buy_data.loc[i, "buy_strat_test"] = "Bought"
                long_btc_amount = (current_balance / current_price) * (
                    1 - self.commission
                )

                # add btc to balance
                current_btc_balance += long_btc_amount
                current_balance = 0
                isLong = True
            if signal == "SELL" and not isShort:
                if isLong:
                    # close out long trade and update balance
                    win_los = (current_price * current_btc_balance) * (
                        1 - self.commission
                    )
                    current_balance = win_los
                    long_btc_amount = 0
                    current_btc_balance = 0
                    isLong = False
                buy_data.loc[i, "buy_strat_test"] = "Sold"
                # take new short position for current balance value
                # remember this is borrowed and used to buy USD
                # so we'll put it in a new column to remember how much we borrowed
                # and add segregate the additional USD value in another bucket
                # to avoid affecting overall portfolio balance.
                # The value is calculated from the current closing price
                short_btc_amount = (current_balance / current_price) * (
                    1 - self.commission
                )
                purchased_usd = current_price * short_btc_amount
                isShort = True

            # either way log balance
            buy_data.loc[i, "ft_val"] = Ft
            buy_data.loc[i, "usd balance"] = current_balance
            buy_data.loc[i, "btc balance"] = current_btc_balance

            # log MTM values
            if isShort:
                buy_data.loc[i, "Quarantined USD on short"] = purchased_usd
                buy_data.loc[i, "short BTC value"] = purchased_usd / current_price
                buy_data.loc[i, "short USD value"] = (
                    purchased_usd / current_price
                ) * current_price
            if isLong:
                buy_data.loc[i, "long USD value"] = current_price * current_btc_balance

            buy_data.loc[i, "portfolio USD value"] = (
                current_price * current_btc_balance
            ) + current_balance
            buy_data.loc[i, "portfolio BTC value"] = current_btc_balance + (
                current_balance / current_price
            )
            print(f"Cycling {i}--> {signal}")
        # tot up
        final_price = current_price

        # force model market exit to tot up open positions
        if isLong:
            buy_data.loc[i, "buy_strat_test"] = "Sold"
            win_los = (current_price * long_btc_amount) * (1 - self.commission)
            current_balance = win_los
            isLong = False
        if isShort:
            buy_data.loc[i, "buy_strat_test"] = "Bought"
            # buy back btc
            win_los_btc = (purchased_usd / current_price) * (1 - self.commission)

            # get remainder of btc and add to balance
            remainder = win_los_btc - short_btc_amount
            current_btc_balance += remainder

            # convert btc to use for final tot
            current_balance += current_btc_balance * current_price
            short_btc_amount = 0

            isShort = False

        buy_and_hold_gains = (final_price * buy_hold_start_btc) * (1 - self.commission)
        print(f"Model total gains: {current_balance}")
        print(f"Buy/Hold total gains: {buy_and_hold_gains}")
        return buy_data
