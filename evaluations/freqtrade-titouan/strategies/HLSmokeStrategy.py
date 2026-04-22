# Minimal HL testnet smoke strategy for Freqtrade-titouan Trial A.
# Goal: exercise the HL exchange module + the fork's _handle_external_close path.
# NOT a strategy to ship — this is a diagnostic runner.

from datetime import datetime
from typing import Optional

from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import IStrategy


class HLSmokeStrategy(IStrategy):
    INTERFACE_VERSION = 3
    can_short: bool = False
    timeframe = "5m"
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    startup_candle_count: int = 30

    minimal_roi = {"0": 0.002}  # 20 bps TP — small, quick turnover for smoke test
    stoploss = -0.03  # 300 bps SL — generous, we're not optimizing for PnL

    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 35) & (dataframe["ema_fast"] > dataframe["ema_slow"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi"] > 65, "exit_long"] = 1
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> float:
        return 1.0
