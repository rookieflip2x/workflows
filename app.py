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
        
        # 统一列名映射 (处理场均数据与中文转换)
        # 注意：Basketball-Reference 的 CSV 中 .1 通常代表场均(Per Game)
        col_map = {
            'Player': '球员', 'PTS.1': '场均得分', 'TRB.1': '场均篮板', 
            'AST.1': '场均助攻', 'STL.1': '场均抢断', 'BLK.1': '场均盖帽', 
            'MP.1': '场均分钟', 'FG%': '命中率', 'G': '出场次数', 
            'TOV': '总失误', 'Rookie_Year': '届别'
        }
        
        # 检查并处理列名
        for eng, chn in col_map.items():
            if eng in df.columns:
                df[chn] = pd.to_numeric(df[eng], errors='coerce')
            elif eng.replace('.1', '') in df.columns:
                df[chn] = pd.to_numeric(df[eng.replace('.1', '')], errors='coerce')
        
        # 补全可能缺失的计算基础列
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

def calculate_metrics(df):
    """应用三套量化模型"""
    # 模型 1: 基础产出 (量能)
    df['基础产出'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + 
                    (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误'])
    
    # 模型 2: 效率加权 (质量)
    prod = df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)
    df['效率加权'] = prod * (df['命中率'] + 0.5) + (df['场均抢断'] + df['场均盖帽']) * 2.0
    
    # 模型 3: 进阶投资 (潜力)
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
        min_g = st.slider("最少出场次数 (样本过滤)", 1, 50, 5)
        min_mp = st.slider("最少场均分钟", 0, 35, 12)

    # --- 3. 趋势与数据处理 ---
    target_dt = pd.to_datetime(sel_date)
    past_dt = target_dt - timedelta(days=7)
    
    # 当前数据
    curr_df = calculate_metrics(df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy())
    # 历史数据 (用于算涨幅)
    past_df = calculate_metrics(df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] <= past_dt)]
                               .sort_values('Fetch_Date', ascending=False).head(200).copy())

    if not past_df.empty:
        trend = past_df.groupby('球员')[strategy].first().reset_index().rename(columns={strategy: 'prev_score'})
        curr_df = curr_df.merge(trend, on='球员', how='left')
        curr_df['7日涨幅'] = curr_df[strategy] - curr_df['prev_score']
    else:
        curr_df['7日涨幅'] = 0.0

    # 过滤与重排序号
    final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
    final_df = final_df.sort_values(strategy, ascending=False).reset_index(drop=True)
    final_df.index = final_df.index + 1 # 序号从1开始
    final_df.index.name = '排名'

    # 投资信号逻辑
    def get_signal(row):
        if row['7日涨幅'] > 2.0 and row[strategy] > final_df[strategy].quantile(0.8):
            return "🔥 强烈推荐"
        elif row['7日涨幅'] > 0:
            return "📈 状态上升"
        elif row['7日涨幅'] < -2.0:
            return "⚠️ 表现下滑"
        return "🔎 持续观察"
    
    final_df['投资建议'] = final_df.apply(get_signal, axis=1)

    # --- 4. 界面呈现 ---
    st.title(f"🏀 {sel_year} 届新秀量化分析 - {strategy}视角")
    
    # 顶层核心指标
    c1, c2, c3 = st.columns(3)
    with c1:
        top_gain = final_df.sort_values('7日涨幅', ascending=False).iloc[0]
        st.metric("本周爆发王", top_gain['球员'], f"+{top_gain['7日涨幅']:.2f}")
    with c2:
        top_val = final_df.iloc[0]
        st.metric("战力天花板", top_val['球员'], f"{top_val[strategy]:.2f}")
    with c3:
        st.metric("在榜人数", len(final_df))

    # 数据表格
    st.subheader("📋 球员量化分析表")
    show_cols = ['球员', '投资建议', strategy, '7日涨幅', '场均得分', '命中率', '场均分钟', '出场次数']
    st.dataframe(
        final_df[show_cols],
        use_container_width=True,
        column_config={
            strategy: st.column_config.NumberColumn(f"{strategy}总分", format="%.2f"),
            "7日涨幅": st.column_config.NumberColumn("7日变动", format="%+.2f"),
            "命中率": st.column_config.NumberColumn("命中率", format="%.3f"),
            "投资建议": st.column_config.TextColumn("信号")
        }
    )

    # 象限图分析
    st.divider()
    st.subheader("💡 投资机会识别 (评分 vs 增长)")
    fig = px.scatter(
        final_df, x=strategy, y='7日涨幅', color='投资建议',
        size='场均得分', hover_name='球员', text='球员',
        labels={strategy: '模型综合评分', '7日涨幅': '近7日趋势变动'},
        color_discrete_map={"🔥 强烈推荐": "#FF4B4B", "📈 状态上升": "#00CC96", "⚠️ 表现下滑": "#636EFA", "🔎 持续观察": "#FFAA00"}
    )
    fig.add_vline(x=final_df[strategy].mean(), line_dash="dash", line_color="gray")
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
