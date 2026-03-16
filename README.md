# AI量化交易机器人 v2.0

基于 DeepSeek AI 和 OKX 交易所的加密货币量化交易系统。

## 项目特点

- **AI驱动**: 使用 DeepSeek AI 进行市场分析和交易决策
- **实时监控**: WebSocket实时数据流 + Web监控面板
- **数据持久化**: SQLite数据库存储所有交易记录
- **模块化设计**: 清晰的代码结构，易于维护和扩展
- **风险管理**: 内置完善的风险控制机制
- **技术指标**: 支持多种技术分析指标
- **情绪分析**: 集成市场情绪数据
- **日志系统**: 完整的日志记录和轮转
- **单元测试**: 包含核心模块的测试用例
- **OKX官方集成**: 支持OKX AI智能交易工具包

## 项目结构

```
ds/
├── README.md                    # 项目说明
├── requirements.txt             # Python依赖
├── setup.py                     # 包安装配置
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git忽略文件
├── config/                      # 配置模块
│   ├── __init__.py
│   ├── settings.py              # 主配置
│   └── trading_config.yaml      # 交易参数配置
├── src/                         # 源代码
│   ├── __init__.py
│   ├── exchange/                # 交易所模块
│   │   ├── client.py            # 交易所客户端
│   │   └── position.py          # 持仓管理
│   ├── data/                    # 数据模块
│   │   ├── fetcher.py           # 数据获取
│   │   ├── indicators.py        # 技术指标
│   │   └── sentiment.py         # 情绪分析
│   ├── strategy/                # 策略模块
│   │   ├── analyzer.py          # AI分析器
│   │   └── signal.py            # 信号处理
│   ├── trading/                 # 交易模块
│   │   ├── executor.py          # 交易执行
│   │   └── risk.py              # 风险管理
│   ├── database/                # 数据库模块
│   │   ├── __init__.py
│   │   ├── models.py            # 数据模型
│   │   └── manager.py           # 数据库管理
│   ├── websocket/               # WebSocket模块
│   │   ├── __init__.py
│   │   ├── client.py            # WebSocket客户端
│   │   └── manager.py           # WebSocket管理
│   ├── web/                     # Web服务模块
│   │   ├── __init__.py
│   │   ├── app.py               # Flask应用
│   │   ├── templates/           # HTML模板
│   │   │   └── dashboard.html
│   │   └── static/              # 静态资源
│   │       ├── css/
│   │       │   └── style.css
│   │       └── js/
│   │           └── dashboard.js
│   └── utils/                   # 工具模块
│       ├── logger.py            # 日志配置
│       └── helpers.py           # 辅助函数
├── tests/                       # 测试目录
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_signal.py
│   └── test_risk.py
├── scripts/                     # 脚本目录
│   └── run_bot.py               # 启动脚本
├── logs/                        # 日志目录
└── data/                        # 数据目录
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# OKX API配置
OKX_API_KEY=your_okx_api_key_here
OKX_SECRET=your_okx_secret_here
OKX_PASSWORD=your_okx_password_here

# 交易模式
TRADE_MODE=paper  # paper 或 live
LOG_LEVEL=INFO
```

### 3. 配置交易参数

编辑 `config/trading_config.yaml` 文件，调整交易参数：

```yaml
trading:
  symbol: "DOGE/USDT:USDT"  # 交易对
  timeframe: "15m"          # K线周期
  leverage: 5               # 杠杆倍数
  test_mode: false          # 测试模式
```

### 4. 运行机器人

```bash
# 方式1: 直接运行
python scripts/run_bot.py

# 方式2: 使用模块方式运行
python -m scripts.run_bot
```

### 5. 访问监控面板

启动后打开浏览器访问：
- 本地访问: http://localhost:5000
- 实时监控: 支持WebSocket实时数据推送

监控面板功能：
- 实时价格显示和走势图
- 当前持仓和盈亏情况
- 交易记录和信号历史
- 余额变化图表
- 绩效统计数据

## 运行测试

```bash
# 运行所有测试
python -m unittest discover tests

# 运行单个测试文件
python -m unittest tests.test_indicators
python -m unittest tests.test_signal
python -m unittest tests.test_risk
```

## 配置说明

### 交易配置 (trading_config.yaml)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| symbol | 交易对 | DOGE/USDT:USDT |
| timeframe | K线周期 | 15m |
| leverage | 杠杆倍数 | 5 |
| test_mode | 测试模式 | false |
| data_points | 数据点数量 | 96 |

### 仓位管理配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| enable_intelligent_position | 启用智能仓位 | true |
| base_usdt_amount | 基础USDT金额 | 1 |
| high_confidence_multiplier | 高信心倍数 | 1.5 |
| medium_confidence_multiplier | 中信心倍数 | 0.5 |
| low_confidence_multiplier | 低信心倍数 | 0.1 |

### 风险管理配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| min_balance_threshold | 最小余额阈值 | 0.5 USDT |
| stop_loss_percentage | 止损百分比 | 2% |
| take_profit_percentage | 止盈百分比 | 2% |
| max_daily_trades | 每日最大交易次数 | 10 |
| cooldown_period_minutes | 交易冷却期 | 15分钟 |

## 核心模块说明

### 1. ExchangeClient (交易所客户端)

封装了 OKX 交易所的所有操作：
- 账户余额查询
- K线数据获取
- 订单创建和管理
- 持仓查询

### 2. AIAnalyzer (AI分析器)

使用 DeepSeek AI 进行市场分析：
- 技术分析文本生成
- 市场情绪分析
- 交易信号生成
- 支持重试机制

### 3. TechnicalIndicators (技术指标)

计算各种技术指标：
- 移动平均线 (SMA, EMA)
- MACD
- RSI
- 布林带
- 支撑阻力位

### 4. TradeExecutor (交易执行器)

执行交易信号：
- 买入/卖出操作
- 仓位调整
- 平仓/开仓
- 测试模式支持

### 5. RiskManager (风险管理)

风险控制功能：
- 每日交易次数限制
- 交易冷却期
- 信号质量检查
- 止损止盈验证

## 日志系统

日志文件保存在 `logs/` 目录：
- `trading_bot.log` - 所有日志
- `error.log` - 错误日志

日志自动轮转，单个文件最大 10MB，保留 5 个备份。

## 安全注意事项

1. **API密钥安全**: 永远不要将 `.env` 文件提交到 Git
2. **测试模式**: 首次运行请使用 `test_mode: true` 进行测试
3. **资金管理**: 合理设置 `base_usdt_amount` 和杠杆倍数
4. **风险控制**: 建议开启所有风险管理功能

## 扩展开发

### 添加新的技术指标

在 `src/data/indicators.py` 中添加：

```python
@staticmethod
def calculate_custom_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """自定义指标"""
    df['custom'] = ...
    return df
```

### 添加新的交易策略

在 `src/strategy/` 目录创建新文件：

```python
class CustomStrategy:
    def analyze(self, data):
        # 策略逻辑
        return signal
```

## 许可证

MIT License

## 免责声明

**风险提示**: 加密货币交易具有高风险，可能导致资金损失。本项目仅供学习研究使用，不构成投资建议。使用本软件进行交易前，请充分了解相关风险。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v2.0.0 (2024-03)
- **新增**: WebSocket实时数据流
- **新增**: Web监控面板（Flask + SocketIO）
- **新增**: SQLite数据持久化
- **新增**: 实时价格走势图
- **新增**: 余额变化图表
- **新增**: 交易历史记录
- **新增**: 信号历史查询
- **新增**: 绩效统计分析
- **优化**: 集成OKX官方API最佳实践
- **优化**: 更完善的错误处理和重试机制

### v1.0.0 (2024-03)
- 初始版本发布
- 支持 DeepSeek AI 分析
- 集成 OKX 交易所
- 完善的风险管理系统
- 模块化代码架构
