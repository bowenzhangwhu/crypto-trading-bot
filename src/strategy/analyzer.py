"""
AI分析模块
使用DeepSeek进行市场分析
"""
import json
import re
from typing import Dict, Any, Optional, List
from openai import OpenAI
from config.settings import Settings, TRADE_CONFIG
from src.data.sentiment import SentimentAnalyzer
from src.data.indicators import TechnicalIndicators
from src.exchange.position import PositionManager
from src.utils.logger import get_logger
from src.utils.helpers import safe_json_parse

logger = get_logger(__name__)


class AIAnalyzer:
    """AI分析器"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=Settings.DEEPSEEK_API_KEY,
            base_url=Settings.DEEPSEEK_BASE_URL
        )
        self.sentiment_analyzer = SentimentAnalyzer()
        self.position_manager = PositionManager()
        self.signal_history: List[Dict[str, Any]] = []
    
    def analyze_market(self, price_data: Dict[str, Any], 
                      max_retries: int = None) -> Dict[str, Any]:
        """
        使用DeepSeek分析市场
        
        Args:
            price_data: 市场数据
            max_retries: 最大重试次数
        
        Returns:
            交易信号字典
        """
        if max_retries is None:
            max_retries = TRADE_CONFIG['execution']['retry_attempts']
        
        for attempt in range(max_retries + 1):
            try:
                signal_data = self._analyze(price_data)
                
                if signal_data and not signal_data.get('is_fallback', False):
                    # 保存信号到历史
                    self._save_signal(signal_data, price_data['timestamp'])
                    return signal_data
                
                if attempt < max_retries:
                    logger.warning(f"第{attempt + 1}次分析失败，进行重试...")
                    import time
                    time.sleep(TRADE_CONFIG['execution']['retry_delay_seconds'])
                    
            except Exception as e:
                logger.error(f"第{attempt + 1}次分析异常: {e}")
                if attempt == max_retries:
                    return self._create_fallback_signal(price_data)
                import time
                time.sleep(TRADE_CONFIG['execution']['retry_delay_seconds'])
        
        return self._create_fallback_signal(price_data)
    
    def _analyze(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行AI分析"""
        # 生成技术分析文本
        technical_analysis = TechnicalIndicators.generate_analysis_text(price_data)
        
        # 构建K线数据文本
        kline_text = self._build_kline_text(price_data.get('kline_data', []))
        
        # 获取情绪数据
        sentiment_data = self.sentiment_analyzer.fetch_sentiment()
        sentiment_text = self.sentiment_analyzer.format_sentiment_text(sentiment_data)
        
        # 获取持仓信息
        self.position_manager.update()
        position_text = self.position_manager.get_position_text()
        current_pos = self.position_manager.current
        pnl_text = f", 持仓盈亏: {current_pos.unrealized_pnl:.2f} USDT" if current_pos else ""
        
        # 构建提示词
        prompt = self._build_prompt(
            price_data=price_data,
            kline_text=kline_text,
            technical_analysis=technical_analysis,
            sentiment_text=sentiment_text,
            position_text=position_text,
            pnl_text=pnl_text
        )
        
        # 调用DeepSeek API
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": f"您是一位专业的交易员，专注于{TRADE_CONFIG['timeframe']}周期趋势分析。请结合K线形态和技术指标做出判断，并严格遵循JSON格式要求。"
                },
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=0.1
        )
        
        # 解析响应
        result = response.choices[0].message.content
        logger.debug(f"DeepSeek原始回复: {result}")
        
        return self._parse_response(result, price_data)
    
    def _build_kline_text(self, kline_data: List[Dict]) -> str:
        """构建K线文本"""
        text = f"【最近5根{TRADE_CONFIG['timeframe']}K线数据】\n"
        
        for i, kline in enumerate(kline_data[-5:]):
            trend = "阳线" if kline['close'] > kline['open'] else "阴线"
            change = ((kline['close'] - kline['open']) / kline['open']) * 100
            text += f"K线{i + 1}: {trend} 开盘:{kline['open']:.2f} 收盘:{kline['close']:.2f} 涨跌:{change:+.2f}%\n"
        
        return text
    
    def _build_prompt(self, **kwargs) -> str:
        """构建分析提示词"""
        price_data = kwargs['price_data']
        
        # 上次交易信号
        signal_text = ""
        if self.signal_history:
            last_signal = self.signal_history[-1]
            signal_text = f"\n【上次交易信号】\n信号: {last_signal.get('signal', 'N/A')}\n信心: {last_signal.get('confidence', 'N/A')}"
        
        return f"""
你是一个专业的加密货币交易分析师。请基于以下{TRADE_CONFIG['symbol']} {TRADE_CONFIG['timeframe']}周期数据进行分析：

{kwargs['kline_text']}

{kwargs['technical_analysis']}

{signal_text}

{kwargs['sentiment_text']}

【当前行情】
- 当前价格: ${price_data['price']:,.2f}
- 时间: {price_data['timestamp']}
- 本K线最高: ${price_data['high']:,.2f}
- 本K线最低: ${price_data['low']:,.2f}
- 本K线成交量: {price_data['volume']:.2f}
- 价格变化: {price_data['price_change']:+.2f}%
- 当前持仓: {kwargs['position_text']}{kwargs['pnl_text']}

【防频繁交易重要原则】
1. **趋势持续性优先**: 不要因单根K线或短期波动改变整体趋势判断
2. **持仓稳定性**: 除非趋势明确强烈反转，否则保持现有持仓方向
3. **反转确认**: 需要至少2-3个技术指标同时确认趋势反转才改变信号
4. **成本意识**: 减少不必要的仓位调整，每次交易都有成本

【交易指导原则 - 必须遵守】
1. **技术分析主导** (权重60%)：趋势、支撑阻力、K线形态是主要依据
2. **市场情绪辅助** (权重30%)：情绪数据用于验证技术信号，不能单独作为交易理由
3. **风险管理** (权重10%)：考虑持仓、盈亏状况和止损位置
4. **趋势跟随**: 明确趋势出现时立即行动，不要过度等待
5. 因为做的是btc，做多权重可以大一点点
6. **信号明确性**:
   - 强势上涨趋势 → BUY信号
   - 强势下跌趋势 → SELL信号
   - 仅在窄幅震荡、无明确方向时 → HOLD信号
7. **技术指标权重**:
   - 趋势(均线排列) > RSI > MACD > 布林带
   - 价格突破关键支撑/阻力位是重要信号

【当前技术状况分析】
- 整体趋势: {price_data['trend_analysis'].get('overall', 'N/A')}
- 短期趋势: {price_data['trend_analysis'].get('short_term', 'N/A')}
- RSI状态: {price_data['technical_data'].get('rsi', 0):.1f}
- MACD方向: {price_data['trend_analysis'].get('macd', 'N/A')}

【智能仓位管理规则 - 必须遵守】
1. **减少过度保守**：
   - 明确趋势中不要因轻微超买/超卖而过度HOLD
   - RSI在30-70区间属于健康范围
   - 布林带位置在20%-80%属于正常波动区间

2. **趋势跟随优先**：
   - 强势上涨趋势 + 任何RSI值 → 积极BUY信号
   - 强势下跌趋势 + 任何RSI值 → 积极SELL信号
   - 震荡整理 + 无明确方向 → HOLD信号

3. **突破交易信号**：
   - 价格突破关键阻力 + 成交量放大 → 高信心BUY
   - 价格跌破关键支撑 + 成交量放大 → 高信心SELL

4. **持仓优化逻辑**：
   - 已有持仓且趋势延续 → 保持或BUY/SELL信号
   - 趋势明确反转 → 及时反向信号
   - 不要因为已有持仓而过度HOLD

【重要】请基于技术分析做出明确判断，避免因过度谨慎而错过趋势行情！

【分析要求】
基于以上分析，请给出明确的交易信号

请用以下JSON格式回复：
{{
    "signal": "BUY|SELL|HOLD",
    "reason": "简要分析理由(包含趋势判断和技术依据)",
    "stop_loss": 具体价格,
    "take_profit": 具体价格,
    "confidence": "HIGH|MEDIUM|LOW"
}}
"""
    
    def _parse_response(self, result: str, price_data: Dict) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 提取JSON部分
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("响应中未找到JSON")
                return self._create_fallback_signal(price_data)
            
            json_str = result[start_idx:end_idx]
            signal_data = safe_json_parse(json_str)
            
            if signal_data is None:
                logger.warning("JSON解析失败")
                return self._create_fallback_signal(price_data)
            
            # 验证必需字段
            required_fields = ['signal', 'reason', 'stop_loss', 'take_profit', 'confidence']
            if not all(field in signal_data for field in required_fields):
                logger.warning(f"缺少必需字段: {[f for f in required_fields if f not in signal_data]}")
                return self._create_fallback_signal(price_data)
            
            return signal_data
            
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return self._create_fallback_signal(price_data)
    
    def _save_signal(self, signal_data: Dict[str, Any], timestamp: str):
        """保存信号到历史"""
        signal_data['timestamp'] = timestamp
        self.signal_history.append(signal_data)
        
        # 限制历史记录长度
        if len(self.signal_history) > 30:
            self.signal_history.pop(0)
        
        # 信号统计
        signal_type = signal_data['signal']
        signal_count = len([s for s in self.signal_history if s.get('signal') == signal_type])
        total_signals = len(self.signal_history)
        logger.info(f"信号统计: {signal_type} (最近{total_signals}次中出现{signal_count}次)")
        
        # 连续性检查
        if len(self.signal_history) >= 3:
            last_three = [s['signal'] for s in self.signal_history[-3:]]
            if len(set(last_three)) == 1:
                logger.warning(f"注意：连续3次{signal_type}信号")
    
    def _create_fallback_signal(self, price_data: Dict) -> Dict[str, Any]:
        """创建备用信号"""
        return {
            "signal": "HOLD",
            "reason": "因技术分析暂时不可用，采取保守策略",
            "stop_loss": price_data['price'] * 0.98,
            "take_profit": price_data['price'] * 1.02,
            "confidence": "LOW",
            "is_fallback": True
        }
