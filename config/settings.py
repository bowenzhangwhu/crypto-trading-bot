"""
配置管理模块
负责加载和管理所有配置
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """应用配置类"""
    
    # 项目根目录
    BASE_DIR = Path(__file__).parent.parent
    
    # DeepSeek API配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    
    # OKX API配置
    OKX_API_KEY = os.getenv("OKX_API_KEY", "")
    OKX_SECRET = os.getenv("OKX_SECRET", "")
    OKX_PASSWORD = os.getenv("OKX_PASSWORD", "")
    
    # 交易模式
    TRADE_MODE = os.getenv("TRADE_MODE", "paper")  # paper 或 live
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def load_yaml_config(cls, config_name: str = "trading_config") -> Dict[str, Any]:
        """加载YAML配置文件"""
        config_path = cls.BASE_DIR / "config" / f"{config_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要配置是否完整"""
        required_vars = [
            "DEEPSEEK_API_KEY",
            "OKX_API_KEY",
            "OKX_SECRET",
            "OKX_PASSWORD"
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"缺少必要的环境变量: {', '.join(missing)}")
        
        return True


# 加载交易配置
try:
    _yaml_config = Settings.load_yaml_config()
    
    # 构建TRADE_CONFIG字典（与原代码兼容）
    TRADE_CONFIG = {
        "symbol": _yaml_config["trading"]["symbol"],
        "leverage": _yaml_config["trading"]["leverage"],
        "timeframe": _yaml_config["trading"]["timeframe"],
        "test_mode": _yaml_config["trading"]["test_mode"],
        "data_points": _yaml_config["trading"]["data_points"],
        "analysis_periods": _yaml_config["analysis_periods"],
        "position_management": _yaml_config["position_management"],
        "technical_indicators": _yaml_config["technical_indicators"],
        "sentiment": _yaml_config["sentiment"],
        "risk_management": _yaml_config["risk_management"],
        "execution": _yaml_config["execution"],
    }
    
except Exception as e:
    print(f"加载配置文件失败: {e}")
    # 使用默认配置
    TRADE_CONFIG = {
        "symbol": "DOGE/USDT:USDT",
        "leverage": 5,
        "timeframe": "15m",
        "test_mode": False,
        "data_points": 96,
        "analysis_periods": {
            "short_term": 20,
            "medium_term": 50,
            "long_term": 96
        },
        "position_management": {
            "enable_intelligent_position": True,
            "base_usdt_amount": 1,
            "high_confidence_multiplier": 1.5,
            "medium_confidence_multiplier": 0.5,
            "low_confidence_multiplier": 0.1,
            "max_position_ratio": 0.5,
            "trend_strength_multiplier": 1.1
        },
        "technical_indicators": {
            "sma_periods": [5, 20, 50],
            "ema_fast": 12,
            "ema_slow": 26,
            "macd_signal": 9,
            "rsi_period": 14,
            "bb_period": 20,
            "bb_std": 2,
            "volume_ma_period": 20,
            "support_resistance_lookback": 20
        },
        "sentiment": {
            "enabled": True,
            "api_url": "https://service.cryptoracle.network/openapi/v2/endpoint",
            "api_key": "7ad48a56-8730-4238-a714-eebc30834e3e",
            "lookback_hours": 4,
            "tokens": ["BTC"]
        },
        "risk_management": {
            "min_balance_threshold": 0.5,
            "stop_loss_percentage": 0.02,
            "take_profit_percentage": 0.02,
            "max_daily_trades": 10,
            "cooldown_period_minutes": 15
        },
        "execution": {
            "order_tag": "60bb4a8d3416BCDE",
            "retry_attempts": 2,
            "retry_delay_seconds": 1,
            "position_check_interval": 60
        }
    }
