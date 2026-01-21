import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据加载与处理 ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        # 字段映射
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
        st.error(f"数据加载失败: {e}")
        return None

def apply_ppi_models(df):
    """应用三套量化评估逻辑"""
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误'])
    df['效率加权评分'] = ((df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * (df['命中率'] + 0.5)) + (df['场均抢断'] + df['场均盖帽']) * 2.0
    df['进阶潜力评分'] = (((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - (df['场均失误'] * 1.5)
    return df

# --- 2. 页面配置 ---
st.set_page_config(page_title="NBA新秀量化数据分析", layout="wide")

# --- 合规声明模块 (顶部及侧边栏) ---
def show_disclaimer():
    with st.sidebar:
        st.warning("⚠️ **免责声明**")
        st.caption("""
        本系统提供的所有数据及评分仅供**学术交流与数据分析**参考，不构成任何形式的投资建议。
        球星卡及二级市场价格波动剧烈，历史表现不代表未来，请根据个人风险承受能力独立决策。
        """)
        st.divider()

show_disclaimer()

df_raw = load_data()

if df_raw is not None:
    with st.sidebar:
        st.header("🎯 策略控制台")
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期", dates[0] if dates else None)
        
        model_type = st.radio("量化评估模型", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_type}评分"
        
        min_g = st.slider("最少出场次数 (G)", 1, 82, 5)
        min_mp = st.slider("最少场均分钟 (MP)", 0, 48, 12)

    # --- 3. 计算与过滤 ---
    target_date = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_date)].copy()
    
    if not curr_df.empty:
        curr_df = apply_ppi_models(curr_df)
        past_date_limit = target_date - timedelta(days=7)
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] <= past_date_limit)]
        
        if not past_pool.empty:
            last_past = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past].copy())
            curr_df['7日涨幅'] = curr_df[strategy_col] - curr_df['球员'].map(past_data.set_index('球员')[strategy_col]).fillna(curr_df[strategy_col])
        else:
            curr_df['7日涨幅'] = 0.0

        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
        
        if not final_df.empty:
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index = final_df.index + 1

            # --- 合规化表述调整 ---
            def get_signal(row):
                if row['7日涨幅'] > 1.5 and row[strategy_col] > final_df[strategy_col].mean(): return "🔥 数据爆发"
                if row['7日涨幅'] > 0.5: return "📈 表现上扬"
                if row['7日涨幅'] < -1.5: return "📉 动态回撤"
                return "🔎 数据持平"
            
            final_df['模型信号'] = final_df.apply(get_signal, axis=1)

            # --- 4. 界面呈现 ---
            st.title(f"📊 {sel_year} 届新秀量化数据看板 ({model_type})")
            
            # 帮助说明
            with st.expander("ℹ️ 数据模型与信号算法说明 (点击展开)"):
                st.write("""
                - **模型逻辑**：基于球员场均产出、效率及分钟数加权得出。
                - **信号说明**：
                    - **数据爆发**：评分显著高于平均水平且近期增幅明显。
                    - **表现上扬**：近期数据趋势向好。
                    - **动态回撤**：近期表现较上一观察点有所下滑。
                - **声明**：本看板仅呈现统计学层面的数据波动。
                """)

            # 4.1 表格呈现
            def style_signal(val):
                colors = {"🔥 数据爆发": "background-color: #ff4b4b; color: white", 
                          "📈 表现上扬": "background-color: #e8f8f5; color: #117a65",
                          "📉 动态回撤": "background-color: #fded
