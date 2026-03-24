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
    document.getElementById('btn-single').classList.toggle('bg-blue-500', type === 'single');
    document.getElementById('btn-single').classList.toggle('text-white', type === 'single');
    document.getElementById('btn-single').classList.toggle('bg-gray-200', type !== 'single');
    
    document.getElementById('btn-duplex').classList.toggle('bg-blue-500', type === 'duplex');
    document.getElementById('btn-duplex').classList.toggle('text-white', type === 'duplex');
    document.getElementById('btn-duplex').classList.toggle('bg-gray-200', type !== 'duplex');
    
    renderPredictions();
}

// ==================== 预测渲染 ====================
function renderPredictions() {
    const container = document.getElementById('predictions');
    
    // 获取对应类型的预测数据
    let predictions, description;
    
    if (currentPredictionType === 'duplex' && predictionsData.duplex) {
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
    
    // 更新标题信息
    document.getElementById('predBasedOn').textContent = 
        `${description} | 基于第${predictionsData.based_on_period}期`;
    
    container.innerHTML = predictions.map(pred => {
        const blue = pred.blue;
        const isMultiBlue = Array.isArray(blue);
        
        return `
        <div class="border border-slate-100 rounded-xl p-4 hover:border-blue-200 hover:bg-blue-50/30 transition">
            <div class="flex flex-wrap justify-between items-start gap-2 mb-3">
                <div>
                    <span class="font-bold text-slate-700">方案 ${pred.id}</span>
                    <span class="ml-2 text-xs px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full">${pred.strategy}</span>
                    ${isMultiBlue ? `<span class="ml-1 text-xs px-2 py-0.5 bg-blue-100 text-blue-600 rounded-full">复式</span>` : ''}
                </div>
                <div class="text-xs text-slate-400 flex gap-3 flex-wrap">
                    <span>和值: ${pred.sum}</span>
                    <span>跨度: ${pred.span}</span>
                    <span>奇偶: ${pred.odd_count}:${pred.red.length - pred.odd_count}</span>
                    <span>区间: ${pred.zone_dist}</span>
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
                📝 ${pred.red_count}红${isMultiBlue ? blue.length : 1}蓝 
                | 注数: ${calculateBets(pred.red_count, isMultiBlue ? blue.length : 1)}注
                | 金额: ${calculateBets(pred.red_count, isMultiBlue ? blue.length : 1) * 2}元
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

// ==================== 回测 ====================
function renderBacktest() {
    if (!backtestData.avg_red_match) {
        document.getElementById('page-backtest').innerHTML = `
            <div class="card p-8 text-center text-slate-400">暂无回测数据</div>
        `;
        return;
    }
    
    document.getElementById('bt-strategy').textContent = backtestData.avg_red_match.toFixed(2);
    document.getElementById('bt-random').textContent = backtestData.avg_random_match.toFixed(2);
    document.getElementById('bt-improve').textContent = 
        `${backtestData.improvement > 0 ? '+' : ''}${backtestData.improvement_percent.toFixed(1)}%`;
    document.getElementById('bt-blue').textContent = 
        `${(backtestData.blue_accuracy * 100).toFixed(1)}%`;
    
    if (charts.backtest) charts.backtest.destroy();
    
    const dist = backtestData.distribution || {};
    charts.backtest = new Chart(document.getElementById('backtestChart'), {
        type: 'bar',
        data: {
            labels: ['0', '1', '2', '3', '4', '5', '6'],
            datasets: [{
                label: '命中次数',
                data: [0,1,2,3,4,5,6].map(i => dist[i] || 0),
                backgroundColor: [
                    'rgba(239,68,68,0.6)', 'rgba(251,146,60,0.6)', 'rgba(234,179,8,0.6)',
                    'rgba(34,197,94,0.6)', 'rgba(34,197,94,0.8)', 'rgba(16,185,129,0.8)',
                    'rgba(6,182,212,0.8)'
                ],
                borderRadius: 6
            }]
        },
        options: {
            ...chartOptions('次数'),
            scales: {
                x: { title: { display: true, text: '红球命中数' } },
                y: { beginAtZero: true }
            }
        }
    });
    
    const details = backtestData.details || [];
    if (details.length) {
        document.getElementById('backtest-details').innerHTML = details.map(d => `
            <div class="flex flex-wrap items-center gap-2 py-2 px-3 rounded ${d.red_match >= 3 ? 'bg-green-50' : 'bg-slate-50'}">
                <span class="text-slate-500 text-xs w-16">${d.period}</span>
                <span class="text-xs text-slate-400">预测:</span>
                ${d.predicted_red.map(n => {
                    const hit = d.actual_red.includes(n);
                    return `<span class="w-6 h-6 rounded-full text-xs flex items-center justify-center ${hit ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-500'}">${n}</span>`;
                }).join('')}
                <span class="text-xs ml-2">命中: <b class="${d.red_match >= 3 ? 'text-green-600' : 'text-slate-600'}">${d.red_match}</b></span>
            </div>
        `).join('');
    }
}

// ==================== 工具函数 ====================
function pad(num) {
    return String(num).padStart(2, '0');
}
