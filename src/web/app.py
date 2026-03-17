"""
Flask Web应用
提供监控面板API
"""
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
from datetime import datetime, timedelta
from config.settings import TRADE_CONFIG
from src.database.manager import DatabaseManager
from src.websocket.manager import WebSocketManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 全局WebSocket管理器
ws_manager = None


def create_app():
    """创建Flask应用"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    # 启用CORS
    CORS(app)
    
    # 初始化SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # 初始化数据库
    db = DatabaseManager()
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('dashboard.html')
    
    @app.route('/api/status')
    def api_status():
        """API状态"""
        return jsonify({
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.1.0'
        })
    
    @app.route('/api/config')
    def api_config():
        """获取配置"""
        return jsonify({
            'symbol': TRADE_CONFIG['symbol'],
            'timeframe': TRADE_CONFIG['timeframe'],
            'leverage': TRADE_CONFIG['leverage'],
            'test_mode': TRADE_CONFIG['test_mode']
        })
    
    @app.route('/api/ticker')
    def api_ticker():
        """获取最新行情"""
        global ws_manager
        if ws_manager:
            ticker = ws_manager.get_ticker(TRADE_CONFIG['symbol'])
            if ticker:
                return jsonify(ticker)
        
        # 从数据库获取
        data = db.get_market_data_history(TRADE_CONFIG['symbol'], hours=1)
        if data:
            return jsonify(data[-1])
        
        return jsonify({'error': 'No data available'}), 404
    
    @app.route('/api/position')
    def api_position():
        """获取当前持仓"""
        global ws_manager
        if ws_manager:
            position = ws_manager.get_position(TRADE_CONFIG['symbol'])
            if position:
                return jsonify(position)
        
        # 从数据库获取
        positions = db.get_open_positions()
        if positions:
            return jsonify(positions[0])
        
        # 返回空持仓而不是404
        return jsonify({
            'symbol': TRADE_CONFIG['symbol'],
            'side': None,
            'size': 0,
            'entry_price': 0,
            'unrealized_pnl': 0,
            'status': 'no_position'
        })
    
    @app.route('/api/trades')
    def api_trades():
        """获取交易记录"""
        limit = request.args.get('limit', 50, type=int)
        trades = db.get_recent_trades(limit)
        return jsonify(trades)
    
    @app.route('/api/signals')
    def api_signals():
        """获取信号记录"""
        limit = request.args.get('limit', 100, type=int)
        signals = db.get_recent_signals(limit)
        return jsonify(signals)
    
    @app.route('/api/balance')
    def api_balance():
        """获取余额"""
        currency = request.args.get('currency', 'USDT')
        balance = db.get_latest_balance(currency)
        
        if balance:
            return jsonify(balance)
        
        return jsonify({'error': 'No balance data'}), 404
    
    @app.route('/api/balance/history')
    def api_balance_history():
        """获取余额历史"""
        currency = request.args.get('currency', 'USDT')
        hours = request.args.get('hours', 24, type=int)
        history = db.get_balance_history(currency, hours)
        return jsonify(history)
    
    @app.route('/api/performance')
    def api_performance():
        """获取绩效统计"""
        stats = db.get_performance_stats()
        return jsonify(stats)
    
    @app.route('/api/market/history')
    def api_market_history():
        """获取市场数据历史"""
        symbol = request.args.get('symbol', TRADE_CONFIG['symbol'])
        hours = request.args.get('hours', 24, type=int)
        data = db.get_market_data_history(symbol, hours)
        return jsonify(data)
    
    @app.route('/api/orderbook')
    def api_orderbook():
        """获取订单簿"""
        global ws_manager
        if ws_manager:
            orderbook = ws_manager.get_orderbook(TRADE_CONFIG['symbol'])
            if orderbook:
                return jsonify(orderbook)
        
        return jsonify({'error': 'No orderbook data'}), 404
    
    # WebSocket事件
    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        logger.info(f"客户端已连接: {request.sid}")
        emit('connected', {'data': 'Connected to trading bot'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开"""
        logger.info(f"客户端已断开: {request.sid}")
    
    @socketio.on('subscribe')
    def handle_subscribe(data):
        """订阅数据更新"""
        channel = data.get('channel')
        logger.debug(f"客户端订阅: {channel}")
        emit('subscribed', {'channel': channel})
    
    # 后台任务：定期广播数据
    def broadcast_data():
        """广播实时数据"""
        global ws_manager
        
        while True:
            try:
                if ws_manager:
                    # 获取所有数据
                    data = ws_manager.get_all_data()
                    
                    # 广播到所有客户端
                    socketio.emit('market_data', data)
                    
                    # 广播持仓数据
                    position = ws_manager.get_position(TRADE_CONFIG['symbol'])
                    if position:
                        socketio.emit('position_update', position)
                
                time.sleep(1)  # 每秒更新一次
                
            except Exception as e:
                logger.error(f"广播数据失败: {e}")
                time.sleep(5)
    
    # 启动广播线程
    broadcast_thread = threading.Thread(target=broadcast_data, daemon=True)
    broadcast_thread.start()
    
    return app, socketio


def start_web_server(host='0.0.0.0', port=5000, ws_mgr=None):
    """启动Web服务器"""
    global ws_manager
    ws_manager = ws_mgr
    
    app, socketio = create_app()
    
    logger.info(f"启动Web服务器: http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, use_reloader=False)
