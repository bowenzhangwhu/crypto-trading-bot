"""
OKX WebSocket客户端
基于OKX官方API文档实现
"""
import json
import time
import hmac
import base64
import hashlib
import threading
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any
import websocket
from config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OKXWebSocketClient:
    """OKX WebSocket客户端"""
    
    # WebSocket URL
    WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
    WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"
    
    def __init__(self):
        self.api_key = Settings.OKX_API_KEY
        self.secret_key = Settings.OKX_SECRET
        self.passphrase = Settings.OKX_PASSWORD
        
        self.ws_public = None
        self.ws_private = None
        self.is_connected = False
        self.is_running = False
        
        # 回调函数
        self.on_ticker_callback: Optional[Callable] = None
        self.on_orderbook_callback: Optional[Callable] = None
        self.on_trade_callback: Optional[Callable] = None
        self.on_position_callback: Optional[Callable] = None
        self.on_order_callback: Optional[Callable] = None
        
        # 订阅列表
        self.subscriptions = set()
        
        # 重连机制
        self.reconnect_interval = 5
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
        
        # 心跳机制
        self.heartbeat_interval = 20  # OKX要求30秒内必须有消息，设置20秒更安全
        self.heartbeat_thread_public = None
        self.heartbeat_thread_private = None
        self.last_ping_time = 0
    
    def _generate_signature(self, timestamp: str) -> str:
        """生成签名"""
        message = timestamp + 'GET' + '/users/self/verify'
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')
    
    def _on_open(self, ws, is_private=False):
        """连接建立回调"""
        logger.info(f"WebSocket {'私有' if is_private else '公有'}连接已建立")
        self.is_connected = True
        self.reconnect_attempts = 0
        
        # 启动心跳（每个连接独立的心跳）
        self._start_heartbeat(is_private)
        
        if is_private:
            self._login_private(ws)
    
    def _start_heartbeat(self, is_private=False):
        """启动心跳线程"""
        thread_attr = 'heartbeat_thread_private' if is_private else 'heartbeat_thread_public'
        ws_attr = 'ws_private' if is_private else 'ws_public'
        
        # 检查是否已有运行中的心跳线程
        existing_thread = getattr(self, thread_attr)
        if existing_thread and existing_thread.is_alive():
            return
        
        def heartbeat_loop():
            conn_type = '私有' if is_private else '公有'
            while self.is_running:
                time.sleep(self.heartbeat_interval)
                ws = getattr(self, ws_attr)
                if ws and ws.sock:
                    try:
                        # OKX使用字符串 "ping" 作为心跳
                        ws.send('ping')
                        logger.debug(f"发送WebSocket {conn_type}心跳")
                    except Exception as e:
                        logger.warning(f"心跳发送失败 ({conn_type}): {e}")
                        break
        
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        setattr(self, thread_attr, thread)
        thread.start()
        logger.debug(f"心跳线程已启动 ({'私有' if is_private else '公有'})")
    
    def _login_private(self, ws):
        """登录私有频道"""
        timestamp = str(int(time.time()))
        sign = self._generate_signature(timestamp)
        
        login_msg = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": sign
            }]
        }
        
        ws.send(json.dumps(login_msg))
        logger.info("发送登录请求")
    
    def _on_message(self, ws, message, is_private=False):
        """收到消息回调"""
        try:
            # 处理pong响应 (OKX返回 "pong" 字符串)
            if message == 'pong':
                logger.debug("收到pong")
                return
            
            data = json.loads(message)
            
            # 处理登录响应
            if data.get('event') == 'login':
                if data.get('code') == '0':
                    logger.info("WebSocket登录成功")
                    # 重新订阅私有频道
                    self._resubscribe_private()
                else:
                    logger.error(f"WebSocket登录失败: {data}")
                return
            
            # 处理订阅响应
            if data.get('event') in ['subscribe', 'unsubscribe']:
                logger.debug(f"订阅响应: {data}")
                return
            
            # 处理错误消息
            if data.get('event') == 'error':
                logger.error(f"WebSocket错误消息: {data}")
                return
            
            # 处理频道数据
            if 'arg' in data and 'data' in data:
                channel = data['arg'].get('channel')
                self._handle_channel_data(channel, data['data'], is_private)
            
        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}")
    
    def _handle_channel_data(self, channel: str, data: list, is_private: bool):
        """处理频道数据"""
        if not data:
            return
        
        item = data[0]
        
        if channel == 'tickers':
            if self.on_ticker_callback:
                self.on_ticker_callback(item)
        
        elif channel == 'books':
            if self.on_orderbook_callback:
                self.on_orderbook_callback(item)
        
        elif channel == 'trades':
            if self.on_trade_callback:
                self.on_trade_callback(item)
        
        elif channel == 'positions':
            if self.on_position_callback:
                self.on_position_callback(item)
        
        elif channel == 'orders':
            if self.on_order_callback:
                self.on_order_callback(item)
    
    def _on_error(self, ws, error, is_private=False):
        """错误回调"""
        logger.error(f"WebSocket {'私有' if is_private else '公有'}错误: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg, is_private=False):
        """连接关闭回调"""
        logger.warning(f"WebSocket {'私有' if is_private else '公有'}连接关闭: {close_status_code} - {close_msg}")
        was_connected = self.is_connected
        self.is_connected = False
        
        # 尝试重连（只在非正常关闭时重连）
        if self.is_running and was_connected and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"{self.reconnect_interval}秒后尝试重连... (尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            time.sleep(self.reconnect_interval)
            # 清理旧连接
            if is_private:
                self.ws_private = None
            else:
                self.ws_public = None
            self.connect()
    
    def connect(self):
        """建立WebSocket连接"""
        self.is_running = True
        
        # 只在未连接时创建新线程
        if not self.ws_public or not self.ws_public.sock:
            threading.Thread(target=self._connect_public, daemon=True).start()
        
        # 连接私有频道
        if self.api_key and (not self.ws_private or not self.ws_private.sock):
            threading.Thread(target=self._connect_private, daemon=True).start()
    
    def _connect_public(self):
        """连接公有频道"""
        try:
            self.ws_public = websocket.WebSocketApp(
                self.WS_URL,
                on_open=lambda ws: self._on_open(ws, False),
                on_message=lambda ws, msg: self._on_message(ws, msg, False),
                on_error=lambda ws, err: self._on_error(ws, err, False),
                on_close=lambda ws, code, msg: self._on_close(ws, code, msg, False)
            )
            self.ws_public.run_forever()
        except Exception as e:
            logger.error(f"公有WebSocket连接失败: {e}")
    
    def _connect_private(self):
        """连接私有频道"""
        try:
            self.ws_private = websocket.WebSocketApp(
                self.WS_PRIVATE_URL,
                on_open=lambda ws: self._on_open(ws, True),
                on_message=lambda ws, msg: self._on_message(ws, msg, True),
                on_error=lambda ws, err: self._on_error(ws, err, True),
                on_close=lambda ws, code, msg: self._on_close(ws, code, msg, True)
            )
            self.ws_private.run_forever()
        except Exception as e:
            logger.error(f"私有WebSocket连接失败: {e}")
    
    def subscribe_ticker(self, inst_id: str):
        """订阅行情数据"""
        self._subscribe('tickers', inst_id, False)
    
    def subscribe_orderbook(self, inst_id: str, depth: int = 5):
        """订阅订单簿"""
        self._subscribe('books', inst_id, False)
    
    def subscribe_trades(self, inst_id: str):
        """订阅成交数据"""
        self._subscribe('trades', inst_id, False)
    
    def subscribe_positions(self, inst_type: str = 'SWAP', inst_id: str = None):
        """订阅持仓数据（私有）"""
        # positions频道使用instType而不是instId
        self._subscribe('positions', inst_type, True)
    
    def subscribe_orders(self, inst_type: str = 'SWAP', inst_id: str = None):
        """订阅订单数据（私有）"""
        # orders频道使用instType而不是instId
        self._subscribe('orders', inst_type, True)
    
    def _subscribe(self, channel: str, inst_id: str, is_private: bool):
        """订阅频道"""
        sub_key = f"{channel}:{inst_id}"
        self.subscriptions.add(sub_key)
        
        # 构建订阅参数
        arg = {"channel": channel}
        
        # 不同频道使用不同参数
        if channel in ['positions', 'orders', 'account']:
            # 这些频道使用instType
            arg["instType"] = inst_id if inst_id else 'SWAP'
        else:
            # 其他频道使用instId
            arg["instId"] = inst_id
        
        msg = {
            "op": "subscribe",
            "args": [arg]
        }
        
        ws = self.ws_private if is_private else self.ws_public
        if ws and ws.sock:
            try:
                ws.send(json.dumps(msg))
                logger.debug(f"订阅频道: {sub_key}")
            except Exception as e:
                logger.warning(f"订阅失败 {sub_key}: {e}")
    
    def _resubscribe_private(self):
        """重新订阅私有频道"""
        for sub_key in self.subscriptions:
            if ':' in sub_key:
                channel, inst_id = sub_key.split(':', 1)
                if channel in ['positions', 'orders']:
                    self._subscribe(channel, inst_id, True)
    
    def unsubscribe(self, channel: str, inst_id: str, is_private: bool = False):
        """取消订阅"""
        sub_key = f"{channel}:{inst_id}"
        self.subscriptions.discard(sub_key)
        
        msg = {
            "op": "unsubscribe",
            "args": [{
                "channel": channel,
                "instId": inst_id
            }]
        }
        
        ws = self.ws_private if is_private else self.ws_public
        if ws and self.is_connected:
            ws.send(json.dumps(msg))
    
    def disconnect(self):
        """断开连接"""
        self.is_running = False
        
        if self.ws_public:
            self.ws_public.close()
        
        if self.ws_private:
            self.ws_private.close()
        
        logger.info("WebSocket连接已断开")
