"""
特征工程
"""

import numpy as np
from collections import Counter
from typing import List, Dict, Tuple
from datetime import datetime

class FeatureEngineer:
    """特征工程"""
    
    def __init__(self, history: List[Dict]):
        self.history = history
    
    def get_frequency(self, window: int = 50) -> Dict:
        """频率统计"""
        recent = self.history[-window:] if len(self.history) >= window else self.history
        
        all_reds = [n for r in recent for n in r['red']]
        all_blues = [r['blue'] for r in recent]
        
        red_freq = {i: 0 for i in range(1, 34)}
        blue_freq = {i: 0 for i in range(1, 17)}
        
        red_freq.update(Counter(all_reds))
        blue_freq.update(Counter(all_blues))
        
        return {
            'red': red_freq,
            'blue': blue_freq,
            'window': window
        }
    
    def get_missing(self, max_look: int = 100) -> Dict:
        """遗漏值分析"""
        recent = self.history[-max_look:] if len(self.history) >= max_look else self.history
        
        red_missing = {}
        blue_missing = {}
        
        for num in range(1, 34):
            missing = len(recent)
            for i, record in enumerate(reversed(recent)):
                if num in record['red']:
                    missing = i
                    break
            red_missing[num] = missing
        
        for num in range(1, 17):
            missing = len(recent)
            for i, record in enumerate(reversed(recent)):
                if num == record['blue']:
                    missing = i
                    break
            blue_missing[num] = missing
        
        return {'red': red_missing, 'blue': blue_missing}
    
    def get_statistics(self, window: int = 50) -> Dict:
        """统计特征"""
        recent = self.history[-window:] if len(self.history) >= window else self.history
        
        if not recent:
            return {}
        
        sums = [sum(r['red']) for r in recent]
        spans = [max(r['red']) - min(r['red']) for r in recent]
        odds = [sum(1 for n in r['red'] if n % 2 == 1) for r in recent]
        bigs = [sum(1 for n in r['red'] if n > 16) for r in recent]
        
        # 三区分布
        zones = []
        for r in recent:
            z1 = sum(1 for n in r['red'] if 1 <= n <= 11)
            z2 = sum(1 for n in r['red'] if 12 <= n <= 22)
            z3 = sum(1 for n in r['red'] if 23 <= n <= 33)
            zones.append([z1, z2, z3])
        
        return {
            'sum': {
                'mean': round(np.mean(sums), 2),
                'std': round(np.std(sums), 2),
                'min': int(min(sums)),
                'max': int(max(sums))
            },
            'span': {
                'mean': round(np.mean(spans), 2),
                'std': round(np.std(spans), 2)
            },
            'odd_ratio': round(np.mean(odds) / 6, 4),
            'big_ratio': round(np.mean(bigs) / 6, 4),
            'zone_avg': [round(x, 2) for x in np.mean(zones, axis=0).tolist()],
            'window': window
        }
    
    def get_trends(self, short: int = 10, long: int = 50) -> Dict:
        """趋势分析 - 近期vs长期"""
        short_freq = self.get_frequency(short)
        long_freq = self.get_frequency(long)
        
        red_trends = {}
        for num in range(1, 34):
            short_rate = short_freq['red'][num] / max(short, 1)
            long_rate = long_freq['red'][num] / max(long, 1)
            red_trends[num] = round(short_rate - long_rate, 4)
        
        blue_trends = {}
        for num in range(1, 17):
            short_rate = short_freq['blue'][num] / max(short, 1)
            long_rate = long_freq['blue'][num] / max(long, 1)
            blue_trends[num] = round(short_rate - long_rate, 4)
        
        # 排序找出上升/下降趋势号码
        rising = sorted(red_trends.items(), key=lambda x: x[1], reverse=True)[:5]
        falling = sorted(red_trends.items(), key=lambda x: x[1])[:5]
        
        return {
            'red': red_trends,
            'blue': blue_trends,
            'rising': [{'num': k, 'trend': v} for k, v in rising],
            'falling': [{'num': k, 'trend': v} for k, v in falling]
        }
    
    def get_consecutive_analysis(self, window: int = 50) -> Dict:
        """连号分析"""
        recent = self.history[-window:] if len(self.history) >= window else self.history
        
        consecutive_count = 0
        for r in recent:
            red = sorted(r['red'])
            for i in range(5):
                if red[i+1] - red[i] == 1:
                    consecutive_count += 1
                    break
        
        return {
            'ratio': round(consecutive_count / max(len(recent), 1), 4),
            'count': consecutive_count,
            'total': len(recent)
        }
    
    def get_repeat_analysis(self, window: int = 50) -> Dict:
        """重复号分析 - 与上期相同的号码"""
        recent = self.history[-window:] if len(self.history) >= window else self.history
        
        if len(recent) < 2:
            return {'avg': 0, 'distribution': {}}
        
        repeats = []
        for i in range(1, len(recent)):
            prev = set(recent[i-1]['red'])
            curr = set(recent[i]['red'])
            repeats.append(len(prev & curr))
        
        dist = Counter(repeats)
        
        return {
            'avg': round(np.mean(repeats), 2) if repeats else 0,
            'distribution': dict(dist)
        }
    
    def build_full_analysis(self) -> Dict:
        """构建完整分析数据"""
        last_record = self.history[-1] if self.history else None
        
        return {
            'frequency_50': self.get_frequency(50),
            'frequency_100': self.get_frequency(100),
            'missing': self.get_missing(100),
            'statistics': self.get_statistics(50),
            'trends': self.get_trends(10, 50),
            'consecutive': self.get_consecutive_analysis(50),
            'repeat': self.get_repeat_analysis(50),
            'last_period': last_record['period'] if last_record else None,
            'last_date': last_record['date'] if last_record else None,
            'total_records': len(self.history),
            'updated_at': datetime.now().isoformat()
        }
