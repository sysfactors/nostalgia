# VwapDmiScalpStrategy.py
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class VwapDmiScalpStrategy(IStrategy):
    """
    1m / 5m scalping strategy using VWAP + DMI with x20 leverage.
    Increased trade frequency (~5x) by lowering thresholds.
    """
    # --- Strategy settings ---
    timeframe = '1m'
    minimal_roi = {"0": 0.015, "5": 0.01, "15": 0}
    stoploss = -0.03
    trailing_stop = False
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 20
    leverage = 20  # futures leverage

    # --- Leverage override for futures ---
    def customize_leverage(self, pair: str, current_leverage: float, max_leverage: float) -> float:
        return 20

    # --- Indicators ---
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # VWAP (simple moving average as proxy)
        dataframe['vwap'] = ta.SMA(dataframe['close'], timeperiod=14)
        # DMI components
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        return dataframe

    # --- Entry conditions ---
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['close'] > dataframe['vwap']) &
            (dataframe['adx'] > 20) &
            (dataframe['plus_di'] > dataframe['minus_di']),
            'buy'
        ] = 1

        dataframe.loc[
            (dataframe['close'] < dataframe['vwap']) &
            (dataframe['adx'] > 20) &
            (dataframe['minus_di'] > dataframe['plus_di']),
            'sell'
        ] = 1
        return dataframe

    # --- Exit conditions ---
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when price crosses opposite side of VWAP or trend weakens
        dataframe.loc[
            (dataframe['close'] < dataframe['vwap']) &
            (dataframe['plus_di'] < dataframe['minus_di']),
            'sell'
        ] = 1

        dataframe.loc[
            (dataframe['close'] > dataframe['vwap']) &
            (dataframe['minus_di'] < dataframe['plus_di']),
            'buy'
        ] = 1
        return dataframe