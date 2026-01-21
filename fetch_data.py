import pandas as pd
import requests

def fetch_nba_data():
    years = [2024, 2025, 2026]
    all_data = []

    for year in years:
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}_rookies.html"
        print(f"正在抓取 {year} 数据...")
        try:
            # 抓取页面中的第一个表格
            df = pd.read_html(url)[0]
            df['Season_Year'] = year # 添加年份标识
            all_data.append(df)
        except Exception as e:
            print(f"{year} 数据抓取失败: {e}")

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        # 保存为 CSV
        final_df.to_csv("nba_rookies_combined.csv", index=False, encoding='utf-8-sig')
        print("CSV 文件已生成")

if __name__ == "__main__":
    fetch_nba_data()
