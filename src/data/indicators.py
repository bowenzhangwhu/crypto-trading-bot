"""
技术指标计算模块
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
from config.settings import TRADE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        try:
            config = TRADE_CONFIG['technical_indicators']
            
            # 移动平均线
            for period in config['sma_periods']:
                df[f'sma_{period}'] = df['close'].rolling(
                    window=period, min_periods=1
                ).mean()
            
            # 指数移动平均线
            df['ema_12'] = df['close'].ewm(span=config['ema_fast']).mean()
            df['ema_26'] = df['close'].ewm(span=config['ema_slow']).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=config['macd_signal']).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(config['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(config['rsi_period']).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # 布林带
            df['bb_middle'] = df['close'].rolling(config['bb_period']).mean()
            bb_std = df['close'].rolling(config['bb_period']).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * config['bb_std'])
            df['bb_lower'] = df['bb_middle'] - (bb_std * config['bb_std'])
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # 成交量指标
            df['volume_ma'] = df['volume'].rolling(config['volume_ma_period']).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # 支撑阻力位
            df['resistance'] = df['high'].rolling(config['support_resistance_lookback']).max()
            df['support'] = df['low'].rolling(config['support_resistance_lookback']).min()
            
            # 填充NaN值
            df = df.bfill().ffill()
            
            return df
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return df
    
    @staticmethod
    def get_market_trend(df: pd.DataFrame) -> Dict[str, Any]:
        """判断市场趋势"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 多时间框架趋势分析
            trend_short = "上涨" if current_price > df['sma_20'].iloc[-1] else "下跌"
            trend_medium = "上涨" if current_price > df['sma_50'].iloc[-1] else "下跌"
            
            # MACD趋势
            macd_trend = "bullish" if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] else "bearish"
            
            # 综合趋势判断
            if trend_short == "上涨" and trend_medium == "上涨":
                overall_trend = "强势上涨"
            elif trend_short == "下跌" and trend_medium == "下跌":
                overall_trend = "强势下跌"
            else:
                overall_trend = "震荡整理"
            
            return {
                'short_term': trend_short,
                'medium_term': trend_medium,
                'macd': macd_trend,
                'overall': overall_trend,
                'rsi_level': float(df['rsi'].iloc[-1])
            }
            
        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            return {}
    
    @staticmethod
    def get_support_resistance_levels(df: pd.DataFrame, 
                                     lookback: int = None) -> Dict[str, Any]:
        """计算支撑阻力位"""
        try:
            if lookback is None:
                lookback = TRADE_CONFIG['technical_indicators']['support_resistance_lookback']
            
            recent_high = df['high'].tail(lookback).max()
            recent_low = df['low'].tail(lookback).min()
            current_price = df['close'].iloc[-1]
            
            # 动态支撑阻力（基于布林带）
            bb_upper = df['bb_upper'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            
            return {
                'static_resistance': float(recent_high),
                'static_support': float(recent_low),
                'dynamic_resistance': float(bb_upper),
                'dynamic_support': float(bb_lower),
                'price_vs_resistance': ((recent_high - current_price) / current_price) * 100,
                'price_vs_support': ((current_price - recent_low) / recent_low) * 100
            }
            
        except Exception as e:
            logger.error(f"支撑阻力计算失败: {e}")
            return {}
    
    @staticmethod
    def generate_analysis_text(price_data: Dict[str, Any]) -> str:
        """生成技术分析文本"""
        try:
            tech = price_data.get('technical_data', {})
            trend = price_data.get('trend_analysis', {})
            levels = price_data.get('levels_analysis', {})
            price = price_data.get('price', 0)
            
            def safe_float(value, default=0):
                return float(value) if value and not pd.isna(value) else default
            
            analysis_text = f"""
【技术指标分析】
移动平均线:
- 5周期: {safe_float(tech.get('sma_5')):.2f} | 价格相对: {(price - safe_float(tech.get('sma_5'))) / safe_float(tech.get('sma_5')) * 100:+.2f}%
- 20周期: {safe_float(tech.get('sma_20')):.2f} | 价格相对: {(price - safe_float(tech.get('sma_20'))) / safe_float(tech.get('sma_20')) * 100:+.2f}%
- 50周期: {safe_float(tech.get('sma_50')):.2f} | 价格相对: {(price - safe_float(tech.get('sma_50'))) / safe_float(tech.get('sma_50')) * 100:+.2f}%

趋势分析:
- 短期趋势: {trend.get('short_term', 'N/A')}
- 中期趋势: {trend.get('medium_term', 'N/A')}
- 整体趋势: {trend.get('overall', 'N/A')}
- MACD方向: {trend.get('macd', 'N/A')}

动量指标:
- RSI: {safe_float(tech.get('rsi')):.2f} ({'超买' if safe_float(tech.get('rsi')) > 70 else '超卖' if safe_float(tech.get('rsi')) < 30 else '中性'})
- MACD: {safe_float(tech.get('macd')):.4f}
- 信号线: {safe_float(tech.get('macd_signal')):.4f}

布林带位置: {safe_float(tech.get('bb_position')):.2%} ({'上部' if safe_float(tech.get('bb_position')) > 0.7 else '下部' if safe_float(tech.get('bb_position')) < 0.3 else '中部'})

关键水平:
- 静态阻力: {safe_float(levels.get('static_resistance', 0)):.2f}
- 静态支撑: {safe_float(levels.get('static_support', 0)):.2f}
"""
            return analysis_text
            
        except Exception as e:
            logger.error(f"生成分析文本失败: {e}")
            return "技术指标数据不可用"
