"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

Base = declarative_base()

# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / "data" / "trading.db"
DB_PATH.parent.mkdir(exist_ok=True)


class Trade(Base):
    """交易记录表"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(String(50), unique=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy/sell
    order_type = Column(String(20), default='market')  # market/limit
    amount = Column(Float, nullable=False)
    price = Column(Float)
    filled_price = Column(Float)
    status = Column(String(20), default='pending')  # pending/filled/cancelled
    pnl = Column(Float, default=0)
    fee = Column(Float, default=0)
    signal_id = Column(String(50))
    confidence = Column(String(10))
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'side': self.side,
            'order_type': self.order_type,
            'amount': self.amount,
            'price': self.price,
            'filled_price': self.filled_price,
            'status': self.status,
            'pnl': self.pnl,
            'fee': self.fee,
            'signal_id': self.signal_id,
            'confidence': self.confidence,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Position(Base):
    """持仓记录表"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # long/short
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    mark_price = Column(Float)
    liquidation_price = Column(Float)
    unrealized_pnl = Column(Float, default=0)
    realized_pnl = Column(Float, default=0)
    margin = Column(Float)
    leverage = Column(Float)
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'mark_price': self.mark_price,
            'liquidation_price': self.liquidation_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'margin': self.margin,
            'leverage': self.leverage,
            'is_open': self.is_open,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }


class Balance(Base):
    """余额记录表"""
    __tablename__ = 'balances'
    
    id = Column(Integer, primary_key=True)
    currency = Column(String(10), nullable=False, index=True)
    total = Column(Float, default=0)
    available = Column(Float, default=0)
    frozen = Column(Float, default=0)
    equity = Column(Float, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'currency': self.currency,
            'total': self.total,
            'available': self.available,
            'frozen': self.frozen,
            'equity': self.equity,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


class Signal(Base):
    """信号记录表"""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(String(50), unique=True, index=True)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)  # BUY/SELL/HOLD
    confidence = Column(String(10))
    reason = Column(Text)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    is_fallback = Column(Boolean, default=False)
    executed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'reason': self.reason,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'is_fallback': self.is_fallback,
            'executed': self.executed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class MarketData(Base):
    """市场数据记录表"""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    high_24h = Column(Float)
    low_24h = Column(Float)
    volume_24h = Column(Float)
    change_24h = Column(Float)
    funding_rate = Column(Float)
    open_interest = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'price': self.price,
            'high_24h': self.high_24h,
            'low_24h': self.low_24h,
            'volume_24h': self.volume_24h,
            'change_24h': self.change_24h,
            'funding_rate': self.funding_rate,
            'open_interest': self.open_interest,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


# 全局引擎和会话
_engine = None
_Session = None


def init_db():
    """初始化数据库"""
    global _engine, _Session
    
    _engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine)
    return _engine


def get_session():
    """获取数据库会话"""
    global _Session
    if _Session is None:
        init_db()
    return _Session()


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        init_db()
    return _engine
