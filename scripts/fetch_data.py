# scripts/fetch_data.py
"""
获取双色球数据
"""

import requests
import json
import os
from pathlib import Path
from lib.parser import SSQDataParser

# ⚠️ 替换为实际的数据URL
DATA_URL = os.environ.get('DATA_URL', 'https://xxx/ssq_data.js')


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
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
            
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            raise
    
    def load_existing(self) -> list:
        """加载现有数据（修复空文件问题）"""
        filepath = self.data_dir / 'history.json'
        
        # 如果文件不存在，返回空列表
        if not filepath.exists():
            print("📁 history.json 不存在，将创建新文件")
            return []
        
        # 读取文件内容
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 如果文件为空或只有空白字符
            if not content:
                print("📁 history.json 为空，将重新初始化")
                return []
            
            # 尝试解析 JSON
            data = json.loads(content)
            
            # 确保返回的是列表
            if not isinstance(data, list):
                print("⚠️ history.json 格式错误，将重新初始化")
                return []
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ history.json 解析失败: {e}，将重新初始化")
            return []
        except Exception as e:
            print(f"⚠️ 读取 history.json 失败: {e}，将重新初始化")
            return []
    
    def save(self, records: list):
        """保存数据"""
        filepath = self.data_dir / 'history.json'
        
        # 确保目录存在
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 保存 {len(records)} 条记录到 {filepath}")
    
    def update(self) -> list:
        """更新数据"""
        print("📥 获取最新数据...")
        
        # 获取并解析新数据
        raw_data = self.fetch()
        parser = SSQDataParser()
        records = parser.parse_js_data(raw_data)
        
        print(f"📊 解析到 {len(records)} 条记录")
        
        if not records:
            print("❌ 未解析到任何数据!")
            return []
        
        # 转换为字典列表
        new_data = [r.to_dict() for r in records]
        
        # 加载现有数据
        existing = self.load_existing()
        existing_periods = {r['period'] for r in existing}
        
        # 合并新数据
        new_count = 0
        for record in new_data:
            if record['period'] not in existing_periods:
                existing.append(record)
                existing_periods.add(record['period'])
                new_count += 1
        
        # 按期号排序
        existing.sort(key=lambda x: x['period'])
        
        # 保存
        self.save(existing)
        print(f"📈 新增 {new_count} 条，共 {len(existing)} 条")
        
        return existing


def main():
    print("🚀 开始更新双色球数据...")
    
    try:
        fetcher = DataFetcher()
        data = fetcher.update()
        
        if data:
            print(f"✅ 完成! 最新期号: {data[-1]['period']}")
        else:
            print("⚠️ 没有数据被保存")
            
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        raise


if __name__ == "__main__":
    main()
