# pragma pylint: disable=missing-docstring, invalid-name
from freqtrade.strategy import IStrategy
import pandas as pd
import talib.abstract as ta


class VwapDmiScalpStrategy(IStrategy):

    INTERFACE_VERSION = 3

    timeframe = '1m'   # switch to '5m' if too noisy
    can_short = True

    minimal_roi = {
        "0": 0.02,
        "10": 0.01,
        "30": 0
    }

    stoploss = -0.03

    use_custom_stoploss = True
    use_custom_exit = True

    startup_candle_count = 200

    # === SCALPING PARAMETERS ===
    adx_threshold = 15        # lower = more trades
    atr_multiplier = 1.2      # tighter SL
    rr_ratio = 1.5            # faster TP
    vwap_window = 50          # faster VWAP
    rsi_entry = 35

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:

        # === FAST VWAP ===
        window = self.vwap_window
        tp = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        vol = dataframe['volume']

        dataframe['vwap'] = (tp * vol).rolling(window).sum() / vol.rolling(window).sum()

        # === DMI / ADX ===
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)

        # === ATR ===
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # === RSI (adds trade frequency) ===
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # === Momentum filter (simple) ===
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=21)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:

        # === LONG (loosened conditions) ===
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['vwap'] * 0.998) &  # zone, not strict cross
                (dataframe['plus_di'] > dataframe['minus_di']) &
                (dataframe['adx'] > self.adx_threshold) &
                (dataframe['rsi'] < 55) &   # allows more entries
                (dataframe['ema_fast'] > dataframe['ema_slow'])
            ),
            'enter_long'] = 1

        # === SHORT ===
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['vwap'] * 1.002) &
                (dataframe['minus_di'] > dataframe['plus_di']) &
                (dataframe['adx'] > self.adx_threshold) &
                (dataframe['rsi'] > 45) &
                (dataframe['ema_fast'] < dataframe['ema_slow'])
            ),
            'enter_short'] = 1

        return dataframe

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        candle = dataframe.iloc[-1]

        atr = candle['atr']

        if trade.is_short:
            stop_price = trade.open_rate + (self.atr_multiplier * atr)
            return (stop_price - current_rate) / current_rate
        else:
            stop_price = trade.open_rate - (self.atr_multiplier * atr)
            return (stop_price - current_rate) / current_rate

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        candle = dataframe.iloc[-1]

        atr = candle['atr']

        # === TAKE PROFIT (faster RR) ===
        if trade.is_short:
            risk = (trade.open_rate + (self.atr_multiplier * atr)) - trade.open_rate
            target = trade.open_rate - (risk * self.rr_ratio)

            if current_rate <= target:
                return "tp_hit"

        else:
            risk = trade.open_rate - (trade.open_rate - (self.atr_multiplier * atr))
            target = trade.open_rate + (risk * self.rr_ratio)

            if current_rate >= target:
                return "tp_hit"

        # === EARLY EXIT (key for scalping) ===
        if current_profit > 0.005:  # ~0.5%
            if trade.is_short and candle['plus_di'] > candle['minus_di']:
                return "momentum_flip"
            if not trade.is_short and candle['minus_di'] > candle['plus_di']:
                return "momentum_flip"

        return None