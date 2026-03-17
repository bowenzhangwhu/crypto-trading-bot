"""
数据获取模块
负责从交易所获取K线数据
"""
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List
from src.exchange.client import ExchangeClient
from config.settings import TRADE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataFetcher:
    """数据获取器"""
    
    def __init__(self):
        self.client = ExchangeClient()
    
    def fetch_ohlcv_data(self, symbol: Optional[str] = None,
                        timeframe: Optional[str] = None,
                        limit: Optional[int] = None) -> pd.DataFrame:
        """
        获取K线数据
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        symbol = symbol or TRADE_CONFIG['symbol']
        timeframe = timeframe or TRADE_CONFIG['timeframe']
        limit = limit or TRADE_CONFIG['data_points']
        
        try:
            logger.debug(f"获取K线数据: {symbol}, {timeframe}, limit={limit}")
            
            ohlcv = self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            logger.debug(f"获取到 {len(df)} 条K线数据")
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            raise
    
    def get_enhanced_market_data(self) -> Optional[Dict[str, Any]]:
        """
        获取增强版市场数据（包含技术指标）
        
        Returns:
            包含价格、技术指标、趋势分析的字典
        """
        try:
            from .indicators import TechnicalIndicators
            
            # 获取K线数据
            df = self.fetch_ohlcv_data()
            
            # 计算技术指标
            df = TechnicalIndicators.calculate_all(df)
            
            current_data = df.iloc[-1]
            previous_data = df.iloc[-2]
            
            # 获取趋势分析
            trend_analysis = TechnicalIndicators.get_market_trend(df)
            levels_analysis = TechnicalIndicators.get_support_resistance_levels(df)
            
            return {
                'price': float(current_data['close']),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'high': float(current_data['high']),
                'low': float(current_data['low']),
                'volume': float(current_data['volume']),
                'timeframe': TRADE_CONFIG['timeframe'],
                'price_change': ((current_data['close'] - previous_data['close']) 
                                / previous_data['close']) * 100,
                'kline_data': df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                           .tail(10).to_dict('records'),
                'technical_data': {
                    'sma_5': float(current_data.get('sma_5', 0)),
                    'sma_20': float(current_data.get('sma_20', 0)),
                    'sma_50': float(current_data.get('sma_50', 0)),
                    'rsi': float(current_data.get('rsi', 0)),
                    'macd': float(current_data.get('macd', 0)),
                    'macd_signal': float(current_data.get('macd_signal', 0)),
                    'macd_histogram': float(current_data.get('macd_histogram', 0)),
                    'bb_upper': float(current_data.get('bb_upper', 0)),
                    'bb_lower': float(current_data.get('bb_lower', 0)),
                    'bb_position': float(current_data.get('bb_position', 0)),
                    'volume_ratio': float(current_data.get('volume_ratio', 0))
                },
                'trend_analysis': trend_analysis,
                'levels_analysis': levels_analysis,
                'full_data': df
            }
            
        except Exception as e:
            logger.error(f"获取增强市场数据失败: {e}")
            return None
    
    def get_current_price(self, symbol: Optional[str] = None) -> float:
        """获取当前价格"""
        try:
            ticker = self.client.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"获取当前价格失败: {e}")
            raise
