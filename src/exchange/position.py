"""
持仓管理模块
"""
from typing import Optional, Dict, Any
from src.exchange.client import ExchangeClient
from config.settings import TRADE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Position:
    """持仓数据类"""
    
    def __init__(self, data: Dict[str, Any]):
        self.symbol = data.get('symbol', '')
        self.side = data.get('side', '')  # 'long' 或 'short'
        self.size = float(data.get('contracts', 0) or 0)
        self.entry_price = float(data.get('entryPrice', 0) or 0)
        self.unrealized_pnl = float(data.get('unrealizedPnl', 0) or 0)
        self.leverage = float(data.get('leverage', TRADE_CONFIG['leverage']) or TRADE_CONFIG['leverage'])
        self.margin_mode = data.get('mgnMode', '')
    
    def __repr__(self):
        return f"Position({self.side}, size={self.size:.4f}, pnl={self.unrealized_pnl:.2f})"
    
    @property
    def is_long(self) -> bool:
        return self.side == 'long'
    
    @property
    def is_short(self) -> bool:
        return self.side == 'short'
    
    @property
    def has_position(self) -> bool:
        return self.size > 0


class PositionManager:
    """持仓管理器"""
    
    def __init__(self):
        self.client = ExchangeClient()
        self._current_position: Optional[Position] = None
    
    def update(self) -> Optional[Position]:
        """更新当前持仓信息"""
        try:
            positions = self.client.fetch_positions()
            
            for pos_data in positions:
                if pos_data['symbol'] == TRADE_CONFIG['symbol']:
                    contracts = float(pos_data.get('contracts', 0) or 0)
                    
                    if contracts > 0:
                        self._current_position = Position(pos_data)
                        logger.debug(f"当前持仓: {self._current_position}")
                        return self._current_position
            
            self._current_position = None
            return None
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return self._current_position
    
    @property
    def current(self) -> Optional[Position]:
        """获取当前持仓（缓存）"""
        return self._current_position
    
    def get_position_text(self) -> str:
        """获取持仓文本描述"""
        pos = self.current
        if not pos or not pos.has_position:
            return "无持仓"
        
        return f"{pos.side}仓, 数量: {pos.size:.4f}, 盈亏: {pos.unrealized_pnl:.2f}USDT"
    
    def calculate_position_size(self, signal_data: Dict, price: float) -> float:
        """
        计算智能仓位大小
        
        Args:
            signal_data: 信号数据
            price: 当前价格
        
        Returns:
            合约张数
        """
        config = TRADE_CONFIG['position_management']
        
        if not config.get('enable_intelligent_position', True):
            min_contracts = TRADE_CONFIG.get('min_amount', 0.01)
            logger.info(f"使用固定最小仓位: {min_contracts} 张")
            return min_contracts
        
        try:
            # 获取账户余额
            balance = self.client.fetch_balance()
            usdt_balance = balance['USDT']['free']
            
            logger.info(f"可用USDT余额: {usdt_balance:.2f}")
            
            # 严格限制最大可用金额
            max_usable = min(usdt_balance * config['max_position_ratio'], 
                           config['base_usdt_amount'])
            
            # 基础金额
            base_usdt = config['base_usdt_amount']
            
            # 根据信心程度调整
            confidence = signal_data.get('confidence', 'MEDIUM')
            confidence_multiplier = {
                'HIGH': config['high_confidence_multiplier'],
                'MEDIUM': config['medium_confidence_multiplier'],
                'LOW': config['low_confidence_multiplier']
            }.get(confidence, 0.1)
            
            # 计算最终金额
            suggested_usdt = base_usdt * confidence_multiplier
            final_usdt = min(suggested_usdt, max_usable)
            
            if final_usdt < 0.01:
                final_usdt = 0.01
            
            # 计算合约张数
            contract_size_value = TRADE_CONFIG.get('contract_size', 1)
            contract_size = final_usdt / (price * contract_size_value)
            contract_size = round(contract_size, 4)
            
            # 确保最小交易量
            min_contracts = TRADE_CONFIG.get('min_amount', 0.001)
            if contract_size < min_contracts:
                contract_size = min_contracts
                logger.warning(f"仓位小于最小值，调整为: {contract_size} 张")
            
            logger.info(f"智能仓位: {final_usdt:.4f} USDT → {contract_size:.4f} 张合约")
            
            return contract_size
            
        except Exception as e:
            logger.error(f"仓位计算失败: {e}")
            return TRADE_CONFIG.get('min_amount', 0.001)
