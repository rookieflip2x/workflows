import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据加载与逻辑 (保持之前的优化版本) ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=600)
def load_and_clean_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        if 'Player' in df.columns: df['球员'] = df['Player']
        elif '球员' not in df.columns: df['球员'] = df.iloc[:, 1]

        col_map = {
            'PTS.1': '场均得分', 'TRB.1': '场均篮板', 'AST.1': '场均助攻', 
            'STL.1': '场均抢断', 'BLK.1': '场均盖帽', 'MP.1': '场均分钟', 
            'FG%': '命中率', 'G': '出场次数', 'TOV': '总失误', 'Rookie_Year': '届别'
        }
        for eng, chn in col_map.items():
            if eng in df.columns: df[chn] = pd.to_numeric(df[eng], errors='coerce')
            elif eng.replace('.1', '') in df.columns: df[chn] = pd.to_numeric(df[eng.replace('.1', '')], errors='coerce')
        
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        calc_cols = ['场均得分', '场均篮板', '场均助攻', '场均抢断', '场均盖帽', '场均分钟', '命中率', '场均失误']
        for col in calc_cols:
            if col in df.columns: df[col] = df[col].fillna(0)
        return df
    except Exception as e:
        st.error(f"加载失败: {e}")
        return None

def apply_ppi_models(df):
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误'])
    prod = df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)
    df['效率加权评分'] = (prod * (df['命中率'] + 0.5)) + (df['场均抢断'] + df['场均盖帽']) * 2.0
    df['进阶潜力评分'] = (((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - (df['场均失误'] * 1.5)
    return df

# --- 2. 页面布局 ---
st.set_page_config(page_title="NBA新秀量化投资系统", layout="wide")

df_raw = load_and_clean_data()

if df_raw is not None:
    with st.sidebar:
        st.title("🎯 策略配置")
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择新秀届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期快照", dates[0] if dates else None)
        
        model_name = st.radio("选择评估模型", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_name}评分"
        
        st.divider()
        min_g = st.slider("最少出场次数 (G)", 1, 82, 5)
        min_mp = st.slider("最少场均分钟 (MP)", 0, 48, 12)

        # --- 侧边栏说明：模型用法 ---
        st.divider()
        with st.expander("📚 三大模型用法指南", expanded=False):
            st.markdown(f"""
            **1. 基础产出 (量能)**
            - **核心：** 填满数据栏的能力。
            - **场景：** 寻找球队的“基石型”新秀，数据越全面分越高。
            
            **2. 效率加权 (质量)**
            - **核心：** 惩罚低效出手。
            - **场景：** 寻找“精英蓝领”或“高效得分手”，避免被高产低效的球员误导。
            
            **3. 进阶潜力 (潜力)**
            - **核心：** 每36分钟效率修正。
            - **场景：** **捡漏神器**。发掘出场时间少但产出极高的“板凳悍将”。
            """)

    # --- 3. 核心计算逻辑 (略, 同前文) ---
    target_date = pd.to_datetime(sel_date)
    curr_data = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_date)].copy()
    
    if not curr_data.empty:
        curr_data = apply_ppi_models(curr_data)
        past_date_limit = target_date - timedelta(days=7)
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] <= past_date_limit)]
        
        if not past_pool.empty:
            last_past_date = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past_date].copy())
            trend_map = past_data.set_index('球员')[strategy_col]
            curr_data['7日涨幅'] = curr_data['球员'].map(trend_map)
            curr_data['7日涨幅'] = curr_data[strategy_col] - curr_data['7日涨幅'].fillna(curr_data[strategy_col])
        else:
            curr_data['7日涨幅'] = 0.0

        final_df = curr_data[(curr_data['出场次数'] >= min_g) & (curr_data['场均分钟'] >= min_mp)].copy()

        if not final_df.empty:
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index = final_df.index + 1
            final_df.index.name = '排名'

            def get_investment_signal(row):
                score = row[strategy_col]
                growth = row['7日涨幅']
                if growth > 1.5 and score > final_df[strategy_col].mean(): return "🔥 强烈推荐"
                if growth > 0.5: return "📈 状态上升"
                if growth < -1.5: return "⚠️ 表现下滑"
                return "🔎 持续观察"
            
            final_df['投资建议'] = final_df.apply(get_investment_signal, axis=1)

            # --- 4. 页面主体：信号释义 ---
            st.title(f"🏀 {sel_year} 届新秀量化分析 - {model_name}模型")
            
            # 使用 Callout 形式展示信号含义
            help_col1, help_col2 = st.columns([2, 1])
            with help_col1:
                st.info("""
                **🚦 信号灯说明：**
                - **🔥 强烈推荐**：评分高于平均水平，且近 7 日评分大幅度爆发。通常预示卡价上涨空间大。
                - **📈 状态上升**：近期表现稳步提升。
                - **⚠️ 表现下滑**：近期表现明显缩水，可能面临“新秀墙”或伤病影响。
                - **🔎 持续观察**：数据波动平稳，适合长线跟踪。
                """)
            
            # (下接之前的指标、表格和象限图代码...)
            c1, c2, c3 = st.columns(3)
            c1.metric("战力榜首", final_df.iloc[0]['球员'], f"{final_df.iloc[0][strategy_col]:.2f}")
            top_gainer = final_df.sort_values('7日涨幅', ascending=False).iloc[0]
            c2.metric("近期爆发王", top_gainer['球员'], f"{top_gainer['7日涨幅']:+.2f}")
            c3.metric("有效样本数", len(final_df))

            st.dataframe(
                final_df[['球员', '投资建议', strategy_col, '7日涨幅', '场均得分', '命中率', '场均分钟', '出场次数']],
                use_container_width=True
            )
            
            # 象限图
            st.divider()
            st.subheader("💡 投资象限图")
            fig = px.scatter(final_df, x=strategy_col, y='7日涨幅', color='投资建议', size='场均得分', hover_name='球员', text='球员')
            st.plotly_chart(fig, use_container_width=True)
