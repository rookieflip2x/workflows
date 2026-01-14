import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')

# --- 核心修复：更新为带转义字符的完整链接 ---
CSV_LINKS = {
    "2023-24": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2023-24_%20rookies%20.csv",
    "2024-25": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2024-25_rookies%20.csv",
    "2025-26": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2025-26_rookies%20.csv"
}

def fetch_and_clean_data(season):
    """基于提供的 Raw 数据结构优化清洗逻辑"""
    try:
        url = CSV_LINKS.get(season)
        # 读取数据，跳过坏行
        df_raw = pd.read_csv(url, on_bad_lines='skip')
        
        # 1. 定位表头：寻找包含 'Player' 或 'PTS' 的行
        header_idx = None
        for i, row in df_raw.head(10).iterrows():
            if 'Player' in row.values:
                header_idx = i
                break
        
        if header_idx is not None:
            df = pd.read_csv(url, header=header_idx + 1)
        else:
            df = df_raw

        # 2. 增强型列名映射：解决 Key 丢失问题的核心
        # 系统会自动扫描所有列，只要列名包含关键词（不分大小写）就进行归一化
        mapping = {}
        target_map = {
            'Player': ['Player', 'Name'],
            'G': ['G', 'GP', 'Totals'],
            'MP': ['MP', 'Min', 'Per Game'],
            'PTS': ['PTS', 'Points'],
            'TRB': ['TRB', 'Rebounds', 'Total Rebounds'],
            'AST': ['AST', 'Assists'],
            'STL': ['STL', 'Steals'],
            'BLK': ['BLK', 'Blocks'],
            'FG%': ['FG%', 'Shooting'],
            'TOV': ['TOV', 'Turnovers']
        }

        for official_name, keywords in target_map.items():
            for col in df.columns:
                if any(kw.lower() in str(col).lower() for kw in keywords):
                    mapping[col] = official_name
                    break
        
        df = df.rename(columns=mapping)

        # 3. 过滤无效数据行（如重复表头或空行）
        if 'Player' in df.columns:
            df = df.dropna(subset=['Player'])
            df = df[df['Player'] != 'Player'].reset_index(drop=True)

        # 4. 强制转换数值，缺失补零
        essential_cols = ['G', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', 'TOV']
        for col in essential_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0 # 找不到列时填充 0，防止逻辑崩溃

        return df
        
    except Exception as e:
        st.error(f"数据处理异常: {str(e)}")
        return pd.DataFrame()

# --- PPI 计算与信号策略 ---
def calculate_ppi(df, version):
    df = df.copy()
    # 基础模型：PTS*1 + TRB*1.2 + AST*1.5
    df['PPI'] = df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5
    if version == "增强版":
        df['PPI'] += (df['STL'] * 1.5 + df['BLK'] * 2.0)
    return df

def main():
    st.set_page_config(page_title="RookieFlip2X", layout="wide")
    st.title("🏀 RookieFlip2X: NBA 新秀投资评估")
    
    with st.sidebar:
        season = st.selectbox("选择赛季", list(CSV_LINKS.keys()), index=2)
        min_g = st.slider("最少场次", 0, 82, 5)
        min_m = st.slider("最少分钟", 0.0, 40.0, 5.0)
        ver = st.radio("模型选择", ["基础版", "增强版"])

    df = fetch_and_clean_data(season)
    
    if not df.empty:
        # 使用清洗后确保存在的列名进行过滤
        mask = (df['G'] >= min_g) & (df['MP'] >= min_m)
        df_final = calculate_ppi(df[mask], ver).sort_values('PPI', ascending=False)
        
        if not df_final.empty:
            st.metric("📊 本届实时标王", df_final.iloc[0]['Player'], f"PPI: {df_final.iloc[0]['PPI']:.1f}")
            st.dataframe(df_final[['Player', 'PPI', 'PTS', 'TRB', 'AST', 'MP', 'G']], use_container_width=True)
            
            # 简易分布图
            st.plotly_chart(px.scatter(df_final, x='PTS', y='PPI', hover_name='Player', color='PPI', title="产出分布图"))
        else:
            st.warning("暂无符合过滤条件的球员。")

if __name__ == "__main__":
    main()
