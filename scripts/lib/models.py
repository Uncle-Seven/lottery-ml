# scripts/lib/models.py
"""
预测模型 - 支持单式和复式
"""

import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
from datetime import datetime
from math import comb


class LotteryPredictor:
    """彩票预测器"""
    
    def __init__(self, history: List[Dict]):
        self.history = history
        self.rng = np.random.default_rng()
    
    # ==================== 基础方法 ====================
    
    def _calculate_red_weights(self) -> np.ndarray:
        """计算红球综合权重"""
        weights = np.ones(33)
        
        if len(self.history) < 10:
            return weights / weights.sum()
        
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
        """选择红球"""
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
        """选择蓝球"""
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
        
        zones = [
            (list(range(1, 12)), red_weights[:11]),
            (list(range(12, 23)), red_weights[11:22]),
            (list(range(23, 34)), red_weights[22:])
        ]
        
        if red_count == 6:
            zone_counts = [2, 2, 2]
        elif red_count == 7:
            zone_counts = [2, 2, 2]
            extra_zone = self.rng.choice(3)
            zone_counts[extra_zone] += 1
        elif red_count == 8:
            zone_counts = [3, 3, 2]
            self.rng.shuffle(zone_counts)
        else:
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
        
        candidate_count = min(red_count + 5, 20)
        candidates = [x[0] for x in sorted_by_missing[:candidate_count]]
        red_balls = list(self.rng.choice(candidates, red_count, replace=False))
        
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
        """连号感知预测"""
        max_attempts = 50
        for _ in range(max_attempts):
            red_balls = self._select_red_balls(red_count)
            
            has_consecutive = any(
                red_balls[i+1] - red_balls[i] == 1 
                for i in range(len(red_balls) - 1)
            )
            
            if (has_consecutive and self.rng.random() < 0.7) or \
               (not has_consecutive and self.rng.random() < 0.3):
                break
        
        blue_balls = self._select_blue_balls(blue_count)
        
        return {
            'red': red_balls,
            'blue': blue_balls[0] if blue_count == 1 else blue_balls,
            'meta': {'method': 'consecutive_aware', 'has_consecutive': has_consecutive}
        }
    
    # ==================== 福运奖增强型算法 ====================
    
    def predict_fortune_optimized(self, red_count: int = 7, blue_count: int = 3) -> Dict:
        """
        福运奖增强型复式投注策略
        
        核心思路：
        1. 历史数据 → 冷/温/热分池 → 偏选冷号+温号（减少分奖人数）
        2. 多维结构评分器（和值/奇偶/分区/连号/尾数/反大众）
        3. 蓝球三分区各选1个偏冷号 → 覆盖 3/16 = 18.75%
        4. 福运奖(奖池≥15亿)：X=3,Y=0 → 可盈利
        """
        # ============ 第一部分：历史数据分析 ============
        history_length = len(self.history)
        analysis_window = min(100, history_length)
        recent = self.history[-analysis_window:] if analysis_window > 0 else []
        
        # 红球频率 & 遗漏分析
        all_reds = [n for record in recent for n in record['red']]
        red_freq = Counter(all_reds)
        expected_freq = max(analysis_window * 6 / 33, 0.1)
        
        red_info = {}
        cold_pool = []
        warm_pool = []
        hot_pool = []
        
        for i in range(1, 34):
            freq = red_freq.get(i, 0)
            deviation = (freq - expected_freq) / expected_freq
            
            # 遗漏值
            gap = len(recent)
            for idx, record in enumerate(reversed(recent)):
                if i in record['red']:
                    gap = idx
                    break
            
            # 分类
            if analysis_window < 10:
                cat = 'warm'
            elif deviation < -0.25 or (gap > 15 and analysis_window >= 30):
                cat = 'cold'
            elif deviation > 0.25:
                cat = 'hot'
            else:
                cat = 'warm'
            
            red_info[i] = {
                'freq': freq,
                'deviation': round(deviation, 3),
                'gap': gap,
                'category': cat
            }
            {'cold': cold_pool, 'warm': warm_pool, 'hot': hot_pool}[cat].append(i)
        
        # 蓝球频率
        all_blues = []
        for record in recent:
            b = record['blue']
            all_blues.extend(b if isinstance(b, (list, tuple)) else [b])
        blue_freq = Counter(all_blues)
        blue_expected = max(analysis_window / 16, 0.1)
        
        # ============ 第二部分：红球加权选择 ============
        POPULAR = {6, 8, 9, 16, 18, 28}      # 吉利数
        UNPOPULAR = {4, 13, 14}              # 不吉利数
        BLUE_POP = {6, 8, 12}                # 蓝球热门号
        
        def red_weight(n):
            """反大众权重"""
            info = red_info[n]
            w = 1.0
            w *= {'cold': 2.5, 'warm': 2.0, 'hot': 0.8}[info['category']]
            if n in UNPOPULAR:
                w *= 1.5
            if n in POPULAR:
                w *= 0.6
            if n > 28:
                w *= 1.3
            return w
        
        candidates = list(range(1, 34))
        raw_weights = np.array([red_weight(n) for n in candidates])
        weights_norm = raw_weights / raw_weights.sum()
        
        # ============ 第三部分：组合结构评分器 ============
        def score_combination(combo):
            """多维评分（满分100）"""
            c = sorted(combo)
            rc = len(c)
            s = 0
            
            # ① 和值（目标 = 17 × R）
            delta = abs(sum(c) - 17 * rc)
            s += 20 if delta <= 15 else (14 if delta <= 25 else (6 if delta <= 35 else 0))
            
            # ② 奇偶均衡
            odd = sum(1 for n in c if n % 2 == 1)
            diff = abs(2 * odd - rc)
            s += 15 if diff <= 1 else (10 if diff <= 2 else (5 if diff <= 3 else 0))
            
            # ③ 三分区覆盖
            zones = [
                sum(1 for n in c if 1 <= n <= 11),
                sum(1 for n in c if 12 <= n <= 22),
                sum(1 for n in c if 23 <= n <= 33),
            ]
            min_z = min(zones)
            s += 20 if min_z >= 2 else (12 if min_z >= 1 else 3)
            
            # ④ 连号对数
            consec = sum(1 for i in range(rc - 1) if c[i + 1] - c[i] == 1)
            s += {0: 5, 1: 10, 2: 6}.get(consec, 0)
            
            # ⑤ 尾数多样性
            tails = len(set(n % 10 for n in c))
            s += 10 if tails >= rc - 1 else (7 if tails >= rc - 2 else (4 if tails >= rc - 3 else 0))
            
            # ⑥ 冷号比例
            cold_cnt = sum(1 for n in c if red_info[n]['category'] == 'cold')
            ideal = round(rc * 0.3)
            s += 15 if abs(cold_cnt - ideal) <= 1 else (8 if abs(cold_cnt - ideal) <= 2 else 3)
            
            # ⑦ 反大众偏好
            anti = 10
            if sum(1 for n in c if n in POPULAR) > 2:
                anti -= 3
            if sum(1 for n in c if 1 <= n <= 12) > rc * 0.5:
                anti -= 3
            # 等差数列检测
            for i in range(rc):
                for j in range(i + 1, rc):
                    d = c[j] - c[i]
                    if d > 0:
                        cnt, nxt = 2, c[j] + d
                        while nxt in c:
                            cnt += 1
                            nxt += d
                        if cnt >= 4:
                            anti -= 4
                            break
                else:
                    continue
                break
            s += max(0, anti)
            
            return s
        
        # ============ 第四部分：迭代搜索最优组合 ============
        best_combo = None
        best_score = -1
        MAX_ATTEMPTS = 10000
        SCORE_THRESHOLD = 88
        
        search_attempts = 0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            search_attempts = attempt
            try:
                combo = self.rng.choice(
                    candidates, size=red_count, replace=False, p=weights_norm
                )
                combo = [int(n) for n in combo]
            except Exception:
                combo = list(self.rng.choice(33, size=red_count, replace=False) + 1)
            
            s = score_combination(combo)
            if s > best_score:
                best_score = s
                best_combo = sorted(combo)
            
            if best_score >= SCORE_THRESHOLD:
                break
        
        # 兜底
        if best_combo is None:
            best_combo = sorted(int(n) for n in self.rng.choice(
                range(1, 34), size=red_count, replace=False
            ))
            best_score = score_combination(best_combo)
        
        # ============ 第五部分：蓝球选择 ============
        BLUE_ZONES = [
            list(range(1, 6)),    # 01-05
            list(range(6, 11)),   # 06-10
            list(range(11, 17)),  # 11-16
        ]
        
        def blue_weight(n):
            freq = blue_freq.get(n, 0)
            dev = (freq - blue_expected) / blue_expected
            w = 3.0 if dev < -0.2 else (2.0 if dev < 0.2 else 1.0)
            if n in BLUE_POP:
                w *= 0.5
            if n in UNPOPULAR:
                w *= 1.3
            return w
        
        blue_balls = []
        for zone in BLUE_ZONES:
            if len(blue_balls) >= blue_count:
                break
            avail = [n for n in zone if n not in blue_balls]
            if not avail:
                continue
            bw = np.array([blue_weight(n) for n in avail])
            bw /= bw.sum()
            blue_balls.append(int(self.rng.choice(avail, size=1, p=bw)[0]))
        
        while len(blue_balls) < blue_count:
            remaining = [n for n in range(1, 17) if n not in blue_balls]
            if not remaining:
                break
            bw = np.array([blue_weight(n) for n in remaining])
            bw /= bw.sum()
            blue_balls.append(int(self.rng.choice(remaining, size=1, p=bw)[0]))
        
        blue_balls = sorted(blue_balls[:blue_count])
        
        # ============ 第六部分：构建返回结果 ============
        red_result = [int(n) for n in best_combo]
        
        # 结构统计
        odd_cnt = sum(1 for n in red_result if n % 2 == 1)
        even_cnt = len(red_result) - odd_cnt
        z1 = len([n for n in red_result if 1 <= n <= 11])
        z2 = len([n for n in red_result if 12 <= n <= 22])
        z3 = len([n for n in red_result if 23 <= n <= 33])
        consec_pairs = sum(
            1 for i in range(len(red_result) - 1)
            if red_result[i + 1] - red_result[i] == 1
        )
        tail_types = len(set(n % 10 for n in red_result))
        
        cold_in = [n for n in red_result if red_info[n]['category'] == 'cold']
        warm_in = [n for n in red_result if red_info[n]['category'] == 'warm']
        hot_in = [n for n in red_result if red_info[n]['category'] == 'hot']
        
        # 注数 & 成本
        expand = comb(red_count, 6) * (blue_count if blue_count > 1 else 1)
        cost = expand * 2
        
        # 福运奖测算
        fortune_red_combos = comb(max(red_count - 3, 0), 3)
        fortune_x3_y0_tickets = fortune_red_combos * blue_count
        fortune_x3_y0_amount = fortune_x3_y0_tickets * 5
        
        return {
            'red': red_result,
            'blue': blue_balls[0] if blue_count == 1 else blue_balls,
            'meta': {
                'method': 'fortune_optimized',
                'combination_score': f'{best_score}/100',
                'search_attempts': search_attempts,
                'expand_notes': f'{red_count}+{blue_count} 复式 → {expand}注 = {cost}元',
                
                'red_structure': {
                    'sum': sum(red_result),
                    'target_sum': 17 * red_count,
                    'odd_even': f'{odd_cnt}奇:{even_cnt}偶',
                    'zone_distribution': f'{z1}:{z2}:{z3}',
                    'consecutive_pairs': consec_pairs,
                    'tail_digit_types': tail_types,
                    'cold_numbers': cold_in,
                    'warm_numbers': warm_in,
                    'hot_numbers': hot_in,
                },
                
                'pool_info': {
                    'analysis_window': f'最近{analysis_window}期',
                    'cold_pool_size': len(cold_pool),
                    'warm_pool_size': len(warm_pool),
                    'hot_pool_size': len(hot_pool),
                },
                
                'fortune_prize': {
                    'activation': '奖池≥15亿自动激活',
                    'x3_y0_scenario': f'{fortune_x3_y0_tickets}注×5元={fortune_x3_y0_amount}元',
                    'cost': f'{cost}元',
                    'net_profit': f'{fortune_x3_y0_amount - cost:+d}元',
                },
            }
        }
    
    # ==================== 生成预测 ====================
    
    def generate_predictions(self, count: int = 5, red_count: int = 6, blue_count: int = 1) -> List[Dict]:
        """生成多组预测"""
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
                
                blue_key = tuple(result['blue']) if isinstance(result['blue'], list) else (result['blue'],)
                combo_key = tuple(result['red']) + blue_key
                
                if combo_key not in used_combinations:
                    used_combinations.add(combo_key)
                    break
            
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
    
    def generate_single_predictions(self, count: int = 5) -> List[Dict]:
        """生成单式投注方案（6红1蓝）"""
        return self.generate_predictions(count=count, red_count=6, blue_count=1)
    
    def generate_duplex_predictions(self, count: int = 3) -> List[Dict]:
        """生成复式投注方案（7红3蓝）"""
        return self.generate_predictions(count=count, red_count=7, blue_count=3)
    
    def generate_fortune_predictions(self, count: int = 3) -> List[Dict]:
        """生成福运奖优化方案（7红3蓝）"""
        predictions = []
        used_combinations = set()
        
        for i in range(count):
            max_tries = 10
            for _ in range(max_tries):
                result = self.predict_fortune_optimized(red_count=7, blue_count=3)
                
                blue = result['blue']
                blue_key = tuple(blue) if isinstance(blue, list) else (blue,)
                combo_key = tuple(result['red']) + blue_key
                
                if combo_key not in used_combinations:
                    used_combinations.add(combo_key)
                    break
            
            red = result['red']
            
            prediction = {
                'id': i + 1,
                'strategy': '福运优化',
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


class Backtester:
    """回测器"""
    
    def __init__(self, history: List[Dict]):
        self.history = history
    
    def _calculate_match(self, pred_red: List[int], pred_blue,
                         actual_red: List[int], actual_blue: int) -> Dict:
        """计算命中"""
        actual_red_set = set(actual_red)
        pred_red_set = set(pred_red)
        red_match = len(pred_red_set & actual_red_set)
        
        if isinstance(pred_blue, list):
            blue_match = 1 if actual_blue in pred_blue else 0
        else:
            blue_match = 1 if pred_blue == actual_blue else 0
        
        return {'red_match': red_match, 'blue_match': blue_match}
    
    def run_single_strategy(self, strategy_name: str, strategy_func,
                            test_periods: int, red_count: int, blue_count: int) -> Dict:
        """运行单个策略回测"""
        results = {
            'strategy': strategy_name,
            'red_count': red_count,
            'blue_count': blue_count,
            'red_matches': [],
            'blue_matches': [],
            'distribution': {},
            'details': []
        }
        
        for i in range(len(self.history) - test_periods, len(self.history)):
            train_data = self.history[:i]
            actual = self.history[i]
            
            if len(train_data) < 30:
                continue
            
            predictor = LotteryPredictor(train_data)
            pred = strategy_func(predictor, red_count, blue_count)
            
            match_result = self._calculate_match(
                pred['red'], pred['blue'], actual['red'], actual['blue']
            )
            
            red_match = match_result['red_match']
            blue_match = match_result['blue_match']
            
            results['red_matches'].append(red_match)
            results['blue_matches'].append(blue_match)
            
            key = str(red_match)
            results['distribution'][key] = results['distribution'].get(key, 0) + 1
            
            results['details'].append({
                'period': actual['period'],
                'predicted_red': pred['red'],
                'predicted_blue': pred['blue'],
                'actual_red': actual['red'],
                'actual_blue': actual['blue'],
                'red_match': red_match,
                'blue_match': blue_match
            })
        
        return results
    
    def run_comparison(self, test_periods: int = 50) -> Dict:
        """运行单式 vs 复式 vs 福运优化对比回测"""
        if len(self.history) < test_periods + 50:
            test_periods = max(10, len(self.history) - 50)
        
        # 所有策略（含福运优化）
        strategies = {
            '智能加权': lambda p, r, b: p.predict_weighted(r, b),
            '三区均衡': lambda p, r, b: p.predict_zone_balanced(r, b),
            '冷热混合': lambda p, r, b: p.predict_cold_hot_mix(r, b),
            '遗漏优先': lambda p, r, b: p.predict_missing_focused(r, b),
            '和值控制': lambda p, r, b: p.predict_sum_controlled(r, b),
            '连号感知': lambda p, r, b: p.predict_consecutive_aware(r, b),
            '福运优化': lambda p, r, b: p.predict_fortune_optimized(r, b),
        }
        
        # 单式回测 (6红1蓝)
        print("  📊 回测单式 (6红1蓝)...")
        single_results = {}
        for name, func in strategies.items():
            if name == '福运优化':
                continue  # 福运优化不适用于单式
            result = self.run_single_strategy(name, func, test_periods, 6, 1)
            avg_red = np.mean(result['red_matches']) if result['red_matches'] else 0
            avg_blue = np.mean(result['blue_matches']) if result['blue_matches'] else 0
            single_results[name] = {
                'avg_red_match': round(avg_red, 4),
                'blue_accuracy': round(avg_blue, 4),
                'distribution': result['distribution'],
                'details': result['details'][-5:]
            }
        
        # 复式回测 (7红3蓝)
        print("  📊 回测复式 (7红3蓝)...")
        duplex_results = {}
        for name, func in strategies.items():
            result = self.run_single_strategy(name, func, test_periods, 7, 3)
            avg_red = np.mean(result['red_matches']) if result['red_matches'] else 0
            avg_blue = np.mean(result['blue_matches']) if result['blue_matches'] else 0
            duplex_results[name] = {
                'avg_red_match': round(avg_red, 4),
                'blue_accuracy': round(avg_blue, 4),
                'distribution': result['distribution'],
                'details': result['details'][-5:]
            }
        
        # 随机基准
        random_single = self._random_baseline(test_periods, 6, 1)
        random_duplex = self._random_baseline(test_periods, 7, 3)
        
        # 找最佳策略
        best_single = max(single_results.items(), key=lambda x: x[1]['avg_red_match'])
        best_duplex = max(duplex_results.items(), key=lambda x: x[1]['avg_red_match'])
        
        return {
            'test_periods': test_periods,
            
            'single': {
                'description': '单式 (6红1蓝)',
                'red_count': 6,
                'blue_count': 1,
                'random_baseline': random_single,
                'strategies': single_results,
                'best_strategy': {
                    'name': best_single[0],
                    'avg_red_match': best_single[1]['avg_red_match'],
                    'improvement': round(best_single[1]['avg_red_match'] - random_single, 4)
                },
                'ranking': sorted(
                    [(n, d['avg_red_match']) for n, d in single_results.items()],
                    key=lambda x: x[1], reverse=True
                )
            },
            
            'duplex': {
                'description': '复式 (7红3蓝)',
                'red_count': 7,
                'blue_count': 3,
                'random_baseline': random_duplex,
                'strategies': duplex_results,
                'best_strategy': {
                    'name': best_duplex[0],
                    'avg_red_match': best_duplex[1]['avg_red_match'],
                    'improvement': round(best_duplex[1]['avg_red_match'] - random_duplex, 4)
                },
                'ranking': sorted(
                    [(n, d['avg_red_match']) for n, d in duplex_results.items()],
                    key=lambda x: x[1], reverse=True
                )
            },
            
            # 向后兼容
            'avg_red_match': best_single[1]['avg_red_match'],
            'avg_random_match': random_single,
            'improvement': round(best_single[1]['avg_red_match'] - random_single, 4),
            'improvement_percent': round(
                (best_single[1]['avg_red_match'] - random_single) / max(random_single, 0.001) * 100, 2
            ),
            'blue_accuracy': best_single[1]['blue_accuracy'],
            'distribution': best_single[1]['distribution'],
            'details': best_single[1]['details'],
            'best_strategy_name': best_single[0],
            'ranking': [(n, d['avg_red_match']) for n, d in single_results.items()]
        }
    
    def _random_baseline(self, test_periods: int, red_count: int, blue_count: int) -> float:
        """计算随机基准"""
        rng = np.random.default_rng(42)
        matches = []
        
        for _ in range(test_periods * 100):
            rand_red = set(rng.choice(range(1, 34), red_count, replace=False))
            actual_idx = rng.integers(len(self.history))
            actual_red = set(self.history[actual_idx]['red'])
            matches.append(len(rand_red & actual_red))
        
        return round(np.mean(matches), 4)
    
    def run(self, test_periods: int = 50) -> Dict:
        """默认回测"""
        return self.run_comparison(test_periods)
