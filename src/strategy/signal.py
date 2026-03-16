"""
信号处理模块
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ConfidenceLevel(Enum):
    """信心等级"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Signal:
    """交易信号数据类"""
    signal: SignalType
    reason: str
    stop_loss: float
    take_profit: float
    confidence: ConfidenceLevel
    is_fallback: bool = False
    timestamp: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Signal':
        """从字典创建信号对象"""
        return cls(
            signal=SignalType(data.get('signal', 'HOLD')),
            reason=data.get('reason', ''),
            stop_loss=float(data.get('stop_loss', 0)),
            take_profit=float(data.get('take_profit', 0)),
            confidence=ConfidenceLevel(data.get('confidence', 'LOW')),
            is_fallback=data.get('is_fallback', False),
            timestamp=data.get('timestamp')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'signal': self.signal.value,
            'reason': self.reason,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'confidence': self.confidence.value,
            'is_fallback': self.is_fallback,
            'timestamp': self.timestamp
        }
    
    @property
    def should_trade(self) -> bool:
        """是否应该交易"""
        return self.signal != SignalType.HOLD
    
    @property
    def is_high_confidence(self) -> bool:
        """是否高信心"""
        return self.confidence == ConfidenceLevel.HIGH


class SignalProcessor:
    """信号处理器"""
    
    def __init__(self):
        self.recent_signals: list = []
        self.max_history = 30
    
    def process(self, signal_data: Dict[str, Any]) -> Signal:
        """
        处理原始信号数据
        
        Args:
            signal_data: AI分析返回的信号字典
        
        Returns:
            Signal对象
        """
        try:
            signal = Signal.from_dict(signal_data)
            
            # 保存到历史
            self.recent_signals.append(signal.to_dict())
            if len(self.recent_signals) > self.max_history:
                self.recent_signals.pop(0)
            
            logger.info(f"信号处理完成: {signal.signal.value}, "
                       f"信心: {signal.confidence.value}")
            
            return signal
            
        except Exception as e:
            logger.error(f"信号处理失败: {e}")
            # 返回保守信号
            return Signal(
                signal=SignalType.HOLD,
                reason="信号处理异常",
                stop_loss=0,
                take_profit=0,
                confidence=ConfidenceLevel.LOW,
                is_fallback=True
            )
    
    def check_signal_consistency(self, signal: Signal) -> bool:
        """
        检查信号一致性
        
        Returns:
            True if signal is consistent with recent signals
        """
        if len(self.recent_signals) < 3:
            return True
        
        # 获取最近3个信号
        recent = [s['signal'] for s in self.recent_signals[-3:]]
        
        # 如果连续3个相同信号，发出警告
        if len(set(recent)) == 1:
            logger.warning(f"连续3次{recent[0]}信号，可能存在过度交易风险")
            return False
        
        return True
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """获取信号统计信息"""
        if not self.recent_signals:
            return {}
        
        total = len(self.recent_signals)
        buy_count = len([s for s in self.recent_signals if s['signal'] == 'BUY'])
        sell_count = len([s for s in self.recent_signals if s['signal'] == 'SELL'])
        hold_count = len([s for s in self.recent_signals if s['signal'] == 'HOLD'])
        
        return {
            'total': total,
            'buy': buy_count,
            'sell': sell_count,
            'hold': hold_count,
            'buy_ratio': buy_count / total,
            'sell_ratio': sell_count / total,
            'hold_ratio': hold_count / total
        }
