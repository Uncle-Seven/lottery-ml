"""
双色球数据解析器
数据格式: 期号 日期 红球1-6 蓝球 [其他字段...]
"""

import re
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class LotteryRecord:
    """开奖记录"""
    period: str           # 期号
    date: str            # 日期
    red: List[int]       # 红球 (6个)
    blue: int            # 蓝球
    
    def to_dict(self) -> Dict:
        return {
            'period': self.period,
            'date': self.date,
            'red': self.red,
            'blue': self.blue
        }


class SSQDataParser:
    """双色球数据解析器"""
    
    @staticmethod
    def parse_js_data(js_content: str) -> List[LotteryRecord]:
        """
        解析 JS 格式的数据
        格式: window.SSQ_ONLINE_DATA = `...`;
        每行: 期号 日期 红1 红2 红3 红4 红5 红6 蓝 [其他...]
        """
        records = []
        
        # 提取反引号中的内容
        match = re.search(r'`([^`]+)`', js_content, re.DOTALL)
        if not match:
            # 尝试直接解析内容
            content = js_content
        else:
            content = match.group(1)
        
        # 按行解析
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 9:
                continue
            
            try:
                record = LotteryRecord(
                    period=parts[0],
                    date=parts[1],
                    red=sorted([int(parts[i]) for i in range(2, 8)]),
                    blue=int(parts[8])
                )
                records.append(record)
            except (ValueError, IndexError) as e:
                print(f"解析行失败: {line[:50]}... 错误: {e}")
                continue
        
        # 按期号排序
        records.sort(key=lambda x: x.period)
        
        return records
    
    @staticmethod
    def parse_line(line: str) -> LotteryRecord:
        """解析单行数据"""
        parts = line.strip().split()
        return LotteryRecord(
            period=parts[0],
            date=parts[1],
            red=sorted([int(parts[i]) for i in range(2, 8)]),
            blue=int(parts[8])
        )


# 测试
if __name__ == "__main__":
    test_data = """window.SSQ_ONLINE_DATA = `
2024030 2024-03-19 10 11 14 19 22 24 04 14 10 19 24 11 22 401991268
2024031 2024-03-22 03 10 12 13 18 33 08 13 10 33 12 18 03 430685136`;"""
    
    parser = SSQDataParser()
    records = parser.parse_js_data(test_data)
    
    for r in records:
        print(f"{r.period}: 红球 {r.red} 蓝球 {r.blue}")
