import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')

# 确保链接包含转义字符 %20
CSV_LINKS = {
    "2023-24": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2023-24_%20rookies%20.csv",
    "2024-25": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2024-25_rookies%20.csv",
    "2025-26": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2025-26_rookies%20.csv"
}

def fetch_and_clean_data(season):
    """
    针对 arg must be a list... 错误优化的清洗函数
    """
    try:
        url = CSV_LINKS.get(season)
        # 1. 加载原始数据
        df_raw = pd.read_csv(url, on_bad_lines='skip')
        
        # 2. 精确定位表头行
        # 遍历前20行，找到真正包含“Player”的一行
        header_row_index = None
        for i in range(len(df_raw.head(20))):
            row_values = df_raw.iloc[i].astype(str).tolist()
            if 'Player' in row_values:
                header_row_index = i
                break
        
        if header_row_index is not None:
            # 重新读取，以找到的行作为 header
            df = pd.read_csv(url, header=header_row_index + 1)
        else:
            df = df_raw

        # 3. 稳健的列名清洗
        # 移除列名中的换行符和多余空格
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        # 4. 字段归一化 (核心修复点)
        # 即使 CSV 结构变化，也能通过关键词锁定数据
        target_map = {
            'Player': ['Player'],
            'G': ['G', 'GP', 'Games'],
            'MP': ['MP', 'Min'],
            'PTS': ['PTS', 'Points'],
            'TRB': ['TRB', 'Rebounds'],
            'AST': ['AST', 'Assists'],
            'STL': ['STL', 'Steals'],
            'BLK': ['BLK', 'Blocks'],
            'FG%': ['FG%'],
            'TOV': ['TOV', 'Turnovers']
        }

        final_mapping = {}
        for official_name, keywords in target_map.items():
            for col in df.columns:
                if any(kw == col or f" {kw}" in col or f"{kw} " in col for kw in keywords):
                    final_mapping[col] = official_name
                    break
        
        df = df.rename(columns=final_mapping)

        # 5. 移除数据中的重复表头行和空行
        if 'Player' in df.columns:
            df = df[df['Player'].notna()]
            df = df[df['Player'] != 'Player'].reset_index(drop=True)

        # 6. 安全的数值转换 (防止 KeyError 和 TypeError)
        essential_cols = ['G', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', 'TOV']
        for col in essential_cols:
            if col in df.columns:
                # 确保传入 to_numeric 的是一个 Series
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                # 缺失列补零，确保后续计算不报错
                df[col] = 0.0
                
        return df
        
    except Exception as e:
        st.error(f"数据处理异常: {str(e)}")
        return pd.DataFrame()

def calculate_ppi(df, version):
    df = df.copy()
    # 确保列存在后再计算
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
        # 过滤
        mask = (df['G'] >= min_g) & (df['MP'] >= min_m)
        df_filtered = df[mask]
        
        if not df_filtered.empty:
            df_final = calculate_ppi(df_filtered, ver).sort_values('PPI', ascending=False)
            
            # 显示
            st.metric("📊 本届实时标王", df_final.iloc[0]['Player'], f"PPI: {df_final.iloc[0]['PPI']:.1f}")
            
            # 最终展示列
            display_cols = ['Player', 'PPI', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'MP', 'G']
            valid_display = [c for c in display_cols if c in df_final.columns]
            
            st.dataframe(df_final[valid_display], use_container_width=True)
            
            st.plotly_chart(px.scatter(df_final, x='PTS', y='PPI', hover_name='Player', 
                                     size='MP', color='PPI', title="产出分布图 (点大小代表时间)"))
        else:
            st.warning("暂无符合过滤条件的球员。")
    else:
        st.info("正在等待数据加载或数据源配置中...")

if __name__ == "__main__":
    main()
