# scripts/lib/models.py
"""
预测模型 - 支持复式投注（7红3蓝）
"""

import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
from datetime import datetime


class LotteryPredictor:
    """彩票预测器"""
    
    def __init__(self, history: List[Dict]):
        self.history = history
        self.rng = np.random.default_rng()
    
    def _calculate_red_weights(self) -> np.ndarray:
        """计算红球综合权重"""
        weights = np.ones(33)
        
        if len(self.history) < 10:
            return weights / weights.sum()
        
        # 1. 频率权重 (近30期)
        recent = self.history[-30:]
        all_reds = [n for r in recent for n in r['red']]
        freq = Counter(all_reds)
        
        for i in range(33):
            num = i + 1
            count = freq.get(num, 0)
            freq_rate = count / len(recent)
            
            if freq_rate > 0.25:
                weights[i] *= 1.3
            elif freq_rate > 0.15:
                weights[i] *= 1.1
            elif freq_rate < 0.05:
                weights[i] *= 0.9
        
        # 2. 遗漏值权重
        for i in range(33):
            num = i + 1
            missing = 0
            for j, record in enumerate(reversed(self.history[-50:])):
                if num in record['red']:
                    missing = j
                    break
            else:
                missing = min(50, len(self.history))
            
            if missing >= 20:
                weights[i] *= 1 + (missing - 20) * 0.015
            elif missing >= 15:
                weights[i] *= 1.1
        
        # 3. 趋势权重
        if len(self.history) >= 50:
            short_freq = Counter([n for r in self.history[-10:] for n in r['red']])
            long_freq = Counter([n for r in self.history[-50:] for n in r['red']])
            
            for i in range(33):
                num = i + 1
                short_rate = short_freq.get(num, 0) / 10
                long_rate = long_freq.get(num, 0) / 50
                trend = short_rate - long_rate
                
                if trend > 0.05:
                    weights[i] *= 1.15
                elif trend < -0.05:
                    weights[i] *= 0.95
        
        return weights / weights.sum()
    
    def _calculate_blue_weights(self) -> np.ndarray:
        """计算蓝球权重"""
        weights = np.ones(16)
        
        if len(self.history) < 10:
            return weights / weights.sum()
        
        recent = self.history[-30:]
        blues = [r['blue'] for r in recent]
        freq = Counter(blues)
        
        for i in range(16):
            num = i + 1
            count = freq.get(num, 0)
            
            if count >= 4:
                weights[i] *= 1.2
            elif count >= 2:
                weights[i] *= 1.1
            elif count == 0:
                missing = 0
                for j, record in enumerate(reversed(self.history[-50:])):
                    if record['blue'] == num:
                        missing = j
                        break
                else:
                    missing = 50
                
                if missing >= 15:
                    weights[i] *= 1.15
        
        return weights / weights.sum()
    
    def _select_red_balls(self, count: int = 6) -> List[int]:
        """选择红球（通用方法）"""
        red_weights = self._calculate_red_weights()
        
        red_balls = []
        available = list(range(1, 34))
        current_weights = red_weights.copy()
        
        for _ in range(count):
            probs = current_weights / current_weights.sum()
            idx = self.rng.choice(len(available), p=probs)
            red_balls.append(available[idx])
            available.pop(idx)
            current_weights = np.delete(current_weights, idx)
        
        return sorted(red_balls)
    
    def _select_blue_balls(self, count: int = 1) -> List[int]:
        """选择蓝球（支持多个）"""
        blue_weights = self._calculate_blue_weights()
        
        if count == 1:
            return [int(self.rng.choice(range(1, 17), p=blue_weights))]
        
        blue_balls = []
        available = list(range(1, 17))
        current_weights = blue_weights.copy()
        
        for _ in range(count):
            probs = current_weights / current_weights.sum()
            idx = self.rng.choice(len(available), p=probs)
            blue_balls.append(available[idx])
            available.pop(idx)
            current_weights = np.delete(current_weights, idx)
        
        return sorted(blue_balls)
    
    # ==================== 预测策略 ====================
    
    def predict_weighted(self, red_count: int = 6, blue_count: int = 1) -> Dict:
        """加权随机预测"""
        red_balls = self._select_red_balls(red_count)
        blue_balls = self._select_blue_balls(blue_count)
        
        return {
            'red': red_balls,
            'blue': blue_balls[0] if blue_count == 1 else blue_balls,
            'meta': {'method': 'weighted'}
        }
    
    def predict_zone_balanced(self, red_count: int = 6, blue_count: int = 1) -> Dict:
        """三区均衡预测"""
        red_weights = self._calculate_red_weights()
        
        # 三区定义
        zones = [
            (list(range(1, 12)), red_weights[:11]),     # 1-11
            (list(range(12, 23)), red_weights[11:22]),  # 12-22
            (list(range(23, 34)), red_weights[22:])     # 23-33
        ]
        
        # 根据需要的红球数量分配每区个数
        if red_count == 6:
            zone_counts = [2, 2, 2]
        elif red_count == 7:
            # 随机选择一个区多选1个
            zone_counts = [2, 2, 2]
            extra_zone = self.rng.choice(3)
            zone_counts[extra_zone] += 1
        elif red_count == 8:
            zone_counts = [3, 3, 2]
            self.rng.shuffle(zone_counts)
        else:
            # 通用分配
            base = red_count // 3
            remainder = red_count % 3
            zone_counts = [base, base, base]
            for i in range(remainder):
                zone_counts[i] += 1
            self.rng.shuffle(zone_counts)
        
        red_balls = []
        for (zone_nums, zone_weights), count in zip(zones, zone_counts):
            if count > 0 and count <= len(zone_nums):
                probs = zone_weights / zone_weights.sum()
                selected = self.rng.choice(zone_nums, size=count, replace=False, p=probs)
                red_balls.extend(selected)
        
        blue_balls = self._select_blue_balls(blue_count)
        
        return {
            'red': sorted([int(x) for x in red_balls]),
            'blue': blue_balls[0] if blue_count == 1 else blue_balls,
            'meta': {'method': 'zone_balanced', 'zone_dist': zone_counts}
        }
    
    def predict_cold_hot_mix(self, red_count: int = 6, blue_count: int = 1) -> Dict:
        """冷热混合预测"""
        recent = self.history[-50:] if len(self.history) >= 50 else self.history
        all_reds = [n for r in recent for n in r['red']]
        freq = Counter(all_reds)
        
        sorted_nums = sorted(range(1, 34), key=lambda x: freq.get(x, 0), reverse=True)
        
        hot = sorted_nums[:11]
        warm = sorted_nums[11:22]
        cold = sorted_nums[22:]
        
        # 根据总数分配
        if red_count == 6:
            hot_count, warm_count, cold_count = 3, 2, 1
        elif red_count == 7:
            hot_count, warm_count, cold_count = 3, 2, 2
        elif red_count == 8:
            hot_count, warm_count, cold_count = 4, 2, 2
        else:
            hot_count = red_count // 2
            warm_count = red_count // 3
            cold_count = red_count - hot_count - warm_count
        
        red_balls = []
        red_balls.extend(self.rng.choice(hot, min(hot_count, len(hot)), replace=False))
        red_balls.extend(self.rng.choice(warm, min(warm_count, len(warm)), replace=False))
        red_balls.extend(self.rng.choice(cold, min(cold_count, len(cold)), replace=False))
        
        blue_balls = self._select_blue_balls(blue_count)
        
        return {
            'red': sorted([int(x) for x in red_balls]),
            'blue': blue_balls[0] if blue_count == 1 else blue_balls,
            'meta': {'method': 'cold_hot_mix', 'ratio': f'{hot_count}热:{warm_count}温:{cold_count}冷'}
        }
    
    def predict_missing_focused(self, red_count: int = 6, blue_count: int = 1) -> Dict:
        """遗漏优先预测"""
        recent = self.history[-100:] if len(self.history) >= 100 else self.history
        
        missing = {}
        for num in range(1, 34):
            for i, record in enumerate(reversed(recent)):
                if num in record['red']:
                    missing[num] = i
                    break
            else:
                missing[num] = len(recent)
        
        sorted_by_missing = sorted(missing.items(), key=lambda x: x[1], reverse=True)
        
        # 从遗漏值最大的号码中选择
        candidate_count = min(red_count + 5, 20)
        candidates = [x[0] for x in sorted_by_missing[:candidate_count]]
        red_balls = list(self.rng.choice(candidates, red_count, replace=False))
        
        # 蓝球也考虑遗漏
        blue_missing = {}
        for num in range(1, 17):
            for i, record in enumerate(reversed(recent)):
                if record['blue'] == num:
                    blue_missing[num] = i
                    break
            else:
                blue_missing[num] = len(recent)
        
        sorted_blue = sorted(blue_missing.items(), key=lambda x: x[1], reverse=True)
        blue_candidates = [x[0] for x in sorted_blue[:blue_count + 3]]
        blue_balls = list(self.rng.choice(blue_candidates, blue_count, replace=False))
        
        return {
            'red': sorted([int(x) for x in red_balls]),
            'blue': sorted([int(x) for x in blue_balls]) if blue_count > 1 else int(blue_balls[0]),
            'meta': {'method': 'missing_focused'}
        }
    
    def predict_sum_controlled(self, red_count: int = 6, blue_count: int = 1) -> Dict:
        """和值控制预测"""
        recent = self.history[-50:] if len(self.history) >= 50 else self.history
        sums = [sum(r['red']) for r in recent]
        mean_sum = np.mean(sums)
        std_sum = np.std(sums)
        
        # 根据红球数量调整目标和值
        ratio = red_count / 6
        target_min = int((mean_sum - std_sum) * ratio)
        target_max = int((mean_sum + std_sum) * ratio)
        
        red_weights = self._calculate_red_weights()
        
        max_attempts = 100
        best_balls = None
        best_diff = float('inf')
        
        for _ in range(max_attempts):
            balls = []
            available = list(range(1, 34))
            weights = red_weights.copy()
            
            for _ in range(red_count):
                probs = weights / weights.sum()
                idx = self.rng.choice(len(available), p=probs)
                balls.append(available[idx])
                available.pop(idx)
                weights = np.delete(weights, idx)
            
            current_sum = sum(balls)
            
            if target_min <= current_sum <= target_max:
                best_balls = balls
                break
            
            diff = min(abs(current_sum - target_min), abs(current_sum - target_max))
            if diff < best_diff:
                best_diff = diff
                best_balls = balls
        
        blue_balls = self._select_blue_balls(blue_count)
        
        return {
            'red': sorted(best_balls),
            'blue': blue_balls[0] if blue_count == 1 else blue_balls,
            'meta': {
                'method': 'sum_controlled',
                'sum': sum(best_balls),
                'target_range': [target_min, target_max]
            }
        }
    
    def predict_consecutive_aware(self, red_count: int = 6, blue_count: int = 1) -> Dict:
        """连号感知预测 - 适当包含连号"""
        red_weights = self._calculate_red_weights()
        
        max_attempts = 50
        for _ in range(max_attempts):
            red_balls = self._select_red_balls(red_count)
            
            # 检查是否有连号（约60%的期数有连号）
            has_consecutive = any(
                red_balls[i+1] - red_balls[i] == 1 
                for i in range(len(red_balls) - 1)
            )
            
            # 70%概率接受有连号的，30%概率接受无连号的
            if (has_consecutive and self.rng.random() < 0.7) or \
               (not has_consecutive and self.rng.random() < 0.3):
                break
        
        blue_balls = self._select_blue_balls(blue_count)
        
        return {
            'red': red_balls,
            'blue': blue_balls[0] if blue_count == 1 else blue_balls,
            'meta': {'method': 'consecutive_aware', 'has_consecutive': has_consecutive}
        }
    
    # ==================== 生成预测 ====================
    
    def generate_predictions(self, count: int = 5, red_count: int = 6, blue_count: int = 1) -> List[Dict]:
        """
        生成多组预测
        
        参数:
            count: 生成方案数量
            red_count: 每组红球数量 (6-20)
            blue_count: 每组蓝球数量 (1-16)
        """
        # 验证参数
        red_count = max(6, min(20, red_count))
        blue_count = max(1, min(16, blue_count))
        
        strategies = [
            ('智能加权', self.predict_weighted),
            ('三区均衡', self.predict_zone_balanced),
            ('冷热混合', self.predict_cold_hot_mix),
            ('遗漏优先', self.predict_missing_focused),
            ('和值控制', self.predict_sum_controlled),
            ('连号感知', self.predict_consecutive_aware),
        ]
        
        predictions = []
        used_combinations = set()
        
        for i in range(count):
            strategy_name, strategy_func = strategies[i % len(strategies)]
            
            max_tries = 10
            for _ in range(max_tries):
                result = strategy_func(red_count=red_count, blue_count=blue_count)
                
                # 生成唯一标识
                blue_key = tuple(result['blue']) if isinstance(result['blue'], list) else (result['blue'],)
                combo_key = tuple(result['red']) + blue_key
                
                if combo_key not in used_combinations:
                    used_combinations.add(combo_key)
                    break
            
            # 构建预测结果
            red = result['red']
            blue = result['blue']
            
            prediction = {
                'id': i + 1,
                'strategy': strategy_name,
                'red': red,
                'blue': blue,
                'red_count': len(red),
                'blue_count': len(blue) if isinstance(blue, list) else 1,
                'sum': sum(red),
                'span': max(red) - min(red),
                'odd_count': sum(1 for n in red if n % 2 == 1),
                'big_count': sum(1 for n in red if n > 16),
                'zone_dist': f"{sum(1 for n in red if n<=11)}:{sum(1 for n in red if 12<=n<=22)}:{sum(1 for n in red if n>=23)}",
                'meta': result.get('meta', {})
            }
            
            predictions.append(prediction)
        
        return predictions
    
    def generate_duplex_predictions(self, count: int = 3) -> List[Dict]:
        """
        生成复式投注方案（7红3蓝）
        """
        return self.generate_predictions(
            count=count,
            red_count=7,
            blue_count=3
        )
    
    def generate_single_predictions(self, count: int = 5) -> List[Dict]:
        """
        生成单式投注方案（6红1蓝）
        """
        return self.generate_predictions(
            count=count,
            red_count=6,
            blue_count=1
        )


class Backtester:
    """回测器 - 支持多策略对比"""
    
    def __init__(self, history: List[Dict]):
        self.history = history
    
    def run_single_strategy(self, strategy_name: str, strategy_func, 
                            test_periods: int = 50, red_count: int = 6, 
                            blue_count: int = 1) -> Dict:
        """运行单个策略的回测"""
        results = {
            'strategy': strategy_name,
            'red_matches': [],
            'blue_matches': [],
            'distribution': {i: 0 for i in range(red_count + 1)},
            'details': []
        }
        
        for i in range(len(self.history) - test_periods, len(self.history)):
            train_data = self.history[:i]
            actual = self.history[i]
            
            predictor = LotteryPredictor(train_data)
            pred = strategy_func(predictor, red_count, blue_count)
            
            # 计算红球命中
            actual_red = set(actual['red'])
            pred_red = set(pred['red'])
            red_match = len(pred_red & actual_red)
            
            # 计算蓝球命中
            pred_blue = pred['blue'] if isinstance(pred['blue'], int) else pred['blue']
            if isinstance(pred_blue, list):
                blue_match = 1 if actual['blue'] in pred_blue else 0
            else:
                blue_match = 1 if pred_blue == actual['blue'] else 0
            
            results['red_matches'].append(red_match)
            results['blue_matches'].append(blue_match)
            results['distribution'][red_match] = results['distribution'].get(red_match, 0) + 1
            
            results['details'].append({
                'period': actual['period'],
                'predicted_red': pred['red'],
                'predicted_blue': pred_blue,
                'actual_red': actual['red'],
                'actual_blue': actual['blue'],
                'red_match': red_match,
                'blue_match': blue_match
            })
        
        return results
    
    def run_all_strategies(self, test_periods: int = 50, 
                           red_count: int = 6, blue_count: int = 1) -> Dict:
        """运行所有策略的回测对比"""
        
        if len(self.history) < test_periods + 50:
            test_periods = max(10, len(self.history) - 50)
        
        # 定义所有策略
        strategies = {
            '智能加权': lambda p, r, b: p.predict_weighted(r, b),
            '三区均衡': lambda p, r, b: p.predict_zone_balanced(r, b),
            '冷热混合': lambda p, r, b: p.predict_cold_hot_mix(r, b),
            '遗漏优先': lambda p, r, b: p.predict_missing_focused(r, b),
            '和值控制': lambda p, r, b: p.predict_sum_controlled(r, b),
            '连号感知': lambda p, r, b: p.predict_consecutive_aware(r, b),
        }
        
        # 运行各策略
        strategy_results = {}
        for name, func in strategies.items():
            print(f"  回测策略: {name}...")
            result = self.run_single_strategy(
                name, func, test_periods, red_count, blue_count
            )
            
            avg_red = np.mean(result['red_matches'])
            avg_blue = np.mean(result['blue_matches'])
            
            strategy_results[name] = {
                'avg_red_match': round(avg_red, 4),
                'blue_accuracy': round(avg_blue, 4),
                'distribution': result['distribution'],
                'details': result['details'][-5:]  # 保留最近5期详情
            }
        
        # 随机基准对比
        random_matches = []
        rng = np.random.default_rng()
        for _ in range(test_periods * 100):
            rand_red = set(rng.choice(range(1, 34), 6, replace=False))
            actual_idx = rng.integers(len(self.history))
            actual_red = set(self.history[actual_idx]['red'])
            random_matches.append(len(rand_red & actual_red))
        
        random_avg = np.mean(random_matches)
        
        # 找出最佳策略
        best_strategy = max(strategy_results.items(), 
                           key=lambda x: x[1]['avg_red_match'])
        
        # 汇总结果
        return {
            'test_periods': test_periods,
            'red_count': red_count,
            'blue_count': blue_count,
            'random_baseline': {
                'avg_red_match': round(random_avg, 4),
                'description': '完全随机选号'
            },
            'strategies': strategy_results,
            'best_strategy': {
                'name': best_strategy[0],
                'avg_red_match': best_strategy[1]['avg_red_match'],
                'improvement': round(best_strategy[1]['avg_red_match'] - random_avg, 4),
                'improvement_percent': round(
                    (best_strategy[1]['avg_red_match'] - random_avg) / max(random_avg, 0.001) * 100, 2
                )
            },
            'summary': {
                name: {
                    'avg_red': data['avg_red_match'],
                    'vs_random': round(data['avg_red_match'] - random_avg, 4)
                }
                for name, data in strategy_results.items()
            }
        }
    
    def run(self, test_periods: int = 50) -> Dict:
        """
        默认回测方法 - 保持向后兼容
        运行所有策略并返回综合结果
        """
        results = self.run_all_strategies(test_periods, red_count=6, blue_count=1)
        
        # 转换为旧格式以保持兼容
        best = results['best_strategy']
        best_data = results['strategies'][best['name']]
        
        return {
            # 最佳策略数据
            'avg_red_match': best_data['avg_red_match'],
            'avg_random_match': results['random_baseline']['avg_red_match'],
            'improvement': best['improvement'],
            'improvement_percent': best['improvement_percent'],
            'blue_accuracy': best_data['blue_accuracy'],
            'distribution': best_data['distribution'],
            'details': best_data['details'],
            
            # 新增：完整策略对比
            'all_strategies': results['strategies'],
            'best_strategy_name': best['name'],
            'random_baseline': results['random_baseline']['avg_red_match'],
            'test_periods': test_periods,
            
            # 策略排名
            'ranking': sorted(
                [(name, data['avg_red_match']) for name, data in results['strategies'].items()],
                key=lambda x: x[1],
                reverse=True
            )
        }
