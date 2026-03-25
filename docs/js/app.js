// docs/js/app.js

// ==================== 全局变量 ====================
let historyData = [];
let analysisData = {};
let predictionsData = {};
let backtestData = {};
let historyDisplayCount = 20;
let charts = {};
let currentPredictionType = 'single';  // 'single' 或 'duplex'

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', async () => {
    await loadAllData();
    initializeUI();
});

async function loadAllData() {
    try {
        const [history, analysis, predictions, backtest] = await Promise.all([
            fetchJSON('data/history.json'),
            fetchJSON('data/analysis.json'),
            fetchJSON('data/predictions.json'),
            fetchJSON('data/backtest.json').catch(() => null)
        ]);
        
        historyData = history || [];
        analysisData = analysis || {};
        predictionsData = predictions || {};
        backtestData = backtest || {};
        
    } catch (error) {
        console.error('加载数据失败:', error);
    }
}

async function fetchJSON(url) {
    const response = await fetch(url + '?t=' + Date.now());
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

// ==================== UI 初始化 ====================
function initializeUI() {
    updateHeader();
    renderLatestDraw();
    renderPredictions();
    renderStatistics();
    renderHotColdNumbers();
}

function updateHeader() {
    const updateTime = predictionsData.generated_at || analysisData.updated_at;
    if (updateTime) {
        document.getElementById('lastUpdate').textContent = 
            new Date(updateTime).toLocaleString('zh-CN', {
                month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
            });
        document.getElementById('lastUpdate').classList.remove('loading');
    }
    document.getElementById('totalRecords').textContent = historyData.length || '-';
}

function renderLatestDraw() {
    if (!historyData.length) return;
    
    const latest = historyData[historyData.length - 1];
    document.getElementById('latestPeriod').textContent = `第 ${latest.period} 期`;
    
    const numbersHtml = `
        ${latest.red.map(n => `<span class="ball ball-red">${pad(n)}</span>`).join('')}
        <span class="mx-1 text-white/50">|</span>
        <span class="ball ball-blue">${pad(latest.blue)}</span>
    `;
    document.getElementById('latestNumbers').innerHTML = numbersHtml;
}

// ==================== 预测类型切换 ====================
function switchPredictionType(type) {
    currentPredictionType = type;
    
    // 更新按钮样式
    ['single', 'duplex', 'fortune'].forEach(t => {
        const btn = document.getElementById(`btn-${t}`);
        if (btn) {
            btn.classList.toggle('bg-blue-500', type === t);
            btn.classList.toggle('text-white', type === t);
            btn.classList.toggle('bg-gray-200', type !== t);
            btn.classList.toggle('text-slate-600', type !== t);
        }
    });
    
    renderPredictions();
}

function renderPredictions() {
    const container = document.getElementById('predictions');
    
    let predictions, description;
    
    if (currentPredictionType === 'fortune' && predictionsData.fortune) {
        predictions = predictionsData.fortune.predictions;
        description = predictionsData.fortune.description;
    } else if (currentPredictionType === 'duplex' && predictionsData.duplex) {
        predictions = predictionsData.duplex.predictions;
        description = predictionsData.duplex.description;
    } else if (predictionsData.single) {
        predictions = predictionsData.single.predictions;
        description = predictionsData.single.description;
    } else {
        predictions = predictionsData.predictions;
        description = '单式投注 (6红1蓝)';
    }
    
    if (!predictions?.length) {
        container.innerHTML = '<div class="text-center py-6 text-slate-400">暂无预测数据</div>';
        return;
    }
    
    document.getElementById('predBasedOn').textContent = 
        `${description} | 基于第${predictionsData.based_on_period}期`;
    
    container.innerHTML = predictions.map(pred => {
        const blue = pred.blue;
        const isMultiBlue = Array.isArray(blue);
        const meta = pred.meta || {};
        const isFortune = meta.method === 'fortune_optimized';
        
        return `
        <div class="border ${isFortune ? 'border-amber-200 bg-amber-50/50' : 'border-slate-100'} rounded-xl p-4 hover:shadow-md transition">
            <div class="flex flex-wrap justify-between items-start gap-2 mb-3">
                <div>
                    <span class="font-bold text-slate-700">方案 ${pred.id}</span>
                    <span class="ml-2 text-xs px-2 py-0.5 ${isFortune ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'} rounded-full">
                        ${pred.strategy}
                    </span>
                    ${isFortune ? '<span class="ml-1 text-xs">🎰</span>' : ''}
                    ${isMultiBlue ? '<span class="ml-1 text-xs px-2 py-0.5 bg-blue-100 text-blue-600 rounded-full">复式</span>' : ''}
                </div>
                <div class="text-xs text-slate-400 flex gap-3 flex-wrap">
                    <span>和值: ${pred.sum}</span>
                    <span>跨度: ${pred.span}</span>
                    <span>区间: ${pred.zone_dist}</span>
                    ${meta.combination_score ? `<span class="text-amber-600">评分: ${meta.combination_score}</span>` : ''}
                </div>
            </div>
            
            <div class="flex flex-wrap items-center gap-1">
                ${pred.red.map(n => `<span class="ball ball-red">${pad(n)}</span>`).join('')}
                <span class="mx-2 text-slate-300">|</span>
                ${isMultiBlue 
                    ? blue.map(n => `<span class="ball ball-blue">${pad(n)}</span>`).join('')
                    : `<span class="ball ball-blue">${pad(blue)}</span>`
                }
            </div>
            
            ${pred.red_count > 6 || (isMultiBlue && blue.length > 1) ? `
            <div class="mt-2 text-xs text-slate-400">
                📝 ${meta.expand_notes || `${pred.red_count}红${isMultiBlue ? blue.length : 1}蓝`}
            </div>
            ` : ''}
            
            ${isFortune && meta.fortune_prize ? `
            <div class="mt-2 p-2 bg-amber-100/50 rounded-lg text-xs">
                <div class="font-medium text-amber-700 mb-1">🎰 福运奖收益测算</div>
                <div class="text-amber-600">
                    ${meta.fortune_prize.x3_y0_scenario} 
                    <span class="ml-2">(成本${meta.fortune_prize.cost})</span>
                </div>
            </div>
            ` : ''}
            
            ${isFortune && meta.red_structure ? `
            <div class="mt-2 text-xs text-slate-500 flex flex-wrap gap-x-4 gap-y-1">
                <span>冷号: ${meta.red_structure.cold_numbers?.join(',') || '-'}</span>
                <span>温号: ${meta.red_structure.warm_numbers?.join(',') || '-'}</span>
                <span>热号: ${meta.red_structure.hot_numbers?.join(',') || '-'}</span>
            </div>
            ` : ''}
        </div>
        `;
    }).join('');
}

// 计算复式注数
function calculateBets(redCount, blueCount) {
    const redBets = combination(redCount, 6);
    return redBets * blueCount;
}

// 组合数 C(n, k)
function combination(n, k) {
    if (k > n) return 0;
    if (k === 0 || k === n) return 1;
    
    let result = 1;
    for (let i = 0; i < k; i++) {
        result = result * (n - i) / (i + 1);
    }
    return Math.round(result);
}

// ==================== 其他渲染函数 ====================

function renderStatistics() {
    const stats = analysisData.statistics;
    if (!stats) return;
    
    document.getElementById('stat-sum').textContent = stats.sum?.mean || '-';
    document.getElementById('stat-span').textContent = stats.span?.mean || '-';
    document.getElementById('stat-odd').textContent = stats.odd_ratio ? 
        `${(stats.odd_ratio * 100).toFixed(0)}%` : '-';
    document.getElementById('stat-big').textContent = stats.big_ratio ? 
        `${(stats.big_ratio * 100).toFixed(0)}%` : '-';
    document.getElementById('stat-zone').textContent = stats.zone_avg ? 
        stats.zone_avg.map(z => z.toFixed(1)).join(' : ') : '-';
}

function renderHotColdNumbers() {
    const freq = analysisData.frequency_50?.red;
    if (freq) {
        const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]);
        const hot = sorted.slice(0, 6);
        document.getElementById('hot-numbers').innerHTML = 
            hot.map(([n, c]) => `
                <span class="ball ball-small ball-red" title="出现${c}次">${pad(n)}</span>
            `).join('');
    }
    
    const missing = analysisData.missing?.red;
    if (missing) {
        const sorted = Object.entries(missing).sort((a, b) => b[1] - a[1]);
        const cold = sorted.slice(0, 6);
        document.getElementById('cold-numbers').innerHTML = 
            cold.map(([n, m]) => `
                <span class="ball ball-small ball-gray" title="遗漏${m}期">${pad(n)}</span>
            `).join('');
    }
    
    const rising = analysisData.trends?.rising;
    if (rising) {
        document.getElementById('rising-numbers').innerHTML = 
            rising.map(item => `
                <span class="ball ball-small" style="background: linear-gradient(145deg, #10b981, #059669); color: white;" 
                      title="趋势+${(item.trend*100).toFixed(1)}%">
                    ${pad(item.num)}
                </span>
            `).join('');
    }
}

// ==================== 标签切换 ====================
function showTab(tabName) {
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(t => {
        t.classList.remove('active');
        t.classList.add('text-slate-500');
    });
    
    const page = document.getElementById(`page-${tabName}`);
    page.classList.remove('hidden');
    page.classList.add('fade-in');
    
    const tab = document.getElementById(`tab-${tabName}`);
    tab.classList.add('active');
    tab.classList.remove('text-slate-500');
    
    if (tabName === 'analysis') {
        setTimeout(renderCharts, 100);
    } else if (tabName === 'history') {
        renderHistory();
    } else if (tabName === 'backtest') {
        renderBacktest();
    }
}

// ==================== 图表 ====================
function renderCharts() {
    Object.values(charts).forEach(c => c?.destroy());
    
    const redFreq = analysisData.frequency_50?.red;
    if (redFreq) {
        charts.red = new Chart(document.getElementById('redFreqChart'), {
            type: 'bar',
            data: {
                labels: Object.keys(redFreq),
                datasets: [{
                    data: Object.values(redFreq),
                    backgroundColor: Object.values(redFreq).map(v => 
                        v >= 8 ? 'rgba(239,68,68,0.8)' : 
                        v >= 5 ? 'rgba(239,68,68,0.5)' : 'rgba(239,68,68,0.3)'
                    ),
                    borderRadius: 4
                }]
            },
            options: chartOptions('次数')
        });
    }
    
    const blueFreq = analysisData.frequency_50?.blue;
    if (blueFreq) {
        charts.blue = new Chart(document.getElementById('blueFreqChart'), {
            type: 'bar',
            data: {
                labels: Object.keys(blueFreq),
                datasets: [{
                    data: Object.values(blueFreq),
                    backgroundColor: 'rgba(59,130,246,0.6)',
                    borderRadius: 4
                }]
            },
            options: chartOptions('次数')
        });
    }
    
    const missing = analysisData.missing?.red;
    if (missing) {
        charts.missing = new Chart(document.getElementById('missingChart'), {
            type: 'bar',
            data: {
                labels: Object.keys(missing),
                datasets: [{
                    data: Object.values(missing),
                    backgroundColor: Object.values(missing).map(v =>
                        v >= 20 ? 'rgba(239,68,68,0.7)' :
                        v >= 10 ? 'rgba(251,146,60,0.7)' : 'rgba(34,197,94,0.7)'
                    ),
                    borderRadius: 4
                }]
            },
            options: chartOptions('期数')
        });
    }
    
    if (historyData.length >= 10) {
        const recent = historyData.slice(-30);
        charts.sum = new Chart(document.getElementById('sumTrendChart'), {
            type: 'line',
            data: {
                labels: recent.map(r => r.period.slice(-3)),
                datasets: [{
                    data: recent.map(r => r.red.reduce((a, b) => a + b, 0)),
                    borderColor: 'rgb(139,92,246)',
                    backgroundColor: 'rgba(139,92,246,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3
                }]
            },
            options: { ...chartOptions('和值'), plugins: { legend: { display: false } } }
        });
    }
}

function chartOptions(yLabel) {
    return {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, title: { display: true, text: yLabel } } }
    };
}

// ==================== 历史记录 ====================
function renderHistory() {
    const container = document.getElementById('history-list');
    const records = historyData.slice().reverse().slice(0, historyDisplayCount);
    
    if (!records.length) {
        container.innerHTML = '<div class="text-center py-6 text-slate-400">暂无数据</div>';
        return;
    }
    
    container.innerHTML = records.map(r => `
        <div class="flex flex-wrap items-center justify-between py-2 px-3 rounded-lg hover:bg-slate-50 gap-2">
            <div class="flex items-center gap-3">
                <span class="text-sm font-medium text-slate-500 w-20">${r.period}</span>
                <div class="flex items-center gap-0.5">
                    ${r.red.map(n => `<span class="ball ball-small ball-red">${pad(n)}</span>`).join('')}
                    <span class="ball ball-small ball-blue ml-1">${pad(r.blue)}</span>
                </div>
            </div>
            <span class="text-xs text-slate-400">${r.date}</span>
        </div>
    `).join('');
    
    document.getElementById('load-more-btn').style.display = 
        historyDisplayCount >= historyData.length ? 'none' : 'block';
}

function loadMoreHistory() {
    historyDisplayCount += 20;
    renderHistory();
}

// ==================== 回测相关 ====================
let currentBacktestType = 'single';

function switchBacktestType(type) {
    currentBacktestType = type;
    
    // 更新按钮样式
    ['single', 'duplex', 'fortune'].forEach(t => {
        const btn = document.getElementById(`bt-btn-${t}`);
        if (btn) {
            btn.classList.toggle('bg-blue-500', type === t);
            btn.classList.toggle('text-white', type === t);
            btn.classList.toggle('bg-gray-200', type !== t);
            btn.classList.toggle('text-slate-600', type !== t);
        }
    });
    
    // 切换显示内容
    const commonEl = document.getElementById('backtest-common');
    const fortuneEl = document.getElementById('backtest-fortune');
    
    if (type === 'fortune') {
        commonEl?.classList.add('hidden');
        fortuneEl?.classList.remove('hidden');
        renderFortuneBacktest();
    } else {
        commonEl?.classList.remove('hidden');
        fortuneEl?.classList.add('hidden');
        renderBacktest();
    }
}

function renderBacktest() {
    if (!backtestData) return;
    
    let data, title, ballCount;
    
    if (currentBacktestType === 'duplex' && backtestData.duplex) {
        data = backtestData.duplex;
        title = '复式回测 (7红3蓝)';
        ballCount = '7红3蓝';
    } else if (backtestData.single) {
        data = backtestData.single;
        title = '单式回测 (6红1蓝)';
        ballCount = '6红1蓝';
    } else {
        return;
    }
    
    const best = data.best_strategy || {};
    const randomBaseline = data.random_baseline || 1.09;
    const improvement = best.avg_red_match - randomBaseline;
    const improvementPercent = (improvement / randomBaseline * 100).toFixed(1);
    
    const bestData = data.strategies?.[best.name] || {};
    const blueAccuracy = bestData.blue_accuracy || 0;
    
    // 更新UI
    document.getElementById('bt-title').textContent = title;
    document.getElementById('bt-strategy').textContent = best.avg_red_match?.toFixed(2) || '-';
    document.getElementById('bt-strategy-name').textContent = best.name || '-';
    document.getElementById('bt-random').textContent = randomBaseline.toFixed(2);
    document.getElementById('bt-improve').textContent = `${improvement > 0 ? '+' : ''}${improvementPercent}%`;
    document.getElementById('bt-blue').textContent = `${(blueAccuracy * 100).toFixed(1)}%`;
    
    renderStrategyRanking(data.ranking, randomBaseline);
    renderBacktestChart(bestData.distribution || {}, best.name);
    renderBacktestDetails(bestData.details || []);
}

function renderFortuneBacktest() {
    const fortune = backtestData?.fortune;
    if (!fortune) {
        document.getElementById('backtest-fortune').innerHTML = 
            '<div class="card p-8 text-center text-slate-400">暂无福运优化回测数据</div>';
        return;
    }
    
    const ms = fortune.match_stats || {};
    const fs = fortune.fortune_stats || {};
    const ps = fortune.profit_stats || {};
    
    // 核心指标
    document.getElementById('ft-red-match').textContent = ms.avg_red_match?.toFixed(2) || '-';
    document.getElementById('ft-trigger-rate').textContent = `${fs.eligible_rate || 0}%`;
    document.getElementById('ft-profit-rate').textContent = `${ps.profit_rate || 0}%`;
    document.getElementById('ft-roi').textContent = `${ps.roi > 0 ? '+' : ''}${ps.roi || 0}%`;
    
    // 收益分析
    document.getElementById('ft-total-cost').textContent = `${(ps.total_cost || 0).toLocaleString()}元`;
    document.getElementById('ft-fortune-income').textContent = `${(ps.total_fortune || 0).toLocaleString()}元`;
    document.getElementById('ft-regular-income').textContent = `${(ps.total_regular_prize || 0).toLocaleString()}元`;
    
    const netProfit = ps.net_profit || 0;
    const netProfitEl = document.getElementById('ft-net-profit');
    netProfitEl.textContent = `${netProfit > 0 ? '+' : ''}${netProfit.toLocaleString()}元`;
    netProfitEl.className = `text-lg font-bold ${netProfit >= 0 ? 'text-green-600' : 'text-red-600'}`;
    
    const fortuneContrib = fortune.summary?.fortune_contribution || 0;
    document.getElementById('ft-fortune-contrib').textContent = `${fortuneContrib}%`;
    
    document.getElementById('ft-periods').textContent = `${fortune.test_periods || 0}期`;
    
    // 渲染图表
    renderFortuneChart(fortune);
    
    // 渲染详情
    renderFortuneDetails(fortune.details || []);
}

function renderFortuneChart(fortune) {
    if (charts.fortune) charts.fortune.destroy();
    
    const ctx = document.getElementById('fortuneChart');
    if (!ctx) return;
    
    const dist = fortune.match_stats?.distribution || {};
    const fortuneByMatch = fortune.fortune_by_red_match || {};
    
    const labels = ['0', '1', '2', '3', '4', '5', '6', '7'];
    const matchCounts = labels.map(k => dist[k] || 0);
    const fortuneCounts = labels.map(k => fortuneByMatch[parseInt(k)]?.fortune_eligible || 0);
    
    charts.fortune = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '命中期数',
                    data: matchCounts,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderRadius: 4,
                    order: 2
                },
                {
                    label: '触发福运奖',
                    data: fortuneCounts,
                    backgroundColor: 'rgba(245, 158, 11, 0.8)',
                    borderRadius: 4,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true },
            },
            scales: {
                x: { 
                    title: { display: true, text: '红球命中数' },
                    stacked: false
                },
                y: { 
                    beginAtZero: true,
                    title: { display: true, text: '期数' }
                }
            }
        }
    });
}

function renderFortuneDetails(details) {
    const container = document.getElementById('fortune-details');
    if (!container) return;
    
    if (!details?.length) {
        container.innerHTML = '<p class="text-slate-400">暂无详情</p>';
        return;
    }
    
    container.innerHTML = details.map(d => {
        const predBlue = Array.isArray(d.predicted_blue) ? d.predicted_blue : [d.predicted_blue];
        const blueHit = predBlue.includes(d.actual_blue);
        const isFortune = d.fortune_eligible;
        const hasProfit = (d.fortune_amount + d.prize_amount) >= 42;
        
        return `
        <div class="flex flex-wrap items-center gap-2 py-2 px-3 rounded 
                    ${isFortune ? 'bg-amber-50 border border-amber-200' : 
                      hasProfit ? 'bg-green-50' : 'bg-slate-50'}">
            <span class="text-slate-500 text-xs w-16">${d.period}</span>
            
            <div class="flex items-center gap-0.5">
                ${d.predicted_red.slice(0, 7).map(n => {
                    const hit = d.actual_red.includes(n);
                    return `<span class="w-5 h-5 rounded-full text-xs flex items-center justify-center 
                        ${hit ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-400'}">${n}</span>`;
                }).join('')}
            </div>
            
            <span class="text-slate-300 mx-1">|</span>
            
            <div class="flex items-center gap-0.5">
                ${predBlue.map(n => {
                    const hit = n === d.actual_blue;
                    return `<span class="w-5 h-5 rounded-full text-xs flex items-center justify-center 
                        ${hit ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-400'}">${n}</span>`;
                }).join('')}
            </div>
            
            <span class="ml-auto text-xs flex items-center gap-2">
                <span class="${d.red_match >= 3 ? 'text-green-600 font-bold' : 'text-slate-500'}">
                    ${d.red_match}红${blueHit ? '+蓝' : ''}
                </span>
                ${isFortune ? `<span class="text-amber-600 font-bold">🎰 +${d.fortune_amount}元</span>` : ''}
                ${d.prize_amount > 0 ? `<span class="text-blue-500">+${d.prize_amount}元</span>` : ''}
            </span>
        </div>
        `;
    }).join('');
}

// 保持原有的 renderStrategyRanking, renderBacktestChart, renderBacktestDetails 函数不变

function renderStrategyRanking(ranking, randomBaseline) {
    const container = document.getElementById('strategy-ranking');
    if (!container || !ranking?.length) {
        if (container) container.innerHTML = '<p class="text-slate-400 text-sm">暂无数据</p>';
        return;
    }
    
    container.innerHTML = ranking.map(([name, score], i) => {
        const vsRandom = score - randomBaseline;
        const isFirst = i === 0;
        const maxScore = ranking[0][1];
        const barWidth = Math.max(20, (score / maxScore) * 100);
        
        return `
        <div class="flex items-center gap-2 py-2 ${isFirst ? 'bg-yellow-50 -mx-2 px-2 rounded-lg' : ''}">
            <span class="w-5 text-center font-bold text-sm ${isFirst ? 'text-yellow-500' : 'text-slate-400'}">
                ${isFirst ? '👑' : i + 1}
            </span>
            <span class="w-16 text-xs font-medium text-slate-700 truncate">${name}</span>
            <div class="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all ${isFirst ? 'bg-yellow-400' : 'bg-blue-400'}" 
                     style="width: ${barWidth}%"></div>
            </div>
            <span class="w-10 text-right text-xs font-bold ${isFirst ? 'text-yellow-600' : 'text-slate-600'}">
                ${score.toFixed(2)}
            </span>
            <span class="w-12 text-right text-xs ${vsRandom >= 0 ? 'text-green-500' : 'text-red-500'}">
                ${vsRandom >= 0 ? '+' : ''}${vsRandom.toFixed(2)}
            </span>
        </div>
        `;
    }).join('');
}

function renderBacktestChart(distribution, strategyName) {
    if (charts.backtest) charts.backtest.destroy();
    
    const ctx = document.getElementById('backtestChart');
    if (!ctx) return;
    
    // 处理分布数据
    const dist = distribution || {};
    const maxKey = Math.max(...Object.keys(dist).map(Number), 6);
    const labels = Array.from({length: maxKey + 1}, (_, i) => String(i));
    const values = labels.map(k => dist[k] || 0);
    
    charts.backtest = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `${strategyName || '策略'} 命中分布`,
                data: values,
                backgroundColor: labels.map((_, i) => {
                    if (i >= 6) return 'rgba(6,182,212,0.8)';
                    if (i >= 4) return 'rgba(34,197,94,0.7)';
                    if (i >= 3) return 'rgba(234,179,8,0.6)';
                    return 'rgba(239,68,68,0.5)';
                }),
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: `最佳策略: ${strategyName || '-'}`
                }
            },
            scales: {
                x: { 
                    title: { display: true, text: '红球命中数' }
                },
                y: { 
                    beginAtZero: true,
                    title: { display: true, text: '次数' }
                }
            }
        }
    });
}

function renderBacktestDetails(details) {
    const container = document.getElementById('backtest-details');
    if (!container) return;
    
    if (!details?.length) {
        container.innerHTML = '<p class="text-slate-400 text-sm">暂无详情</p>';
        return;
    }
    
    container.innerHTML = details.map(d => {
        const predBlue = Array.isArray(d.predicted_blue) ? d.predicted_blue : [d.predicted_blue];
        const blueHit = predBlue.includes(d.actual_blue);
        
        return `
        <div class="flex flex-wrap items-center gap-2 py-2 px-3 rounded 
                    ${d.red_match >= 4 ? 'bg-green-50' : d.red_match >= 3 ? 'bg-yellow-50' : 'bg-slate-50'}">
            <span class="text-slate-500 text-xs w-16">${d.period}</span>
            
            <!-- 红球 -->
            <div class="flex items-center gap-0.5">
                ${d.predicted_red.map(n => {
                    const hit = d.actual_red.includes(n);
                    return `<span class="w-5 h-5 rounded-full text-xs flex items-center justify-center 
                        ${hit ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-400'}">${n}</span>`;
                }).join('')}
            </div>
            
            <!-- 蓝球 -->
            <span class="text-slate-300 mx-1">|</span>
            <div class="flex items-center gap-0.5">
                ${predBlue.map(n => {
                    const hit = n === d.actual_blue;
                    return `<span class="w-5 h-5 rounded-full text-xs flex items-center justify-center 
                        ${hit ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-400'}">${n}</span>`;
                }).join('')}
            </div>
            
            <!-- 命中统计 -->
            <span class="ml-auto text-xs">
                <span class="${d.red_match >= 3 ? 'text-green-600 font-bold' : 'text-slate-500'}">
                    ${d.red_match}红
                </span>
                ${blueHit ? '<span class="text-blue-500 font-bold">+蓝</span>' : ''}
                ${d.prize ? `<span class="ml-1 text-amber-500">${d.prize}</span>` : ''}
            </span>
        </div>
        `;
    }).join('');
}
// ==================== 工具函数 ====================
function pad(num) {
    return String(num).padStart(2, '0');
}
