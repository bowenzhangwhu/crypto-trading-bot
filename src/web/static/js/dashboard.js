/**
 * 监控面板JavaScript
 */

// 全局变量
let socket;
let priceChart;
let balanceChart;
let priceHistory = [];
let balanceHistory = [];

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initSocket();
    initCharts();
    startDataUpdates();
    updateTime();
    setInterval(updateTime, 1000);
});

// 初始化WebSocket连接
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket已连接');
        updateConnectionStatus(true);
        socket.emit('subscribe', { channel: 'all' });
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket已断开');
        updateConnectionStatus(false);
    });
    
    socket.on('market_data', function(data) {
        handleMarketData(data);
    });
    
    socket.on('position_update', function(data) {
        handlePositionUpdate(data);
    });
}

// 初始化图表
function initCharts() {
    // 价格图表
    const priceLayout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#9CA3AF' },
        xaxis: { 
            gridcolor: '#374151',
            showgrid: true
        },
        yaxis: { 
            gridcolor: '#374151',
            showgrid: true,
            side: 'right'
        },
        margin: { t: 10, r: 50, b: 30, l: 30 },
        showlegend: false
    };
    
    Plotly.newPlot('price-chart', [{
        x: [],
        y: [],
        type: 'scatter',
        mode: 'lines',
        line: { color: '#3B82F6', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(59, 130, 246, 0.1)'
    }], priceLayout, { responsive: true });
    
    // 余额图表
    const balanceLayout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#9CA3AF' },
        xaxis: { 
            gridcolor: '#374151',
            showgrid: true
        },
        yaxis: { 
            gridcolor: '#374151',
            showgrid: true,
            side: 'right'
        },
        margin: { t: 10, r: 50, b: 30, l: 30 },
        showlegend: false
    };
    
    Plotly.newPlot('balance-chart', [{
        x: [],
        y: [],
        type: 'scatter',
        mode: 'lines',
        line: { color: '#10B981', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(16, 185, 129, 0.1)'
    }], balanceLayout, { responsive: true });
}

// 处理市场数据
function handleMarketData(data) {
    if (data.ticker) {
        const ticker = Object.values(data.ticker)[0];
        if (ticker) {
            updatePriceDisplay(ticker);
            
            // 更新价格历史
            priceHistory.push({
                time: new Date(),
                price: ticker.price
            });
            
            // 只保留最近100个点
            if (priceHistory.length > 100) {
                priceHistory.shift();
            }
            
            updatePriceChart();
        }
    }
}

// 处理持仓更新
function handlePositionUpdate(data) {
    updatePositionDisplay(data);
}

// 更新价格显示
function updatePriceDisplay(ticker) {
    const priceEl = document.getElementById('current-price');
    const changeEl = document.getElementById('price-change');
    
    priceEl.textContent = '$' + formatNumber(ticker.price);
    
    if (ticker.change_24h !== undefined) {
        const change = ((ticker.price - ticker.change_24h) / ticker.change_24h * 100);
        const changeText = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
        changeEl.textContent = '24h: ' + changeText;
        changeEl.className = 'text-sm mt-2 ' + (change >= 0 ? 'price-up' : 'price-down');
    }
}

// 更新持仓显示
function updatePositionDisplay(position) {
    const sideEl = document.getElementById('position-side');
    const sizeEl = document.getElementById('position-size');
    const pnlEl = document.getElementById('unrealized-pnl');
    const entryEl = document.getElementById('entry-price');
    
    if (position && position.size > 0) {
        sideEl.textContent = position.side === 'long' ? '做多' : '做空';
        sideEl.className = 'text-3xl font-bold ' + 
            (position.side === 'long' ? 'price-up' : 'price-down');
        
        sizeEl.textContent = position.size.toFixed(4) + ' 张';
        
        const pnl = position.unrealized_pnl || 0;
        pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + formatNumber(pnl);
        pnlEl.className = 'text-3xl font-bold ' + (pnl >= 0 ? 'price-up' : 'price-down');
        
        entryEl.textContent = '入场价: $' + formatNumber(position.entry_price);
    } else {
        sideEl.textContent = '无持仓';
        sideEl.className = 'text-3xl font-bold text-gray-500';
        sizeEl.textContent = '--';
        pnlEl.textContent = '--';
        pnlEl.className = 'text-3xl font-bold';
        entryEl.textContent = '--';
    }
}

// 更新价格图表
function updatePriceChart() {
    const times = priceHistory.map(p => p.time);
    const prices = priceHistory.map(p => p.price);
    
    Plotly.react('price-chart', [{
        x: times,
        y: prices,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#3B82F6', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(59, 130, 246, 0.1)'
    }]);
}

// 更新余额图表
function updateBalanceChart(data) {
    if (!data || data.length === 0) return;
    
    const times = data.map(d => new Date(d.recorded_at));
    const balances = data.map(d => d.available);
    
    Plotly.react('balance-chart', [{
        x: times,
        y: balances,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#10B981', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(16, 185, 129, 0.1)'
    }]);
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.innerHTML = '<span class="w-3 h-3 bg-green-500 rounded-full mr-2"></span><span class="text-sm">已连接</span>';
    } else {
        statusEl.innerHTML = '<span class="w-3 h-3 bg-red-500 rounded-full mr-2"></span><span class="text-sm">已断开</span>';
    }
}

// 更新时间
function updateTime() {
    const timeEl = document.getElementById('current-time');
    const now = new Date();
    timeEl.textContent = now.toLocaleString('zh-CN');
}

// 开始数据更新
function startDataUpdates() {
    // 立即获取一次数据
    fetchAllData();
    
    // 定期更新
    setInterval(fetchAllData, 5000);
}

// 获取所有数据
async function fetchAllData() {
    try {
        // 获取持仓
        const positionRes = await fetch('/api/position');
        if (positionRes.ok) {
            const position = await positionRes.json();
            updatePositionDisplay(position);
        }
        
        // 获取交易记录
        const tradesRes = await fetch('/api/trades?limit=10');
        if (tradesRes.ok) {
            const trades = await tradesRes.json();
            updateTradesTable(trades);
        }
        
        // 获取信号
        const signalsRes = await fetch('/api/signals?limit=10');
        if (signalsRes.ok) {
            const signals = await signalsRes.json();
            updateSignalsTable(signals);
        }
        
        // 获取余额历史
        const balanceRes = await fetch('/api/balance/history?hours=24');
        if (balanceRes.ok) {
            const balanceData = await balanceRes.json();
            updateBalanceChart(balanceData);
        }
        
        // 获取绩效统计
        const perfRes = await fetch('/api/performance');
        if (perfRes.ok) {
            const perf = await perfRes.json();
            updatePerformance(perf);
        }
        
    } catch (error) {
        console.error('获取数据失败:', error);
    }
}

// 更新交易表格
function updateTradesTable(trades) {
    const tbody = document.getElementById('trades-table');
    
    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-500">暂无交易记录</td></tr>';
        return;
    }
    
    tbody.innerHTML = trades.map(trade => `
        <tr class="border-b border-gray-700">
            <td class="py-2">${formatTime(trade.created_at)}</td>
            <td class="py-2">
                <span class="${trade.side === 'buy' ? 'price-up' : 'price-down'}">
                    ${trade.side === 'buy' ? '买入' : '卖出'}
                </span>
            </td>
            <td class="py-2 text-right">${trade.amount.toFixed(4)}</td>
            <td class="py-2 text-right">$${formatNumber(trade.filled_price || trade.price)}</td>
            <td class="py-2 text-right ${(trade.pnl || 0) >= 0 ? 'price-up' : 'price-down'}">
                ${trade.pnl ? (trade.pnl >= 0 ? '+' : '') + '$' + formatNumber(trade.pnl) : '--'}
            </td>
        </tr>
    `).join('');
}

// 更新信号表格
function updateSignalsTable(signals) {
    const tbody = document.getElementById('signals-table');
    
    if (signals.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="py-4 text-center text-gray-500">暂无信号</td></tr>';
        return;
    }
    
    tbody.innerHTML = signals.map(signal => `
        <tr class="border-b border-gray-700">
            <td class="py-2">${formatTime(signal.created_at)}</td>
            <td class="py-2">
                <span class="signal-${signal.signal_type.toLowerCase()}">
                    ${signal.signal_type === 'BUY' ? '买入' : signal.signal_type === 'SELL' ? '卖出' : '观望'}
                </span>
            </td>
            <td class="py-2 confidence-${signal.confidence?.toLowerCase()}">
                ${signal.confidence === 'HIGH' ? '高' : signal.confidence === 'MEDIUM' ? '中' : '低'}
            </td>
            <td class="py-2 text-gray-400 truncate max-w-xs" title="${signal.reason || ''}">
                ${signal.reason || '--'}
            </td>
        </tr>
    `).join('');
}

// 更新绩效显示
function updatePerformance(perf) {
    document.getElementById('total-trades').textContent = perf.total_trades || 0;
    document.getElementById('win-rate').textContent = (perf.win_rate || 0).toFixed(1) + '%';
    document.getElementById('total-pnl').textContent = '$' + formatNumber(perf.total_pnl || 0);
    document.getElementById('profitable-trades').textContent = perf.profitable_trades || 0;
    
    // 今日盈亏
    const todayPnlEl = document.getElementById('today-pnl');
    const todayTradesEl = document.getElementById('today-trades');
    
    if (perf.today_pnl !== undefined) {
        todayPnlEl.textContent = (perf.today_pnl >= 0 ? '+' : '') + '$' + formatNumber(perf.today_pnl);
        todayPnlEl.className = 'text-3xl font-bold ' + (perf.today_pnl >= 0 ? 'price-up' : 'price-down');
    }
    
    if (perf.today_trades !== undefined) {
        todayTradesEl.textContent = `今日交易: ${perf.today_trades} 次`;
    }
}

// 格式化数字
function formatNumber(num) {
    if (num === undefined || num === null) return '--';
    return num.toLocaleString('en-US', { 
        minimumFractionDigits: 2, 
        maximumFractionDigits: 2 
    });
}

// 格式化时间
function formatTime(timeStr) {
    if (!timeStr) return '--';
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}
