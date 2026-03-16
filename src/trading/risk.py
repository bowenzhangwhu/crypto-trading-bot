"""
风险管理模块
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from src.exchange.position import PositionManager
from src.strategy.signal import Signal, SignalType
from config.settings import TRADE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RiskManager:
    """风险管理器"""
    
    def __init__(self):
        self.position_manager = PositionManager()
        self.daily_trade_count = 0
        self.last_trade_date = datetime.now().date()
        self.last_trade_time = None
        self.config = TRADE_CONFIG['risk_management']
    
    def check_trade_allowed(self, signal: Signal) -> bool:
        """
        检查是否允许交易
        
        Args:
            signal: 交易信号
        
        Returns:
            是否允许交易
        """
        # 重置每日计数
        self._reset_daily_count()
        
        # 检查每日交易次数限制
        if self.daily_trade_count >= self.config['max_daily_trades']:
            logger.warning(f"已达到每日最大交易次数限制: {self.config['max_daily_trades']}")
            return False
        
        # 检查冷却期
        if not self._check_cooldown():
            return False
        
        # 检查信号质量
        if not self._check_signal_quality(signal):
            return False
        
        return True
    
    def _reset_daily_count(self):
        """重置每日交易计数"""
        current_date = datetime.now().date()
        if current_date != self.last_trade_date:
            self.daily_trade_count = 0
            self.last_trade_date = current_date
            logger.info("重置每日交易计数")
    
    def _check_cooldown(self) -> bool:
        """检查交易冷却期"""
        if self.last_trade_time is None:
            return True
        
        cooldown_minutes = self.config['cooldown_period_minutes']
        elapsed = (datetime.now() - self.last_trade_time).total_seconds() / 60
        
        if elapsed < cooldown_minutes:
            remaining = cooldown_minutes - elapsed
            logger.warning(f"交易冷却期中，还需等待 {remaining:.1f} 分钟")
            return False
        
        return True
    
    def _check_signal_quality(self, signal: Signal) -> bool:
        """检查信号质量"""
        # 低信心信号需要额外确认
        if signal.confidence.value == 'LOW':
            logger.warning("低信心信号，建议观望")
            return False
        
        return True
    
    def record_trade(self):
        """记录交易"""
        self.daily_trade_count += 1
        self.last_trade_time = datetime.now()
        logger.info(f"记录交易，今日交易次数: {self.daily_trade_count}")
    
    def get_risk_report(self) -> Dict[str, Any]:
        """获取风险报告"""
        self._reset_daily_count()
        
        current_pos = self.position_manager.current
        
        return {
            'daily_trade_count': self.daily_trade_count,
            'max_daily_trades': self.config['max_daily_trades'],
            'remaining_trades': self.config['max_daily_trades'] - self.daily_trade_count,
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
            'cooldown_minutes': self.config['cooldown_period_minutes'],
            'current_position': {
                'side': current_pos.side if current_pos else None,
                'size': current_pos.size if current_pos else 0,
                'unrealized_pnl': current_pos.unrealized_pnl if current_pos else 0
            } if current_pos else None
        }
    
    def calculate_position_risk(self, entry_price: float, 
                               stop_loss: float,
                               position_size: float) -> Dict[str, Any]:
        """
        计算仓位风险
        
        Args:
            entry_price: 入场价格
            stop_loss: 止损价格
            position_size: 仓位大小
        
        Returns:
            风险指标
        """
        # 计算风险金额
        price_risk = abs(entry_price - stop_loss) / entry_price
        risk_amount = position_size * entry_price * price_risk
        
        return {
            'price_risk_percentage': price_risk * 100,
            'risk_amount': risk_amount,
            'risk_percentage_of_position': price_risk * 100,
            'stop_loss_distance': abs(entry_price - stop_loss)
        }
    
    def validate_stop_loss_take_profit(self, current_price: float,
                                       stop_loss: float,
                                       take_profit: float,
                                       signal_type: SignalType) -> bool:
        """
        验证止损止盈设置是否合理
        
        Returns:
            是否有效
        """
        if signal_type == SignalType.BUY:
            if stop_loss >= current_price:
                logger.error("做多止损价必须低于当前价格")
                return False
            if take_profit <= current_price:
                logger.error("做多止盈价必须高于当前价格")
                return False
        
        elif signal_type == SignalType.SELL:
            if stop_loss <= current_price:
                logger.error("做空止损价必须高于当前价格")
                return False
            if take_profit >= current_price:
                logger.error("做空止盈价必须低于当前价格")
                return False
        
        # 检查止损止盈比例是否合理
        sl_distance = abs(current_price - stop_loss) / current_price
        tp_distance = abs(current_price - take_profit) / current_price
        
        max_sl = self.config['stop_loss_percentage']
        max_tp = self.config['take_profit_percentage']
        
        if sl_distance > max_sl * 2:  # 允许2倍容差
            logger.warning(f"止损距离过大: {sl_distance*100:.2f}%")
        
        if tp_distance > max_tp * 2:
            logger.warning(f"止盈距离过大: {tp_distance*100:.2f}%")
        
        return True
