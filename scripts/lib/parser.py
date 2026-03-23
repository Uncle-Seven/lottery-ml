# scripts/lib/parser.py
"""
双色球数据解析器
"""

import re
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class LotteryRecord:
    """开奖记录"""
    period: str
    date: str
    red: List[int]
    blue: int
    
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
        
        if not js_content or not js_content.strip():
            print("⚠️ 输入内容为空")
            return records
        
        # 尝试提取反引号中的内容
        match = re.search(r'`([^`]+)`', js_content, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            # 尝试提取引号中的内容
            match = re.search(r'["\']([^"\']+)["\']', js_content, re.DOTALL)
            if match:
                content = match.group(1)
            else:
                # 直接使用原内容
                content = js_content
        
        # 按行解析
        lines = content.strip().split('\n')
        parse_errors = 0
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # 跳过注释或无效行
            if line.startswith('//') or line.startswith('#'):
                continue
            
            parts = line.split()
            
            # 至少需要 9 个字段: 期号 日期 红1-6 蓝
            if len(parts) < 9:
                if parse_errors < 5:  # 只打印前5个错误
                    print(f"⚠️ 第{line_num}行字段不足: {line[:50]}...")
                parse_errors += 1
                continue
            
            try:
                # 解析红球 (第3-8个字段, 索引2-7)
                red_balls = []
                for i in range(2, 8):
                    num = int(parts[i])
                    if not 1 <= num <= 33:
                        raise ValueError(f"红球 {num} 超出范围 1-33")
                    red_balls.append(num)
                
                # 解析蓝球 (第9个字段, 索引8)
                blue_ball = int(parts[8])
                if not 1 <= blue_ball <= 16:
                    raise ValueError(f"蓝球 {blue_ball} 超出范围 1-16")
                
                record = LotteryRecord(
                    period=parts[0],
                    date=parts[1],
                    red=sorted(red_balls),
                    blue=blue_ball
                )
                records.append(record)
                
            except (ValueError, IndexError) as e:
                if parse_errors < 5:
                    print(f"⚠️ 第{line_num}行解析失败: {e}")
                parse_errors += 1
                continue
        
        if parse_errors > 0:
            print(f"⚠️ 共有 {parse_errors} 行解析失败")
        
        # 按期号排序
        records.sort(key=lambda x: x.period)
        
        print(f"✅ 成功解析 {len(records)} 条记录")
        
        return records


# 测试
if __name__ == "__main__":
    test_data = """window.SSQ_ONLINE_DATA = `
2024030 2024-03-19 10 11 14 19 22 24 04 14 10 19 24 11 22 401991268
2024031 2024-03-22 03 10 12 13 18 33 08 13 10 33 12 18 03 430685136
`;"""
    
    parser = SSQDataParser()
    records = parser.parse_js_data(test_data)
    
    for r in records:
        print(f"{r.period}: 红球 {r.red} 蓝球 {r.blue}")
