import pandas as pd
import requests
import time
import os
from datetime import datetime

# 设置文件名
CSV_FILE_NAME = "nba_rookies_combined.csv"

def fetch_nba_data():
    years = [2024, 2025, 2026]
    new_data_list = []
    
    # 获取当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"--- 开始执行抓取任务: {current_date} ---")

    # 1. 抓取最新数据
    for year in years:
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}_rookies.html"
        print(f"正在抓取 {year} ...")
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # 关键修改：header=1 告诉 pandas 第二行才是真正的表头 (跳过 Totals/Shooting 等分类头)
                dfs = pd.read_html(response.text, header=1)
                
                if dfs:
                    df = dfs[0]
                    
                    # 清洗数据：删除重复的表头行
                    if 'Player' in df.columns:
                        df = df[df['Player'] != 'Player']
                    
                    # 添加元数据列
                    df['Rookie_Year'] = year
                    df['Fetch_Date'] = current_date
                    
                    new_data_list.append(df)
                    print(f"  - {year} 抓取成功，获取 {len(df)} 行")
            
            time.sleep(3) # 礼貌等待
            
        except Exception as e:
            print(f"  - {year} 抓取出错: {e}")

    # 如果没有抓到任何新数据，直接退出
    if not new_data_list:
        print("未获取到新数据，脚本结束。")
        return

    # 合并本次抓取的所有年份数据
    today_df = pd.concat(new_data_list, ignore_index=True)

    # 2. 处理历史数据逻辑
    if os.path.exists(CSV_FILE_NAME):
        print("检测到现有 CSV 文件，正在读取历史数据...")
        try:
            existing_df = pd.read_csv(CSV_FILE_NAME)
            
            # --- 数据清洗：处理旧文件可能的乱码表头 ---
            # 如果发现旧文件的列名里包含 "Unnamed"，说明是旧格式的脏数据
            # 这种情况下，建议丢弃旧数据或只保留新数据，防止格式冲突
            # 这里我们做一个简单的判断：如果列名正常，就保留
            if "Player" in existing_df.columns:
                # 关键步骤：删除“今天”已有的数据（防止重复运行脚本导致数据重复）
                # 我们只保留 Fetch_Date 不等于今天的行
                if 'Fetch_Date' in existing_df.columns:
                    existing_df = existing_df[existing_df['Fetch_Date'] != current_date]
                
                # 合并：旧历史数据 + 今天新抓的数据
                final_df = pd.concat([existing_df, today_df], ignore_index=True)
                print(f"合并完成。历史数据: {len(existing_df)} 行, 新增数据: {len(today_df)} 行")
            else:
                print("旧文件格式不兼容（可能是旧的乱码表头），将覆盖为新格式。")
                final_df = today_df
        except Exception as e:
            print(f"读取旧文件失败 ({e})，将创建新文件。")
            final_df = today_df
    else:
        print("未检测到 CSV 文件，将创建新文件。")
        final_df = today_df

    # 3. 保存文件
    # 再次清洗：确保没有空行
    final_df.dropna(how='all', inplace=True)
    
    final_df.to_csv(CSV_FILE_NAME, index=False, encoding='utf-8-sig')
    print(f"文件已保存: {CSV_FILE_NAME} (总行数: {len(final_df)})")

if __name__ == "__main__":
    fetch_nba_data()
