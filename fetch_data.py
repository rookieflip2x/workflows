import pandas as pd
import requests
import time
import os
from datetime import datetime

# 设置文件名
CSV_FILE_NAME = "nba_rookies_combined.csv"

def clean_data(df):
    """
    通用数据清洗函数：
    1. 删除重复表头行
    2. 删除空行
    3. 转换数字列格式
    """
    # 1. 过滤掉 'Player' 列等于 'Player' 的行（这是网站中间插入的表头）
    if 'Player' in df.columns:
        df = df[df['Player'] != 'Player']
    
    # 2. 删除没有球员名字的空行
    df = df.dropna(subset=['Player'])

    # 3. 强制转换数字列（防止因为混入表头导致数字变成字符串）
    # 列出关键的数值列，确保它们是数字格式
    numeric_cols = ['Age', 'G', 'MP', 'FG', 'FGA', '3P', 'FT', 'TRB', 'AST', 'STL', 'BLK', 'PTS']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def fetch_nba_data():
    years = [2024, 2025, 2026]
    new_data_list = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"--- 开始执行抓取任务: {current_date} ---")

    # === 第一步：抓取最新数据 ===
    for year in years:
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}_rookies.html"
        print(f"正在抓取 {year} ...")
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # header=1 跳过最顶部的分类表头
                dfs = pd.read_html(response.text, header=1)
                
                if dfs:
                    df = dfs[0]
                    
                    # 添加元数据
                    df['Rookie_Year'] = year
                    df['Fetch_Date'] = current_date
                    
                    # 立即清洗本次抓取的数据
                    df = clean_data(df)
                    
                    new_data_list.append(df)
                    print(f"  - {year} 抓取成功，有效数据 {len(df)} 行")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"  - {year} 抓取出错: {e}")

    if not new_data_list:
        print("未获取到新数据，脚本结束。")
        return

    # 合并本次新数据
    today_df = pd.concat(new_data_list, ignore_index=True)

    # === 第二步：处理历史数据 ===
    if os.path.exists(CSV_FILE_NAME):
        print("检测到历史文件，正在读取并修复...")
        try:
            existing_df = pd.read_csv(CSV_FILE_NAME)
            
            # --- 关键修复：清洗旧文件 ---
            # 这会把以前混进去的 'Player' 表头行删掉
            existing_df = clean_data(existing_df)
            
            # 删除“今天”已有的数据（防止重复运行）
            if 'Fetch_Date' in existing_df.columns:
                existing_df = existing_df[existing_df['Fetch_Date'] != current_date]
            
            # 合并：清洗后的历史数据 + 今天新数据
            final_df = pd.concat([existing_df, today_df], ignore_index=True)
            print(f"合并完成。历史数据: {len(existing_df)} 行, 新增数据: {len(today_df)} 行")
            
        except Exception as e:
            print(f"读取旧文件失败 ({e})，将创建新文件。")
            final_df = today_df
    else:
        print("创建新文件...")
        final_df = today_df

    # === 第三步：最终保存 ===
    # 保存前再做一次去重（可选，以防万一）
    final_df.drop_duplicates(subset=['Player', 'Rookie_Year', 'Fetch_Date'], inplace=True)
    
    final_df.to_csv(CSV_FILE_NAME, index=False, encoding='utf-8-sig')
    print(f"文件已保存: {CSV_FILE_NAME} (总行数: {len(final_df)})")

if __name__ == "__main__":
    fetch_nba_data()
