import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据源配置 ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        # 统一场均数据列名 (处理 .1 后缀)
        rename_map = {'PTS.1': 'PTS_PG', 'TRB.1': 'TRB_PG', 'AST.1': 'AST_PG',
                      'STL.1': 'STL_PG', 'BLK.1': 'BLK_PG', 'MP.1': 'MP_PG'}
        for old_col, new_col in rename_map.items():
            if old_col in df.columns:
                df[new_col] = pd.to_numeric(df[old_col], errors='coerce')
            else:
                orig_col = old_col.replace('.1', '')
                df[new_col] = pd.to_numeric(df[orig_col], errors='coerce')
        
        numeric_cols = ['PTS', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'FG%', 'MP', 'G']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"加载失败: {e}")
        return None

def calculate_all_ppi(df):
    """应用三套模型公式"""
    # 基础数据准备
    tov_pg = (df['TOV'] / df['G']).replace([np.inf, -np.inf], 0).fillna(0)
    
    # 1. 基础产出
    df['PPI_Basic'] = (df['PTS_PG'] + (df['TRB_PG'] * 1.2) + (df['AST_PG'] * 1.5) + 
                       (df['STL_PG'] * 2.0) + (df['BLK_PG'] * 2.0) - tov_pg)
    # 2. 效率加权
    df['PPI_Efficiency'] = (df['PTS_PG'] + (df['TRB_PG'] * 0.8) + (df['AST_PG'] * 1.2)) * \
                           (df['FG%'] + 0.5) + (df['STL_PG'] + df['BLK_PG']) * 2.0
    # 3. 进阶投资
    df['PPI_Growth'] = ((df['PTS_PG'] + df['TRB_PG'] + df['AST_PG']) / (df['MP_PG'] + 0.1) * 36) * \
                       (df['FG%'] * 1.1) - (tov_pg * 1.5)
    return df

# --- 2. 页面布局 ---
st.set_page_config(page_title="NBA新秀量化增长监控", layout="wide")

df_raw = load_data()

if df_raw is not None:
    with st.sidebar:
        st.title("📈 增长监控中心")
        years = sorted(df_raw['Rookie_Year'].unique(), reverse=True)
        sel_year = st.selectbox("选择届别", years)
        
        dates = sorted(df_raw[df_raw['Rookie_Year'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("当前观察日期", dates[0] if dates else None)
        
        strategy = st.radio("选择评估模型", ["基础产出 (量能)", "效率加权 (质量)", "进阶投资 (潜力)"])
        model_col = {"基础产出 (量能)": "PPI_Basic", "效率加权 (质量)": "PPI_Efficiency", "进阶投资 (潜力)": "PPI_Growth"}[strategy]
        
        min_mp = st.slider("最小场均时间", 0, 35, 12)

    # --- 3. 趋势计算逻辑 ---
    target_date = pd.to_datetime(sel_date)
    past_date = target_date - timedelta(days=7)
    
    # 获取当前和过去的数据集
    current_df = calculate_all_ppi(df_raw[(df_raw['Rookie_Year'] == sel_year) & (df_raw['Fetch_Date'] == target_date)].copy())
    past_df = calculate_all_ppi(df_raw[(df_raw['Rookie_Year'] == sel_year) & (df_raw['Fetch_Date'] <= past_date)].sort_values('Fetch_Date', ascending=False).head(len(current_df)).copy())

    # 合并趋势
    if not past_df.empty:
        trend_df = past_df[['Player', model_col]].rename(columns={model_col: 'prev_ppi'})
        current_df = current_df.merge(trend_df, on='Player', how='left')
        current_df['7日涨幅'] = current_df[model_col] - current_df['prev_ppi']
    else:
        current_df['7日涨幅'] = 0.0

    current_df = current_df[current_df['MP_PG'] >= min_mp].sort_values(model_col, ascending=False)

    # --- 4. 展示 ---
    st.title(f"🏀 {sel_year} 届新秀趋势分析 - {strategy}")
    
    # 涨幅榜 Top 3
    st.subheader("🚀 近 7 日表现飙升榜")
    gainers = current_df.sort_values('7日涨幅', ascending=False).head(3)
    c1, c2, c3 = st.columns(3)
    for i, (idx, row) in enumerate(gainers.iterrows()):
        [c1, c2, c3][i].metric(row['Player'], f"{row[model_col]:.2f}", f"{row['7日涨幅']:+.2f} (7D)")

    # 主表
    st.divider()
    st.dataframe(
        current_df[['Player', model_col, '7日涨幅', 'PTS_PG', 'FG%', 'MP_PG']],
        use_container_width=True,
        column_config={
            model_col: st.column_config.NumberColumn("当前评分", format="%.2f"),
            "7日涨幅": st.column_config.NumberColumn("趋势 (7D)", format="%+.2f"),
            "FG%": st.column_config.NumberColumn("命中率", format="%.3f")
        }
    )

    # 散点图：横轴评分，纵轴涨幅
    st.subheader("🔥 潜力与增长象限图")
    fig = px.scatter(
        current_df, x=model_col, y='7日涨幅', 
        size='MP_PG', color='7日涨幅', hover_name='Player',
        text='Player', color_continuous_scale='RdYlGn',
        labels={model_col: '当前综合评分', '7日涨幅': '7日评分变动'}
    )
    # 添加象限辅助线
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
