"""
交易所客户端模块
封装ccxt交易所操作
"""
import ccxt
from typing import Optional, Dict, Any, List
from config.settings import Settings, TRADE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExchangeClient:
    """交易所客户端"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.exchange = None
        self.symbol = TRADE_CONFIG["symbol"]
        self.leverage = TRADE_CONFIG["leverage"]
        self._initialized = True
    
    def _ensure_initialized(self):
        """确保交易所已初始化"""
        if self.exchange is None:
            self.initialize()
    
    def initialize(self) -> bool:
        """初始化交易所连接"""
        try:
            logger.info("正在初始化OKX交易所...")
            
            self.exchange = ccxt.okx({
                'options': {
                    'defaultType': 'swap',
                },
                'apiKey': Settings.OKX_API_KEY,
                'secret': Settings.OKX_SECRET,
                'password': Settings.OKX_PASSWORD,
                'enableRateLimit': True,
            })
            
            # 测试连接
            self.exchange.load_markets()
            logger.info("交易所连接成功")
            return True
            
        except Exception as e:
            logger.error(f"交易所初始化失败: {e}")
            return False
    
    def setup_trading(self) -> bool:
        """设置交易参数"""
        try:
            logger.info(f"设置交易参数: 交易对={self.symbol}, 杠杆={self.leverage}x")
            
            # 获取合约规格
            market = self.exchange.market(self.symbol)
            contract_size = float(market['contractSize'])
            min_amount = market['limits']['amount']['min']
            
            # 存储合约规格到配置
            TRADE_CONFIG['contract_size'] = contract_size
            TRADE_CONFIG['min_amount'] = min_amount
            
            logger.info(f"合约规格: 1张 = {contract_size}, 最小交易量: {min_amount}")
            
            # 检查余额
            balance = self.fetch_balance()
            usdt_balance = balance['USDT']['free']
            logger.info(f"当前USDT余额: {usdt_balance:.2f}")
            
            if usdt_balance < TRADE_CONFIG['risk_management']['min_balance_threshold']:
                logger.error(f"资金不足: {usdt_balance:.2f} USDT")
                return False
            
            # 检查现有持仓模式
            if not self._check_position_mode():
                return False
            
            # 设置单向持仓模式
            self._set_position_mode()
            
            # 设置杠杆
            self._set_leverage()
            
            logger.info("交易参数设置完成")
            return True
            
        except Exception as e:
            logger.error(f"设置交易参数失败: {e}", exc_info=True)
            return False
    
    def _check_position_mode(self) -> bool:
        """检查持仓模式"""
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            
            for pos in positions:
                if pos['symbol'] == self.symbol:
                    contracts = float(pos.get('contracts', 0))
                    mode = pos.get('mgnMode')
                    
                    if contracts > 0 and mode == 'isolated':
                        logger.error("检测到逐仓持仓，请先平仓或转为全仓模式")
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f"检查持仓模式失败: {e}")
            return True  # 继续执行
    
    def _set_position_mode(self):
        """设置单向持仓模式"""
        try:
            self.exchange.set_position_mode(False, self.symbol)
            logger.info("已设置单向持仓模式")
        except Exception as e:
            logger.warning(f"设置单向持仓模式失败(可能已设置): {e}")
    
    def _set_leverage(self):
        """设置杠杆"""
        try:
            self.exchange.set_leverage(
                self.leverage,
                self.symbol,
                {'mgnMode': 'cross'}
            )
            logger.info(f"已设置全仓杠杆: {self.leverage}x")
        except Exception as e:
            logger.warning(f"设置杠杆失败: {e}")
            # 尝试简单设置
            try:
                self.exchange.set_leverage(self.leverage, self.symbol)
                logger.info(f"已设置杠杆: {self.leverage}x")
            except Exception as e2:
                logger.warning(f"简单杠杆设置也失败: {e2}")
    
    def fetch_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        self._ensure_initialized()
        return self.exchange.fetch_balance()
    
    def fetch_ohlcv(self, symbol: Optional[str] = None, 
                    timeframe: Optional[str] = None,
                    limit: Optional[int] = None) -> List[List]:
        """获取K线数据"""
        self._ensure_initialized()
        symbol = symbol or self.symbol
        timeframe = timeframe or TRADE_CONFIG['timeframe']
        limit = limit or TRADE_CONFIG['data_points']
        
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取持仓信息"""
        self._ensure_initialized()
        symbols = [symbol or self.symbol]
        return self.exchange.fetch_positions(symbols)
    
    def fetch_ticker(self, symbol: Optional[str] = None) -> Dict:
        """获取行情数据"""
        self._ensure_initialized()
        symbol = symbol or self.symbol
        return self.exchange.fetch_ticker(symbol)
    
    def create_market_order(self, side: str, amount: float, 
                           reduce_only: bool = False) -> Dict:
        """
        创建市价单
        
        Args:
            side: 'buy' 或 'sell'
            amount: 交易数量
            reduce_only: 是否只减仓
        
        Returns:
            订单信息
        """
        self._ensure_initialized()
        params = {'tag': TRADE_CONFIG['execution']['order_tag']}
        if reduce_only:
            params['reduceOnly'] = True
        
        return self.exchange.create_market_order(
            self.symbol, side, amount, params=params
        )
    
    def get_contract_value(self, price: float) -> float:
        """计算合约价值"""
        contract_size = TRADE_CONFIG.get('contract_size', 1)
        return price * contract_size
