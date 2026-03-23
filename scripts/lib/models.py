"""
预测模型
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
            
            # 热号适度加权
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
            
            # 遗漏过长适当加权（回补效应）
            if missing >= 20:
                weights[i] *= 1 + (missing - 20) * 0.015
            elif missing >= 15:
                weights[i] *= 1.1
        
        # 3. 趋势权重（短期vs长期）
        if len(self.history) >= 50:
            short_freq = Counter([n for r in self.history[-10:] for n in r['red']])
            long_freq = Counter([n for r in self.history[-50:] for n in r['red']])
            
            for i in range(33):
                num = i + 1
                short_rate = short_freq.get(num, 0) / 10
                long_rate = long_freq.get(num, 0) / 50
                trend = short_rate - long_rate
                
                # 上升趋势加权
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
                # 遗漏号加权
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
    
    def predict_weighted(self) -> Tuple[List[int], int, Dict]:
        """加权随机预测"""
        red_weights = self._calculate_red_weights()
        blue_weights = self._calculate_blue_weights()
        
        # 选择红球（不重复采样）
        red_balls = []
        available = list(range(1, 34))
        current_weights = red_weights.copy()
        
        for _ in range(6):
            probs = current_weights / current_weights.sum()
            idx = self.rng.choice(len(available), p=probs)
            red_balls.append(available[idx])
            available.pop(idx)
            current_weights = np.delete(current_weights, idx)
        
        # 选择蓝球
        blue_ball = self.rng.choice(range(1, 17), p=blue_weights)
        
        # 计算置信度（基于平均权重）
        selected_indices = [n - 1 for n in red_balls]
        avg_red_weight = np.mean(red_weights[selected_indices])
        confidence = min(avg_red_weight * 33 / 6, 1.0)  # 归一化
        
        return sorted(red_balls), int(blue_ball), {
            'red_confidence': round(confidence, 4),
            'blue_confidence': round(float(blue_weights[blue_ball - 1]) * 16, 4)
        }
    
    def predict_zone_balanced(self) -> Tuple[List[int], int, Dict]:
        """三区均衡预测 (2-2-2 分布)"""
        red_weights = self._calculate_red_weights()
        
        zones = [
            (list(range(1, 12)), red_weights[:11]),     # 1-11
            (list(range(12, 23)), red_weights[11:22]),  # 12-22
            (list(range(23, 34)), red_weights[22:])     # 23-33
        ]
        
        red_balls = []
        for zone_nums, zone_weights in zones:
            probs = zone_weights / zone_weights.sum()
            selected = self.rng.choice(zone_nums, size=2, replace=False, p=probs)
            red_balls.extend(selected)
        
        blue_weights = self._calculate_blue_weights()
        blue_ball = self.rng.choice(range(1, 17), p=blue_weights)
        
        return sorted([int(x) for x in red_balls]), int(blue_ball), {
            'zone_distribution': '2:2:2'
        }
    
    def predict_cold_hot_mix(self) -> Tuple[List[int], int, Dict]:
        """冷热混合预测 (3热 + 2温 + 1冷)"""
        recent = self.history[-50:] if len(self.history) >= 50 else self.history
        all_reds = [n for r in recent for n in r['red']]
        freq = Counter(all_reds)
        
        # 按频率排序
        sorted_nums = sorted(range(1, 34), key=lambda x: freq.get(x, 0), reverse=True)
        
        hot = sorted_nums[:11]      # 热号
        warm = sorted_nums[11:22]   # 温号
        cold = sorted_nums[22:]     # 冷号
        
        red_balls = []
        red_balls.extend(self.rng.choice(hot, 3, replace=False))
        red_balls.extend(self.rng.choice(warm, 2, replace=False))
        red_balls.extend(self.rng.choice(cold, 1, replace=False))
        
        blue_weights = self._calculate_blue_weights()
        blue_ball = self.rng.choice(range(1, 17), p=blue_weights)
        
        return sorted([int(x) for x in red_balls]), int(blue_ball), {
            'mix_ratio': '3热:2温:1冷'
        }
    
    def predict_missing_focused(self) -> Tuple[List[int], int, Dict]:
        """遗漏优先预测 - 关注长期未出号码"""
        # 计算遗漏值
        recent = self.history[-100:] if len(self.history) >= 100 else self.history
        
        missing = {}
        for num in range(1, 34):
            for i, record in enumerate(reversed(recent)):
                if num in record['red']:
                    missing[num] = i
                    break
            else:
                missing[num] = len(recent)
        
        # 按遗漏值排序
        sorted_by_missing = sorted(missing.items(), key=lambda x: x[1], reverse=True)
        
        # 选择前15个遗漏较大的号码作为候选池
        candidates = [x[0] for x in sorted_by_missing[:15]]
        red_balls = list(self.rng.choice(candidates, 6, replace=False))
        
        blue_weights = self._calculate_blue_weights()
        blue_ball = self.rng.choice(range(1, 17), p=blue_weights)
        
        selected_missing = [missing[n] for n in red_balls]
        
        return sorted([int(x) for x in red_balls]), int(blue_ball), {
            'avg_missing': round(np.mean(selected_missing), 1),
            'max_missing': max(selected_missing)
        }
    
    def predict_sum_range(self, target_sum_range: Tuple[int, int] = None) -> Tuple[List[int], int, Dict]:
        """和值范围预测 - 确保和值在合理范围内"""
        if target_sum_range is None:
            # 基于历史计算合理范围
            recent = self.history[-50:] if len(self.history) >= 50 else self.history
            sums = [sum(r['red']) for r in recent]
            mean_sum = np.mean(sums)
            std_sum = np.std(sums)
            target_sum_range = (int(mean_sum - std_sum), int(mean_sum + std_sum))
        
        red_weights = self._calculate_red_weights()
        
        max_attempts = 100
        for _ in range(max_attempts):
            red_balls = []
            available = list(range(1, 34))
            current_weights = red_weights.copy()
            
            for _ in range(6):
                probs = current_weights / current_weights.sum()
                idx = self.rng.choice(len(available), p=probs)
                red_balls.append(available[idx])
                available.pop(idx)
                current_weights = np.delete(current_weights, idx)
            
            if target_sum_range[0] <= sum(red_balls) <= target_sum_range[1]:
                break
        
        blue_weights = self._calculate_blue_weights()
        blue_ball = self.rng.choice(range(1, 17), p=blue_weights)
        
        return sorted(red_balls), int(blue_ball), {
            'sum': sum(red_balls),
            'target_range': list(target_sum_range)
        }
    
    def generate_predictions(self, count: int = 5) -> List[Dict]:
        """生成多组预测"""
        strategies = [
            ('智能加权', self.predict_weighted),
            ('三区均衡', self.predict_zone_balanced),
            ('冷热混合', self.predict_cold_hot_mix),
            ('遗漏优先', self.predict_missing_focused),
            ('和值控制', self.predict_sum_range),
        ]
        
        predictions = []
        used_combinations = set()  # 避免重复
        
        for i in range(count):
            strategy_name, strategy_func = strategies[i % len(strategies)]
            
            max_tries = 10
            for _ in range(max_tries):
                red, blue, meta = strategy_func()
                combo_key = tuple(red) + (blue,)
                
                if combo_key not in used_combinations:
                    used_combinations.add(combo_key)
                    break
            
            prediction = {
                'id': i + 1,
                'strategy': strategy_name,
                'red': red,
                'blue': blue,
                'sum': sum(red),
                'span': max(red) - min(red),
                'odd_count': sum(1 for n in red if n % 2 == 1),
                'big_count': sum(1 for n in red if n > 16),
                'zone_dist': f"{sum(1 for n in red if n<=11)}:{sum(1 for n in red if 12<=n<=22)}:{sum(1 for n in red if n>=23)}",
                'meta': meta
            }
            
            predictions.append(prediction)
        
        return predictions


class Backtester:
    """回测器"""
    
    def __init__(self, history: List[Dict]):
        self.history = history
    
    def run(self, test_periods: int = 50, strategies: List[str] = None) -> Dict:
        """运行回测"""
        if len(self.history) < test_periods + 50:
            test_periods = max(10, len(self.history) - 50)
        
        results = {
            'red_matches': [],
            'blue_matches': [],
            'distribution': {i: 0 for i in range(7)},
            'details': []
        }
        
        for i in range(len(self.history) - test_periods, len(self.history)):
            # 使用历史数据训练
            train_data = self.history[:i]
            actual = self.history[i]
            
            predictor = LotteryPredictor(train_data)
            red_pred, blue_pred, _ = predictor.predict_weighted()
            
            # 计算命中
            actual_red = set(actual['red'])
            red_match = len(set(red_pred) & actual_red)
            blue_match = 1 if blue_pred == actual['blue'] else 0
            
            results['red_matches'].append(red_match)
            results['blue_matches'].append(blue_match)
            results['distribution'][red_match] += 1
            
            results['details'].append({
                'period': actual['period'],
                'predicted_red': red_pred,
                'predicted_blue': blue_pred,
                'actual_red': actual['red'],
                'actual_blue': actual['blue'],
                'red_match': red_match,
                'blue_match': blue_match
            })
        
        # 随机对比
        random_matches = []
        for _ in range(test_periods * 100):
            rand_red = set(np.random.choice(range(1, 34), 6, replace=False))
            actual_idx = np.random.randint(len(self.history))
            actual_red = set(self.history[actual_idx]['red'])
            random_matches.append(len(rand_red & actual_red))
        
        avg_red = np.mean(results['red_matches'])
        avg_random = np.mean(random_matches)
        
        return {
            'avg_red_match': round(avg_red, 4),
            'avg_random_match': round(avg_random, 4),
            'improvement': round(avg_red - avg_random, 4),
            'improvement_percent': round((avg_red - avg_random) / avg_random * 100, 2) if avg_random > 0 else 0,
            'blue_accuracy': round(np.mean(results['blue_matches']), 4),
            'distribution': results['distribution'],
            'test_periods': test_periods,
            'details': results['details'][-10:]  # 只保留最近10期详情
        }
