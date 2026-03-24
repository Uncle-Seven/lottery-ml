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
    
    data_dir = Path('docs/data')
    
    # 1. 加载历史数据
    history_file = data_dir / 'history.json'
    if not history_file.exists():
        print("❌ 历史数据文件不存在!")
        return
    
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    print(f"📊 加载 {len(history)} 条历史记录")
    
    if len(history) < 10:
        print("❌ 数据量不足!")
        return
    
    # 2. 生成分析数据
    print("📈 生成分析数据...")
    fe = FeatureEngineer(history)
    analysis = fe.build_full_analysis()
    
    with open(data_dir / 'analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print("✅ analysis.json 已生成")
    
    # 3. 生成预测数据
    print("🎯 生成预测数据...")
    predictor = LotteryPredictor(history)
    
    single_predictions = predictor.generate_single_predictions(count=5)
    duplex_predictions = predictor.generate_duplex_predictions(count=3)
    
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
        'predictions': single_predictions
    }
    
    with open(data_dir / 'predictions.json', 'w', encoding='utf-8') as f:
        json.dump(pred_output, f, ensure_ascii=False, indent=2)
    print("✅ predictions.json 已生成")
    
    # 4. 运行多策略回测
    print("📊 运行多策略回测验证...")
    backtester = Backtester(history)
    backtest_results = backtester.run(test_periods=min(100, len(history) - 50))
    
    with open(data_dir / 'backtest.json', 'w', encoding='utf-8') as f:
        json.dump(backtest_results, f, ensure_ascii=False, indent=2)
    print("✅ backtest.json 已生成")
    
    # 5. 打印摘要
    print("\n" + "=" * 60)
    print("📋 生成摘要")
    print("=" * 60)
    print(f"最新期号: {history[-1]['period']}")
    print(f"数据日期: {history[-1]['date']}")
    print(f"单式方案: {len(single_predictions)} 组")
    print(f"复式方案: {len(duplex_predictions)} 组")
    
    print("\n📊 策略回测排名:")
    print("-" * 40)
    for i, (name, score) in enumerate(backtest_results['ranking'], 1):
        vs_random = score - backtest_results['random_baseline']
        marker = "👑" if i == 1 else "  "
        print(f"{marker} {i}. {name}: {score:.3f} (vs随机 {vs_random:+.3f})")
    
    print("-" * 40)
    print(f"随机基准: {backtest_results['random_baseline']:.3f}")
    print(f"最佳策略: {backtest_results['best_strategy_name']}")
    print("=" * 60)
    
    print("\n✅ 所有数据生成完成!")


if __name__ == "__main__":
    main()
