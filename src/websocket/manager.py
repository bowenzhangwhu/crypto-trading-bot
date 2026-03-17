"""
WebSocket管理器
统一管理所有WebSocket连接和数据分发
"""
import json
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from .client import OKXWebSocketClient
from src.database.manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self):
        self.client = OKXWebSocketClient()
        self.db = DatabaseManager()
        
        # 数据缓存
        self.ticker_data: Dict[str, Any] = {}
        self.orderbook_data: Dict[str, Any] = {}
        self.position_data: Dict[str, Any] = {}
        
        # 设置回调
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """设置WebSocket回调"""
        self.client.on_ticker_callback = self._on_ticker
        self.client.on_orderbook_callback = self._on_orderbook
        self.client.on_position_callback = self._on_position
        self.client.on_order_callback = self._on_order
    
    def _on_ticker(self, data: Dict):
        """处理行情数据"""
        try:
            inst_id = data.get('instId')
            if not inst_id:
                return
            
            # 缓存数据
            self.ticker_data[inst_id] = {
                'price': float(data.get('last', 0)),
                'high_24h': float(data.get('high24h', 0)),
                'low_24h': float(data.get('low24h', 0)),
                'volume_24h': float(data.get('vol24h', 0)),
                'change_24h': float(data.get('open24h', 0)),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # 保存到数据库（每5秒保存一次）
            if inst_id not in self._last_saved or \
               (datetime.utcnow() - self._last_saved.get(inst_id, datetime.min)).seconds >= 5:
                self.db.save_market_data({
                    'symbol': inst_id,
                    'price': self.ticker_data[inst_id]['price'],
                    'high_24h': self.ticker_data[inst_id]['high_24h'],
                    'low_24h': self.ticker_data[inst_id]['low_24h'],
                    'volume_24h': self.ticker_data[inst_id]['volume_24h'],
                    'change_24h': self.ticker_data[inst_id]['change_24h']
                })
                self._last_saved[inst_id] = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"处理行情数据失败: {e}")
    
    def _on_orderbook(self, data: Dict):
        """处理订单簿数据"""
        try:
            inst_id = data.get('instId')
            if not inst_id:
                return
            
            asks = data.get('asks', [])
            bids = data.get('bids', [])
            
            self.orderbook_data[inst_id] = {
                'asks': [[float(p), float(s)] for p, s, *_ in asks[:5]],
                'bids': [[float(p), float(s)] for p, s, *_ in bids[:5]],
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"处理订单簿数据失败: {e}")
    
    def _on_position(self, data: Dict):
        """处理持仓数据"""
        try:
            inst_id = data.get('instId')
            if not inst_id:
                return
            
            self.position_data[inst_id] = {
                'symbol': inst_id,
                'side': data.get('posSide'),
                'size': float(data.get('pos', 0)),
                'entry_price': float(data.get('avgPx', 0)),
                'mark_price': float(data.get('markPx', 0)),
                'unrealized_pnl': float(data.get('upl', 0)),
                'margin': float(data.get('margin', 0)),
                'leverage': float(data.get('lever', 1)),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # 更新数据库
            self.db.update_position(inst_id, self.position_data[inst_id])
            
        except Exception as e:
            logger.error(f"处理持仓数据失败: {e}")
    
    def _on_order(self, data: Dict):
        """处理订单数据"""
        try:
            order_id = data.get('ordId')
            if not order_id:
                return
            
            # 更新数据库中的订单状态
            updates = {
                'status': data.get('state', 'pending').lower(),
                'filled_price': float(data.get('avgPx', 0)) if data.get('avgPx') else None,
                'updated_at': datetime.utcnow()
            }
            
            self.db.update_trade(order_id, updates)
            
        except Exception as e:
            logger.error(f"处理订单数据失败: {e}")
    
    def start(self, symbol: str):
        """启动WebSocket连接"""
        logger.info(f"启动WebSocket管理器，交易对: {symbol}")
        
        # 转换交易对格式 (DOGE/USDT:USDT -> DOGE-USDT-SWAP)
        inst_id = symbol.replace('/', '-').replace(':USDT', '-SWAP')
        
        # 连接WebSocket
        self.client.connect()
        
        # 等待连接建立（给足够时间）
        import time
        max_wait = 10
        waited = 0
        while waited < max_wait:
            time.sleep(0.5)
            waited += 0.5
            if self.client.is_connected:
                break
        
        if not self.client.is_connected:
            logger.warning("WebSocket连接未在预期时间内建立，继续尝试订阅...")
        
        # 订阅公有频道
        self.client.subscribe_ticker(inst_id)
        self.client.subscribe_orderbook(inst_id)
        
        # 订阅私有频道（使用正确的instType格式）
        self.client.subscribe_positions('SWAP', inst_id)
        self.client.subscribe_orders('SWAP', inst_id)
        
        self._last_saved = {}
        
        logger.info("WebSocket订阅完成")
    
    def stop(self):
        """停止WebSocket连接"""
        self.client.disconnect()
        self.db.close()
        logger.info("WebSocket管理器已停止")
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """获取最新行情"""
        return self.ticker_data.get(symbol)
    
    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """获取最新订单簿"""
        return self.orderbook_data.get(symbol)
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """获取最新持仓"""
        return self.position_data.get(symbol)
    
    def get_all_data(self) -> Dict[str, Any]:
        """获取所有数据"""
        return {
            'ticker': self.ticker_data,
            'orderbook': self.orderbook_data,
            'position': self.position_data,
            'timestamp': datetime.utcnow().isoformat()
        }
