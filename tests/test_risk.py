"""
风险管理测试
"""
import unittest
from datetime import datetime, timedelta
from src.trading.risk import RiskManager
from src.strategy.signal import Signal, SignalType, ConfidenceLevel


class TestRiskManager(unittest.TestCase):
    """风险管理测试类"""
    
    def setUp(self):
        self.risk_manager = RiskManager()
    
    def test_check_signal_quality(self):
        """测试信号质量检查"""
        # 高信心信号应该通过
        high_conf_signal = Signal(
            signal=SignalType.BUY,
            reason="测试",
            stop_loss=40000,
            take_profit=60000,
            confidence=ConfidenceLevel.HIGH
        )
        self.assertTrue(self.risk_manager._check_signal_quality(high_conf_signal))
        
        # 低信心信号应该失败
        low_conf_signal = Signal(
            signal=SignalType.BUY,
            reason="测试",
            stop_loss=40000,
            take_profit=60000,
            confidence=ConfidenceLevel.LOW
        )
        self.assertFalse(self.risk_manager._check_signal_quality(low_conf_signal))
    
    def test_validate_stop_loss_take_profit(self):
        """测试止损止盈验证"""
        current_price = 50000
        
        # 有效的做多止损止盈
        self.assertTrue(
            self.risk_manager.validate_stop_loss_take_profit(
                current_price, 49000, 51000, SignalType.BUY
            )
        )
        
        # 无效的做多止损（高于当前价）
        self.assertFalse(
            self.risk_manager.validate_stop_loss_take_profit(
                current_price, 51000, 52000, SignalType.BUY
            )
        )
        
        # 有效的做空止损止盈
        self.assertTrue(
            self.risk_manager.validate_stop_loss_take_profit(
                current_price, 51000, 49000, SignalType.SELL
            )
        )
    
    def test_calculate_position_risk(self):
        """测试仓位风险计算"""
        risk = self.risk_manager.calculate_position_risk(
            entry_price=50000,
            stop_loss=49000,
            position_size=1
        )
        
        self.assertIn('price_risk_percentage', risk)
        self.assertIn('risk_amount', risk)
        self.assertAlmostEqual(risk['price_risk_percentage'], 2.0, places=1)


if __name__ == '__main__':
    unittest.main()
