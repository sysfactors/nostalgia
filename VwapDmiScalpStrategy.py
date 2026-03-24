# File: VwapDmiScalpStrategy.py
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class VwapDmiScalpStrategy(IStrategy):
    # --- STRATEGY SETTINGS ---
    timeframe = '5m'
    stoploss = -0.03
    minimal_roi = {"0": 0.02}  # take 2% profit immediately
    startup_candle_count: int = 20
    leverage = 10  # futures leverage

    # Use dynamic stake sizing to prevent 30% ignore issue
    stake_amount = 50
    stake_currency = 'USDT'
    tradable_balance_ratio = 0.99

    # Optional: limit number of trades
    max_open_trades = 5

    # --- INDICATORS ---
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # VWAP
        dataframe['vwap'] = ta.SMA(dataframe['close'], timeperiod=14)

        # DMI
        dataframe['plus_di'] = ta.PLUS_DI(dataframe)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe)
        dataframe['adx'] = ta.ADX(dataframe)

        return dataframe

    # --- ENTRY RULES ---
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['buy'] = 0
        dataframe['sell'] = 0

        # Buy: price above VWAP, ADX > 20, +DI > -DI
        buy_condition = (
            (dataframe['close'] > dataframe['vwap']) &
            (dataframe['adx'] > 20) &
            (dataframe['plus_di'] > dataframe['minus_di'])
        )
        dataframe.loc[buy_condition, 'buy'] = 1

        # Sell: price below VWAP, ADX > 20, -DI > +DI
        sell_condition = (
            (dataframe['close'] < dataframe['vwap']) &
            (dataframe['adx'] > 20) &
            (dataframe['minus_di'] > dataframe['plus_di'])
        )
        dataframe.loc[sell_condition, 'sell'] = 1

        return dataframe

    # --- EXIT RULES ---
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

        # Exit long when price drops below VWAP
        dataframe.loc[dataframe['close'] < dataframe['vwap'], 'exit_long'] = 1

        # Exit short when price rises above VWAP
        dataframe.loc[dataframe['close'] > dataframe['vwap'], 'exit_short'] = 1

        return dataframe