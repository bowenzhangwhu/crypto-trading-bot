#!/usr/bin/env python3
"""
交易机器人启动脚本 v2.0
集成WebSocket、数据库、监控面板
"""
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings, TRADE_CONFIG
from src.utils.logger import setup_logging, get_logger
from src.exchange.client import ExchangeClient
from src.data.fetcher import DataFetcher
from src.strategy.analyzer import AIAnalyzer
from src.strategy.signal import SignalProcessor
from src.trading.executor import TradeExecutor
from src.trading.risk import RiskManager
from src.utils.helpers import wait_for_next_period
from src.database.manager import DatabaseManager
from src.websocket.manager import WebSocketManager
from src.web.app import start_web_server

logger = get_logger(__name__)


class TradingBot:
    """交易机器人类 v2.0"""
    
    def __init__(self):
        self.exchange_client = ExchangeClient()
        self.data_fetcher = DataFetcher()
        self.ai_analyzer = AIAnalyzer()
        self.signal_processor = SignalProcessor()
        self.trade_executor = TradeExecutor()
        self.risk_manager = RiskManager()
        self.db = DatabaseManager()
        self.ws_manager = None
        self.web_thread = None
        self.running = False
        
        # 初始化数据库
        from src.database.models import init_db
        init_db()
    
    def initialize(self) -> bool:
        """初始化机器人"""
        try:
            logger.info("=" * 60)
            logger.info("AI量化交易机器人 v2.0")
            logger.info("=" * 60)
            
            # 验证配置
            Settings.validate()
            
            # 显示配置信息
            logger.info(f"交易对: {TRADE_CONFIG['symbol']}")
            logger.info(f"K线周期: {TRADE_CONFIG['timeframe']}")
            logger.info(f"杠杆倍数: {TRADE_CONFIG['leverage']}x")
            logger.info(f"测试模式: {'是' if TRADE_CONFIG['test_mode'] else '否'}")
            
            # 初始化交易所
            if not self.exchange_client.initialize():
                logger.error("交易所初始化失败")
                return False
            
            # 设置交易参数
            if not self.exchange_client.setup_trading():
                logger.error("交易参数设置失败")
                return False
            
            # 启动WebSocket
            logger.info("启动WebSocket连接...")
            self.ws_manager = WebSocketManager()
            self.ws_manager.start(TRADE_CONFIG['symbol'])
            
            # 启动Web服务器
            logger.info("启动Web监控面板...")
            self.web_thread = threading.Thread(
                target=start_web_server,
                kwargs={'host': '0.0.0.0', 'port': 5000, 'ws_mgr': self.ws_manager},
                daemon=True
            )
            self.web_thread.start()
            logger.info("监控面板地址: http://localhost:5000")
            
            logger.info("机器人初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            return False
    
    def run_once(self):
        """执行一次交易循环"""
        try:
            logger.info("\n" + "=" * 60)
            logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)
            
            # 1. 获取市场数据
            logger.info("正在获取市场数据...")
            price_data = self.data_fetcher.get_enhanced_market_data()
            
            if not price_data:
                logger.error("获取市场数据失败")
                return
            
            logger.info(f"当前价格: ${price_data['price']:,.2f}")
            logger.info(f"价格变化: {price_data['price_change']:+.2f}%")
            
            # 保存余额记录
            try:
                balance = self.exchange_client.fetch_balance()
                self.db.save_balance({
                    'currency': 'USDT',
                    'total': balance['USDT'].get('total', 0),
                    'available': balance['USDT'].get('free', 0),
                    'frozen': balance['USDT'].get('used', 0)
                })
            except Exception as e:
                logger.warning(f"保存余额记录失败: {e}")
            
            # 2. AI分析
            logger.info("正在进行AI分析...")
            signal_data = self.ai_analyzer.analyze_market(price_data)
            
            # 保存信号到数据库
            signal_record = {
                'signal_id': f"sig_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'symbol': TRADE_CONFIG['symbol'],
                'signal_type': signal_data.get('signal', 'HOLD'),
                'confidence': signal_data.get('confidence', 'LOW'),
                'reason': signal_data.get('reason', ''),
                'stop_loss': signal_data.get('stop_loss', 0),
                'take_profit': signal_data.get('take_profit', 0),
                'is_fallback': signal_data.get('is_fallback', False)
            }
            self.db.save_signal(signal_record)
            
            if signal_data.get('is_fallback'):
                logger.warning("使用备用交易信号")
            
            # 3. 处理信号
            signal = self.signal_processor.process(signal_data)
            
            # 4. 风险管理检查
            if not self.risk_manager.check_trade_allowed(signal):
                logger.warning("风险管理阻止了本次交易")
                return
            
            # 5. 执行交易
            if signal.should_trade:
                success = self.trade_executor.execute(signal, price_data['price'])
                if success:
                    self.risk_manager.record_trade()
                    
                    # 保存交易记录
                    trade_record = {
                        'trade_id': f"trade_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        'symbol': TRADE_CONFIG['symbol'],
                        'side': 'buy' if signal.signal.value == 'BUY' else 'sell',
                        'amount': 0,  # 实际执行时会更新
                        'price': price_data['price'],
                        'signal_id': signal_record['signal_id'],
                        'confidence': signal.confidence.value,
                        'reason': signal.reason
                    }
                    self.db.save_trade(trade_record)
            else:
                logger.info("信号为HOLD，不执行交易")
            
            # 6. 输出风险报告
            risk_report = self.risk_manager.get_risk_report()
            logger.info(f"今日交易次数: {risk_report['daily_trade_count']}/"
                       f"{risk_report['max_daily_trades']}")
            
            # 7. 输出绩效统计
            perf_stats = self.db.get_performance_stats()
            logger.info(f"总盈亏: ${perf_stats.get('total_pnl', 0):.2f}, "
                       f"胜率: {perf_stats.get('win_rate', 0):.1f}%")
            
        except Exception as e:
            logger.error(f"交易循环执行失败: {e}", exc_info=True)
    
    def run(self):
        """运行机器人主循环"""
        if not self.initialize():
            logger.error("机器人初始化失败，退出")
            return
        
        self.running = True
        logger.info("机器人启动成功，开始运行...")
        logger.info(f"执行频率: 每{TRADE_CONFIG['timeframe']}周期执行一次")
        
        try:
            while self.running:
                # 等待到整点
                wait_seconds = wait_for_next_period(
                    int(TRADE_CONFIG['timeframe'].rstrip('m'))
                )
                
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                
                # 执行交易
                self.run_once()
                
                # 短暂休息后继续等待
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("收到停止信号，机器人正在关闭...")
            self.stop()
        except Exception as e:
            logger.error(f"机器人运行异常: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """停止机器人"""
        self.running = False
        
        if self.ws_manager:
            self.ws_manager.stop()
        
        self.db.close()
        logger.info("机器人已停止")


def main():
    """主函数"""
    # 设置日志
    setup_logging()
    
    # 创建并运行机器人
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
