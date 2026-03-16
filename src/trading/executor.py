"""
交易执行模块
"""
import time
from typing import Optional, Dict, Any
from src.exchange.client import ExchangeClient
from src.exchange.position import PositionManager, Position
from src.strategy.signal import Signal, SignalType
from config.settings import TRADE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TradeExecutor:
    """交易执行器"""
    
    def __init__(self):
        self.client = ExchangeClient()
        self.position_manager = PositionManager()
        self.test_mode = TRADE_CONFIG['test_mode']
    
    def execute(self, signal: Signal, price: float) -> bool:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
            price: 当前价格
        
        Returns:
            是否执行成功
        """
        # 检查余额
        if not self._check_balance():
            return False
        
        # 更新持仓信息
        current_position = self.position_manager.update()
        
        # 获取目标仓位大小
        position_size = self.position_manager.calculate_position_size(
            signal.to_dict(), price
        )
        
        logger.info(f"交易信号: {signal.signal.value}")
        logger.info(f"信心程度: {signal.confidence.value}")
        logger.info(f"智能仓位: {position_size:.4f} 张")
        logger.info(f"理由: {signal.reason}")
        
        # 测试模式
        if self.test_mode:
            logger.info("【测试模式】仅模拟交易，不执行真实订单")
            return True
        
        # 低信心信号跳过
        if signal.confidence.value == 'LOW':
            logger.warning("低信心信号，跳过执行")
            return False
        
        # 执行交易
        try:
            if signal.signal == SignalType.BUY:
                return self._execute_buy(current_position, position_size)
            elif signal.signal == SignalType.SELL:
                return self._execute_sell(current_position, position_size)
            elif signal.signal == SignalType.HOLD:
                logger.info("建议观望，不执行交易")
                return True
            
        except Exception as e:
            logger.error(f"交易执行失败: {e}")
            return False
    
    def _check_balance(self) -> bool:
        """检查账户余额"""
        try:
            balance = self.client.fetch_balance()
            usdt_balance = balance['USDT']['free']
            
            min_threshold = TRADE_CONFIG['risk_management']['min_balance_threshold']
            
            if usdt_balance < min_threshold:
                logger.error(f"资金不足: {usdt_balance:.2f} USDT (最低需要 {min_threshold})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查余额失败: {e}")
            return False
    
    def _execute_buy(self, current_position: Optional[Position], 
                    position_size: float) -> bool:
        """执行买入/开多"""
        symbol = TRADE_CONFIG['symbol']
        
        if current_position and current_position.is_short:
            # 平空仓并开多仓
            if current_position.size > 0:
                logger.info(f"平空仓 {current_position.size:.4f} 张并开多仓 {position_size:.4f} 张...")
                
                # 平空仓
                self.client.create_market_order(
                    side='buy',
                    amount=current_position.size,
                    reduce_only=True
                )
                time.sleep(1)
            
            # 开多仓
            self.client.create_market_order(
                side='buy',
                amount=position_size,
                reduce_only=False
            )
            
        elif current_position and current_position.is_long:
            # 同方向，调整仓位
            size_diff = position_size - current_position.size
            
            if abs(size_diff) >= 0.01:
                if size_diff > 0:
                    # 加仓
                    add_size = round(size_diff, 2)
                    logger.info(f"多仓加仓 {add_size:.4f} 张")
                    self.client.create_market_order(
                        side='buy',
                        amount=add_size,
                        reduce_only=False
                    )
                else:
                    # 减仓
                    reduce_size = round(abs(size_diff), 2)
                    logger.info(f"多仓减仓 {reduce_size:.4f} 张")
                    self.client.create_market_order(
                        side='sell',
                        amount=reduce_size,
                        reduce_only=True
                    )
            else:
                logger.info(f"已有多头持仓，仓位合适保持现状")
        
        else:
            # 无持仓，开多仓
            logger.info(f"开多仓 {position_size:.4f} 张...")
            self.client.create_market_order(
                side='buy',
                amount=position_size,
                reduce_only=False
            )
        
        logger.info("买入执行成功")
        time.sleep(2)
        
        # 更新持仓
        self.position_manager.update()
        return True
    
    def _execute_sell(self, current_position: Optional[Position],
                     position_size: float) -> bool:
        """执行卖出/开空"""
        if current_position and current_position.is_long:
            # 平多仓并开空仓
            if current_position.size > 0:
                logger.info(f"平多仓 {current_position.size:.4f} 张并开空仓 {position_size:.4f} 张...")
                
                # 平多仓
                self.client.create_market_order(
                    side='sell',
                    amount=current_position.size,
                    reduce_only=True
                )
                time.sleep(1)
            
            # 开空仓
            self.client.create_market_order(
                side='sell',
                amount=position_size,
                reduce_only=False
            )
            
        elif current_position and current_position.is_short:
            # 同方向，调整仓位
            size_diff = position_size - current_position.size
            
            if abs(size_diff) >= 0.01:
                if size_diff > 0:
                    # 加仓
                    add_size = round(size_diff, 2)
                    logger.info(f"空仓加仓 {add_size:.4f} 张")
                    self.client.create_market_order(
                        side='sell',
                        amount=add_size,
                        reduce_only=False
                    )
                else:
                    # 减仓
                    reduce_size = round(abs(size_diff), 2)
                    logger.info(f"空仓减仓 {reduce_size:.4f} 张")
                    self.client.create_market_order(
                        side='buy',
                        amount=reduce_size,
                        reduce_only=True
                    )
            else:
                logger.info(f"已有空头持仓，仓位合适保持现状")
        
        else:
            # 无持仓，开空仓
            logger.info(f"开空仓 {position_size:.4f} 张...")
            self.client.create_market_order(
                side='sell',
                amount=position_size,
                reduce_only=False
            )
        
        logger.info("卖出执行成功")
        time.sleep(2)
        
        # 更新持仓
        self.position_manager.update()
        return True
