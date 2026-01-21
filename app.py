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
        
        # 核心修复：确保找到“球员”列
        # 检查原始列名中是否有 'Player' 或 '球员'
        if 'Player' in df.columns:
            df['球员'] = df['Player']
        elif '球员' not in df.columns:
            # 如果都没有，尝试取第二列（通常是球员名）
            df['球员'] = df.iloc[:, 1]

        # 统一场均数据映射 (处理 .1 后缀)
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
        
        # 补全计算列
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

def calculate_metrics(df):
    """应用三套量化模型"""
    # 确保字段存在，防止计算报错
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
        sel_date = st.date_input("分析快照日期", dates[0] if dates else None)
        
        strategy = st.radio("量化投资模型", ["基础产出", "效率加权", "进阶潜力"])
        
        st.divider()
        min_g = st.slider("最少出场次数 (G)", 1, 82, 5) # 修正：最大场次设为82
        min_mp = st.slider("最少场均分钟 (MP)", 0, 48, 12)

    # --- 3. 数据处理 ---
    target_dt = pd.to_datetime(sel_date)
    past_dt = target_dt - timedelta(days=7)
    
    # 当前选定日期的数据
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if curr_df.empty:
        st.warning(f"⚠️ 暂无 {sel_date} 的抓取记录，请尝试其他日期。")
    else:
        curr_df = calculate_metrics(curr_df)
        
        # 寻找 7 天前的数据算趋势
        past_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] <= past_dt)].sort_values('Fetch_Date', ascending=False)
        if not past_df.empty:
            past_snapshot = calculate_metrics(past_df[past_df['Fetch_Date'] == past_df['Fetch_Date'].iloc[0]].copy())
            trend = past_snapshot[['球员', strategy]].rename(columns={strategy: 'prev_score'})
            curr_df = curr_df.merge(trend, on='球员', how='left')
            curr_df['7日涨幅'] = curr_df[strategy] - curr_df['prev_score'].fillna(curr_df[strategy])
        else:
            curr_df['7日涨幅'] = 0.0

        # 过滤与重排序号
        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
        final_df = final_df.sort_values(strategy, ascending=False).reset_index(drop=True)
        final_df.index = final_df.index + 1 # 生成新排名序号

        # 信号灯逻辑
        def get_signal(row):
            score = row[strategy]
            growth = row['7日涨幅']
            if growth > 1.5 and score > final_df[strategy].mean(): return "🔥 强烈推荐"
            if growth > 0.5: return "📈 状态上升"
            if growth < -1.5: return "⚠️ 表现下滑"
            return "🔎 持续观察"
        
        final_df['投资建议'] = final_df.apply(get_signal, axis=1)

        # --- 4. 界面呈现 ---
        st.title(f"🏀 {sel_year} 届新秀量化分析 - {strategy}视角")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("战力榜首", final_df.iloc[0]['球员'], f"{final_df.iloc[0][strategy]:.2f}")
        with c2:
            top_gainer = final_df.sort_values('7日涨幅', ascending=False).iloc[0]
            st.metric("本周爆发", top_gainer['球员'], f"{top_gainer['7日涨幅']:+.2f}")
        with c3:
            st.metric("在榜人数", len(final_df))

        # 数据主表
        st.subheader("📋 球员量化排行榜")
        # 确保列名列表完全匹配生成的中文列名
        show_cols = ['球员', '投资建议', strategy, '7日涨幅', '场均得分', '命中率', '场均分钟', '出场次数']
        st.dataframe(
            final_df[show_cols],
            use_container_width=True,
            column_config={
                strategy: st.column_config.NumberColumn(f"{strategy}总分", format="%.2f"),
                "7日涨幅": st.column_config.NumberColumn("7日趋势", format="%+.2f"),
                "命中率": st.column_config.NumberColumn("FG%", format="%.3f"),
                "投资建议": st.column_config.TextColumn("信号指示")
            }
