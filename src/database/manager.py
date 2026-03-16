"""
数据库管理器
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, func
from .models import get_session, Trade, Position, Balance, Signal, MarketData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.session = get_session()
    
    def save_trade(self, trade_data: Dict[str, Any]) -> Trade:
        """保存交易记录"""
        try:
            trade = Trade(**trade_data)
            self.session.add(trade)
            self.session.commit()
            logger.debug(f"保存交易记录: {trade.trade_id}")
            return trade
        except Exception as e:
            self.session.rollback()
            logger.error(f"保存交易记录失败: {e}")
            raise
    
    def update_trade(self, trade_id: str, updates: Dict[str, Any]) -> bool:
        """更新交易记录"""
        try:
            trade = self.session.query(Trade).filter_by(trade_id=trade_id).first()
            if trade:
                for key, value in updates.items():
                    setattr(trade, key, value)
                trade.updated_at = datetime.utcnow()
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"更新交易记录失败: {e}")
            return False
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """获取最近的交易记录"""
        trades = self.session.query(Trade).order_by(
            desc(Trade.created_at)
        ).limit(limit).all()
        return [t.to_dict() for t in trades]
    
    def get_trades_by_date(self, start_date: datetime, 
                          end_date: datetime) -> List[Dict]:
        """获取指定日期范围的交易记录"""
        trades = self.session.query(Trade).filter(
            Trade.created_at >= start_date,
            Trade.created_at <= end_date
        ).order_by(desc(Trade.created_at)).all()
        return [t.to_dict() for t in trades]
    
    def save_position(self, position_data: Dict[str, Any]) -> Position:
        """保存持仓记录"""
        try:
            position = Position(**position_data)
            self.session.add(position)
            self.session.commit()
            return position
        except Exception as e:
            self.session.rollback()
            logger.error(f"保存持仓记录失败: {e}")
            raise
    
    def update_position(self, symbol: str, updates: Dict[str, Any]) -> bool:
        """更新持仓记录"""
        try:
            position = self.session.query(Position).filter_by(
                symbol=symbol, is_open=True
            ).first()
            if position:
                for key, value in updates.items():
                    setattr(position, key, value)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"更新持仓记录失败: {e}")
            return False
    
    def get_open_positions(self) -> List[Dict]:
        """获取当前持仓"""
        positions = self.session.query(Position).filter_by(
            is_open=True
        ).all()
        return [p.to_dict() for p in positions]
    
    def close_position(self, symbol: str, realized_pnl: float):
        """关闭持仓"""
        try:
            position = self.session.query(Position).filter_by(
                symbol=symbol, is_open=True
            ).first()
            if position:
                position.is_open = False
                position.realized_pnl = realized_pnl
                position.closed_at = datetime.utcnow()
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"关闭持仓失败: {e}")
    
    def save_balance(self, balance_data: Dict[str, Any]) -> Balance:
        """保存余额记录"""
        try:
            balance = Balance(**balance_data)
            self.session.add(balance)
            self.session.commit()
            return balance
        except Exception as e:
            self.session.rollback()
            logger.error(f"保存余额记录失败: {e}")
            raise
    
    def get_latest_balance(self, currency: str = 'USDT') -> Optional[Dict]:
        """获取最新余额"""
        balance = self.session.query(Balance).filter_by(
            currency=currency
        ).order_by(desc(Balance.recorded_at)).first()
        return balance.to_dict() if balance else None
    
    def get_balance_history(self, currency: str = 'USDT', 
                           hours: int = 24) -> List[Dict]:
        """获取余额历史"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        balances = self.session.query(Balance).filter(
            Balance.currency == currency,
            Balance.recorded_at >= start_time
        ).order_by(Balance.recorded_at).all()
        return [b.to_dict() for b in balances]
    
    def save_signal(self, signal_data: Dict[str, Any]) -> Signal:
        """保存信号记录"""
        try:
            signal = Signal(**signal_data)
            self.session.add(signal)
            self.session.commit()
            return signal
        except Exception as e:
            self.session.rollback()
            logger.error(f"保存信号记录失败: {e}")
            raise
    
    def get_recent_signals(self, limit: int = 100) -> List[Dict]:
        """获取最近的信号"""
        signals = self.session.query(Signal).order_by(
            desc(Signal.created_at)
        ).limit(limit).all()
        return [s.to_dict() for s in signals]
    
    def save_market_data(self, data: Dict[str, Any]) -> MarketData:
        """保存市场数据"""
        try:
            market_data = MarketData(**data)
            self.session.add(market_data)
            self.session.commit()
            return market_data
        except Exception as e:
            self.session.rollback()
            logger.error(f"保存市场数据失败: {e}")
            raise
    
    def get_market_data_history(self, symbol: str, 
                                hours: int = 24) -> List[Dict]:
        """获取市场数据历史"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        data = self.session.query(MarketData).filter(
            MarketData.symbol == symbol,
            MarketData.recorded_at >= start_time
        ).order_by(MarketData.recorded_at).all()
        return [d.to_dict() for d in data]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取交易绩效统计"""
        try:
            # 总交易次数
            total_trades = self.session.query(Trade).count()
            
            # 盈利交易
            profitable_trades = self.session.query(Trade).filter(
                Trade.pnl > 0
            ).count()
            
            # 总盈亏
            total_pnl = self.session.query(func.sum(Trade.pnl)).scalar() or 0
            
            # 今日交易
            today = datetime.utcnow().date()
            today_trades = self.session.query(Trade).filter(
                func.date(Trade.created_at) == today
            ).count()
            
            # 今日盈亏
            today_pnl = self.session.query(func.sum(Trade.pnl)).filter(
                func.date(Trade.created_at) == today
            ).scalar() or 0
            
            return {
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'win_rate': (profitable_trades / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'today_trades': today_trades,
                'today_pnl': today_pnl
            }
        except Exception as e:
            logger.error(f"获取绩效统计失败: {e}")
            return {}
    
    def close(self):
        """关闭数据库连接"""
        self.session.close()
