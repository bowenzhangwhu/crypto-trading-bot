"""
技术指标测试
"""
import unittest
import pandas as pd
import numpy as np
from src.data.indicators import TechnicalIndicators


class TestTechnicalIndicators(unittest.TestCase):
    """技术指标测试类"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建模拟K线数据
        np.random.seed(42)
        n = 100
        
        self.df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=n, freq='15min'),
            'open': np.random.randn(n).cumsum() + 50000,
            'high': np.random.randn(n).cumsum() + 50100,
            'low': np.random.randn(n).cumsum() + 49900,
            'close': np.random.randn(n).cumsum() + 50000,
            'volume': np.random.randint(1000, 10000, n)
        })
        
        # 确保 high >= low
        self.df['high'] = self.df[['high', 'low', 'close']].max(axis=1) + 100
        self.df['low'] = self.df[['low', 'close']].min(axis=1) - 100
        self.df['open'] = self.df['close'].shift(1).fillna(self.df['close'])
    
    def test_calculate_all(self):
        """测试计算所有指标"""
        result = TechnicalIndicators.calculate_all(self.df)
        
        # 检查是否添加了指标列
        self.assertIn('sma_5', result.columns)
        self.assertIn('sma_20', result.columns)
        self.assertIn('sma_50', result.columns)
        self.assertIn('rsi', result.columns)
        self.assertIn('macd', result.columns)
        self.assertIn('bb_upper', result.columns)
        self.assertIn('bb_lower', result.columns)
    
    def test_get_market_trend(self):
        """测试趋势判断"""
        df = TechnicalIndicators.calculate_all(self.df)
        trend = TechnicalIndicators.get_market_trend(df)
        
        self.assertIn('short_term', trend)
        self.assertIn('medium_term', trend)
        self.assertIn('overall', trend)
        self.assertIn('macd', trend)
        self.assertIn('rsi_level', trend)
    
    def test_get_support_resistance_levels(self):
        """测试支撑阻力位计算"""
        df = TechnicalIndicators.calculate_all(self.df)
        levels = TechnicalIndicators.get_support_resistance_levels(df)
        
        self.assertIn('static_resistance', levels)
        self.assertIn('static_support', levels)
        self.assertIn('dynamic_resistance', levels)
        self.assertIn('dynamic_support', levels)
        
        # 检查数值合理性
        self.assertGreater(levels['static_resistance'], levels['static_support'])


if __name__ == '__main__':
    unittest.main()
