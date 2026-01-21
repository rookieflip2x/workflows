import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据源与清洗配置 ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        # 核心修复：确保找到“球员”列名，优先匹配 Player 或 球员
        if 'Player' in df.columns:
            df['球员'] = df['Player']
        elif '球员' not in df.columns:
            df['球员'] = df.iloc[:, 1] # 兜底逻辑：取第二列

        # 统一列名映射 (处理 .1 后缀)
        col_map = {
            'PTS.1': '场均得分', 'TRB.1': '场均篮板', 'AST.1': '场均助攻', 
            'STL.1': '场均抢断', 'BLK.1': '场均盖帽', 'MP.1': '场均分钟', 
            'FG%': '命中率', 'G': '出场次数', 'TOV': '总失误', 'Rookie_Year': '届别'
        }
        
        for eng, chn in col_map.items():
            if eng in df.columns:
                df[chn] = pd.to_numeric(df[eng], errors='coerce')
            elif eng.replace('.1', '') in df.columns:
                df[chn] = pd.to_numeric(df[eng.replace('.1', '')], errors='coerce')
        
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

def calculate_metrics(df):
    """应用三套量化模型公式"""
    cols = ['场均得分', '场均篮板', '场均助攻', '场均抢断', '场均盖帽', '场均分钟', '命中率', '场均失误']
    for c in cols:
        if c not in df.columns: df[c] = 0
            
    # 模型 1: 基础产出
    df['基础产出'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + 
                    (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误'])
    # 模型 2: 效率加权
    df['效率加权'] = (df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * \
                    (df['命中率'] + 0.5) + (df['场均抢断'] + df['场均盖帽']) * 2.0
    # 模型 3: 进阶潜力
    df['进阶潜力'] = ((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * \
                    (df['命中率'] * 1.1) - (df['场均失误'] * 1.5)
    return df

# --- 2. 页面设置 ---
st.set_page_config(page_title="NBA新秀量化投资系统", layout="wide")

df_raw = load_data()

if df_raw is not None:
    with st.sidebar:
        st.header("🔍 筛选与策略")
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择新秀届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        if dates:
            sel_date = st.date_input("分析快照日期", dates[0])
        else:
            sel_date = st.date_input("分析快照日期")
        
        strategy = st.radio("量化投资模型", ["基础产出", "效率加权", "进阶潜力"])
        
        st.divider()
        min_g = st.slider("最少出场次数 (G)", 1, 82, 5)
        min_mp = st.slider("最少场均分钟 (MP)", 0, 48, 12)

    # --- 3. 数据处理 ---
    target_dt = pd.to_datetime(sel_date)
    past_dt = target_dt - timedelta(days=7)
    
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if curr_df.empty:
        st.warning(f"⚠️ 暂无 {sel_date} 的抓取记录。")
    else:
        curr_df = calculate_metrics(curr_df)
        
        # 寻找趋势数据
        all_past = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] <= past_dt)]
        if not all_past.empty:
            last_past_date = all_past['Fetch_Date'].max()
            past_snapshot = calculate_metrics(all_past[all_past['Fetch_Date'] == last_past_date].copy())
            trend = past_snapshot[['球员', strategy]].rename(columns={strategy: 'prev_score'})
            curr_df = curr_df.merge(trend, on='球员', how='left')
            curr_df['7日涨幅'] = curr_df[strategy] - curr_df['prev_score'].fillna(curr_df[strategy])
        else:
            curr_df['7日涨幅'] = 0.0

        # 过滤与重排序号
        final_df
