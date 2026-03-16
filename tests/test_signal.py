"""
信号处理测试
"""
import unittest
from src.strategy.signal import Signal, SignalType, ConfidenceLevel, SignalProcessor


class TestSignal(unittest.TestCase):
    """信号测试类"""
    
    def test_signal_creation(self):
        """测试信号创建"""
        signal = Signal(
            signal=SignalType.BUY,
            reason="测试信号",
            stop_loss=40000,
            take_profit=60000,
            confidence=ConfidenceLevel.HIGH
        )
        
        self.assertEqual(signal.signal, SignalType.BUY)
        self.assertEqual(signal.confidence, ConfidenceLevel.HIGH)
        self.assertTrue(signal.should_trade)
        self.assertTrue(signal.is_high_confidence)
    
    def test_signal_from_dict(self):
        """测试从字典创建信号"""
        data = {
            'signal': 'SELL',
            'reason': '测试',
            'stop_loss': 40000,
            'take_profit': 60000,
            'confidence': 'MEDIUM',
            'is_fallback': False
        }
        
        signal = Signal.from_dict(data)
        
        self.assertEqual(signal.signal, SignalType.SELL)
        self.assertEqual(signal.confidence, ConfidenceLevel.MEDIUM)
        self.assertFalse(signal.is_high_confidence)
    
    def test_signal_to_dict(self):
        """测试信号转字典"""
        signal = Signal(
            signal=SignalType.HOLD,
            reason="观望",
            stop_loss=0,
            take_profit=0,
            confidence=ConfidenceLevel.LOW
        )
        
        data = signal.to_dict()
        
        self.assertEqual(data['signal'], 'HOLD')
        self.assertEqual(data['confidence'], 'LOW')
        self.assertFalse(data['is_fallback'])


class TestSignalProcessor(unittest.TestCase):
    """信号处理器测试类"""
    
    def setUp(self):
        self.processor = SignalProcessor()
    
    def test_process_signal(self):
        """测试信号处理"""
        data = {
            'signal': 'BUY',
            'reason': '测试',
            'stop_loss': 40000,
            'take_profit': 60000,
            'confidence': 'HIGH'
        }
        
        signal = self.processor.process(data)
        
        self.assertEqual(signal.signal, SignalType.BUY)
        self.assertEqual(len(self.processor.recent_signals), 1)
    
    def test_signal_statistics(self):
        """测试信号统计"""
        # 添加多个信号
        for i in range(5):
            self.processor.process({
                'signal': 'BUY' if i % 2 == 0 else 'SELL',
                'reason': '测试',
                'stop_loss': 40000,
                'take_profit': 60000,
                'confidence': 'MEDIUM'
            })
        
        stats = self.processor.get_signal_statistics()
        
        self.assertEqual(stats['total'], 5)
        self.assertEqual(stats['buy'] + stats['sell'], 5)


if __name__ == '__main__':
    unittest.main()
