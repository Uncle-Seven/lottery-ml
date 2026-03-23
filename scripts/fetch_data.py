"""
获取双色球数据
"""

import requests
import json
from pathlib import Path
from lib.parser import SSQDataParser

# ⚠️ 替换为实际的数据URL
DATA_URL = "https://uncle-seven.github.io/caipiao-calculator/ssq_data.js"

class DataFetcher:
    def __init__(self, data_url: str = DATA_URL):
        self.data_url = data_url
        self.data_dir = Path('docs/data')
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch(self) -> str:
        """获取原始数据"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(self.data_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 处理编码
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
            
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            raise
    
    def load_existing(self) -> list:
        """加载现有数据"""
        filepath = self.data_dir / 'history.json'
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save(self, records: list):
        """保存数据"""
        filepath = self.data_dir / 'history.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存 {len(records)} 条记录")
    
    def update(self) -> list:
        """更新数据"""
        print("📥 获取最新数据...")
        
        # 获取并解析
        raw_data = self.fetch()
        parser = SSQDataParser()
        records = parser.parse_js_data(raw_data)
        
        print(f"📊 解析到 {len(records)} 条记录")
        
        # 转换为字典列表
        data = [r.to_dict() for r in records]
        
        # 与现有数据合并（去重）
        existing = self.load_existing()
        existing_periods = {r['period'] for r in existing}
        
        new_count = 0
        for record in data:
            if record['period'] not in existing_periods:
                existing.append(record)
                new_count += 1
        
        # 排序
        existing.sort(key=lambda x: x['period'])
        
        # 保存
        self.save(existing)
        print(f"📈 新增 {new_count} 条，共 {len(existing)} 条")
        
        return existing


def main():
    print("🚀 开始更新双色球数据...")
    fetcher = DataFetcher()
    fetcher.update()
    print("✅ 完成!")


if __name__ == "__main__":
    main()
