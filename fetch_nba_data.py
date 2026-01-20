import pandas as pd
import os

def fetch_data():
    # 定义需要抓取的年份
    years = [2024, 2025, 2026]
    
    for year in years:
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}_rookies.html"
        file_name = f"nba_rookies_{year}.csv"
        
        print(f"正在抓取 {year} 赛季数据...")
        try:
            # 抓取页面中的第一个表格
            # header=1 是因为该网站表格通常有两层表头，这样可以直接取到统计数据
            tables = pd.read_html(url)
            if tables:
                df = tables[0]
                # 清洗数据：移除重复的表头行（比赛中途出现的表头）
                df = df[df['Rk'] != 'Rk']
                # 保存为独立 CSV
                df.to_csv(file_name, index=False, encoding='utf-8-sig')
                print(f"成功保存: {file_name}")
        except Exception as e:
            print(f"抓取 {year} 失败，错误原因: {e}")

if __name__ == "__main__":
    fetch_data()
