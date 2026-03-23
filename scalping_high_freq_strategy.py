
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class ScalpingHighFreq(IStrategy):
    timeframe = '5m'
    can_short = True

    stoploss = -0.015

    minimal_roi = {
        "0": 0.015,
        "10": 0.01,
        "30": 0.005
    }

    process_only_new_candles = False
    startup_candle_count = 120

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 35) &
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['volume'] > dataframe['volume_mean'])
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 60)
            ),
            'exit_long'] = 1
        return dataframe
