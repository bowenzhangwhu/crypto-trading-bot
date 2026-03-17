"""
市场情绪数据获取模块
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from config.settings import TRADE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SentimentAnalyzer:
    """情绪分析器"""
    
    def __init__(self):
        self.config = TRADE_CONFIG.get('sentiment', {})
        self.enabled = self.config.get('enabled', True)
    
    def fetch_sentiment(self) -> Optional[Dict[str, Any]]:
        """获取市场情绪指标"""
        if not self.enabled:
            logger.debug("情绪分析已禁用")
            return None
        
        try:
            api_url = self.config.get('api_url')
            api_key = self.config.get('api_key')
            lookback_hours = self.config.get('lookback_hours', 4)
            tokens = self.config.get('tokens', ['BTC'])
            
            # 获取时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=lookback_hours)
            
            request_body = {
                "apiKey": api_key,
                "endpoints": ["CO-A-02-01", "CO-A-02-02"],
                "startTime": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "timeType": "15m",
                "token": tokens
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": api_key
            }
            
            logger.debug("正在获取情绪数据...")
            response = requests.post(api_url, json=request_body, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"情绪API返回错误: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get("code") != 200 or not data.get("data"):
                logger.warning("情绪数据格式错误")
                return None
            
            # 解析数据
            time_periods = data["data"][0]["timePeriods"]
            
            for period in time_periods:
                period_data = period.get("data", [])
                sentiment = {}
                valid_data_found = False
                
                for item in period_data:
                    endpoint = item.get("endpoint")
                    value = item.get("value", "").strip()
                    
                    if value:
                        try:
                            if endpoint in ["CO-A-02-01", "CO-A-02-02"]:
                                sentiment[endpoint] = float(value)
                                valid_data_found = True
                        except (ValueError, TypeError):
                            continue
                
                if valid_data_found and "CO-A-02-01" in sentiment and "CO-A-02-02" in sentiment:
                    positive = sentiment['CO-A-02-01']
                    negative = sentiment['CO-A-02-02']
                    net_sentiment = positive - negative
                    
                    # 计算数据延迟
                    data_time = datetime.strptime(period['startTime'], '%Y-%m-%d %H:%M:%S')
                    data_delay = int((datetime.now() - data_time).total_seconds() // 60)
                    
                    logger.info(f"情绪数据时间: {period['startTime']} (延迟: {data_delay}分钟)")
                    
                    return {
                        'positive_ratio': positive,
                        'negative_ratio': negative,
                        'net_sentiment': net_sentiment,
                        'data_time': period['startTime'],
                        'data_delay_minutes': data_delay
                    }
            
            logger.warning("所有时间段数据都为空")
            return None
            
        except requests.exceptions.Timeout:
            logger.warning("获取情绪数据超时")
            return None
        except Exception as e:
            logger.error(f"情绪指标获取失败: {e}")
            return None
    
    def format_sentiment_text(self, sentiment_data: Optional[Dict[str, Any]]) -> str:
        """格式化情绪文本"""
        if not sentiment_data:
            return "【市场情绪】数据暂不可用"
        
        sign = '+' if sentiment_data['net_sentiment'] >= 0 else ''
        return (f"【市场情绪】"
                f"乐观{sentiment_data['positive_ratio']:.1%} "
                f"悲观{sentiment_data['negative_ratio']:.1%} "
                f"净值{sign}{sentiment_data['net_sentiment']:.3f}")
