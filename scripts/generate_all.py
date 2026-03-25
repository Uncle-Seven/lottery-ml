# scripts/generate_all.py
"""
生成所有数据文件
"""

import json
from pathlib import Path
from datetime import datetime
from lib.features import FeatureEngineer
from lib.models import LotteryPredictor, Backtester


def main():
    print("🚀 开始生成分析和预测数据...")
    print("=" * 60)
    
    data_dir = Path('docs/data')
    
    # 1. 加载历史数据
    history_file = data_dir / 'history.json'
    if not history_file.exists():
        print("❌ 历史数据文件不存在!")
        return
    
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    print(f"📊 加载 {len(history)} 条历史记录")
    
    if len(history) < 30:
        print("❌ 数据量不足 (需要至少30期)!")
        return
    
    # 2. 生成分析数据
    print("\n📈 生成分析数据...")
    fe = FeatureEngineer(history)
    analysis = fe.build_full_analysis()
    
    with open(data_dir / 'analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print("   ✅ analysis.json")
    
    # 3. 生成预测数据
    print("\n🎯 生成预测数据...")
    predictor = LotteryPredictor(history)
    
    # 单式预测
    single_predictions = predictor.generate_single_predictions(count=5)
    
    # 普通复式预测
    duplex_predictions = predictor.generate_duplex_predictions(count=3)
    
    # 福运优化预测
    fortune_predictions = predictor.generate_fortune_predictions(count=3)
    
    pred_output = {
        'generated_at': datetime.now().isoformat(),
        'based_on_period': history[-1]['period'],
        'based_on_date': history[-1]['date'],
        'total_history': len(history),
        'single': {
            'description': '单式投注 (6红1蓝)',
            'red_count': 6,
            'blue_count': 1,
            'predictions': single_predictions
        },
        'duplex': {
            'description': '复式投注 (7红3蓝)',
            'red_count': 7,
            'blue_count': 3,
            'predictions': duplex_predictions
        },
        'fortune': {
            'description': '福运优化 (7红3蓝)',
            'red_count': 7,
            'blue_count': 3,
            'note': '针对福运奖优化，奖池≥15亿时收益最大化',
            'predictions': fortune_predictions
        },
        'predictions': single_predictions
    }
    
    with open(data_dir / 'predictions.json', 'w', encoding='utf-8') as f:
        json.dump(pred_output, f, ensure_ascii=False, indent=2)
    print("   ✅ predictions.json")
    
    # 4. 运行回测
    print("\n📊 运行回测验证...")
    backtester = Backtester(history)
    backtest_results = backtester.run(test_periods=min(100, len(history) - 50))
    
    with open(data_dir / 'backtest.json', 'w', encoding='utf-8') as f:
        json.dump(backtest_results, f, ensure_ascii=False, indent=2)
    print("   ✅ backtest.json")
    
    # 5. 打印摘要
    print("\n" + "=" * 60)
    print("📋 生成摘要")
    print("=" * 60)
    print(f"最新期号: {history[-1]['period']}")
    print(f"开奖日期: {history[-1]['date']}")
    print(f"红球: {history[-1]['red']} 蓝球: {history[-1]['blue']}")
    
    print(f"\n📦 生成方案:")
    print(f"   单式 (6+1): {len(single_predictions)} 组")
    print(f"   复式 (7+3): {len(duplex_predictions)} 组")
    print(f"   福运优化:   {len(fortune_predictions)} 组")
    
    # 打印福运优化方案详情
    if fortune_predictions:
        print(f"\n🎰 福运优化方案示例:")
        fp = fortune_predictions[0]
        meta = fp.get('meta', {})
        print(f"   红球: {fp['red']}")
        print(f"   蓝球: {fp['blue']}")
        print(f"   评分: {meta.get('combination_score', '-')}")
        print(f"   注数: {meta.get('expand_notes', '-')}")
        if 'fortune_prize' in meta:
            print(f"   福运收益: {meta['fortune_prize'].get('x3_y0_scenario', '-')}")
    
    # 单式回测
    print("\n📊 单式回测排名:")
    print("-" * 40)
    single = backtest_results.get('single', {})
    for i, (name, score) in enumerate(single.get('ranking', [])[:5], 1):
        vs_random = score - single.get('random_baseline', 1.09)
        print(f"   {i}. {name}: {score:.3f} (vs随机 {vs_random:+.3f})")
    
    # 复式回测
    print("\n📊 复式回测排名:")
    print("-" * 40)
    duplex = backtest_results.get('duplex', {})
    for i, (name, score) in enumerate(duplex.get('ranking', [])[:5], 1):
        vs_random = score - duplex.get('random_baseline', 1.27)
        marker = "🏆" if name == '福运优化' else "  "
        print(f" {marker}{i}. {name}: {score:.3f} (vs随机 {vs_random:+.3f})")
    
    print("\n" + "=" * 60)
    print("✅ 所有数据生成完成!")


if __name__ == "__main__":
    main()
