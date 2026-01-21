import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据源配置 ---
# 请将下方链接替换为你 GitHub 仓库中 nba_rookies_combined.csv 的 Raw 链接
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

def load_data():
    """读取每日更新的汇总数据"""
    try:
        df = pd.read_csv(DATA_URL)
        # 确保日期格式正确
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        return df
    except Exception as e:
        st.error(f"加载数据失败，请检查链接或文件是否存在: {e}")
        return None

def process_ppi(df):
    """针对汇总文件优化的 PPI 分析逻辑"""
    # 1. 基础列映射与清洗
    rename_dict = {
        'Player': '球员', 'Age': '年龄', 'G': '出场', 'MP': '分钟',
        'PTS': '得分', 'TRB': '篮板', 'AST': '助攻', 'STL': '抢断',
        'BLK': '盖帽', 'FG%': '命中率', '3P': '三分', 'Rookie_Year': '赛季'
    }
    df = df.rename(columns=rename_dict)
    
    # 2. 转换数值类型（强制转换防止报错）
    numeric_cols = ['年龄', '出场', '分钟', '得分', '篮板', '助攻', '抢断', '盖帽', '命中率', '三分']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. 计算 PPI (Player Performance Index)
    # 权重公式：得分*1 + 篮板*1.2 + 助攻*1.5 + 抢断*2 + 盖帽*2 - 三分*0.5 (可根据喜好调整)
    df['PPI'] = (df['得分'] * 1.0 + df['篮板'] * 1.2 + df['助攻'] * 1.5 + 
                 df['抢断'] * 2.0 + df['盖帽'] * 2.0) / (df['分钟'] + 1)
    
    # 4. 投资信号判断
    q75 = df['PPI'].quantile(0.75)
    q90 = df['PPI'].quantile(0.90)
    q50 = df['PPI'].quantile(0.50)

    def get_signal(ppi):
        if ppi >= q90: return '🚀 强力买入 (前10%)'
        if ppi >= q75: return '📈 建议买入 (前25%)'
        if ppi >= q50: return '📊 谨慎持有 (前50%)'
        return '⚖️ 观望回避'

    df['投资信号'] = df['PPI'].apply(get_signal)
    return df

# --- 页面 UI 部分 ---
st.set_page_config(page_title="NBA 新秀每日监控", layout="wide")
st.title("🏀 NBA 新秀投资分析看板 (基于每日最新抓取)")

raw_df = load_data()

if raw_df is not None:
    # 侧边栏筛选
    with st.sidebar:
        st.header("控制面板")
        
        # 赛季选择
        target_year = st.selectbox("选择新秀届别", sorted(raw_df['Rookie_Year'].unique(), reverse=True))
        
        # 自动定位该赛季最新的抓取日期
        season_df = raw_df[raw_df['Rookie_Year'] == target_year]
        latest_date = season_df['Fetch_Date'].max()
        
        selected_date = st.date_input("查看历史快照 (默认最新)", latest_date)
        
    # 过滤数据：指定赛季 + 指定日期
    final_df = season_df[season_df['Fetch_Date'] == pd.to_datetime(selected_date)]
    
    if final_df.empty:
        st.warning(f"⚠️ {selected_date} 这一天没有抓取到数据，请选择其他日期。")
    else:
        final_df = process_ppi(final_df)
        
        # 数据看板
        st.metric("分析球员总数", len(final_df), f"更新日期: {selected_date}")
        
        # 展示表格
        st.subheader(f"🔥 {target_year} 届新秀战力排行")
        st.dataframe(
            final_df[['球员', '投资信号', 'PPI', '得分', '篮板', '助攻', '命中率', '分钟']].sort_values('PPI', ascending=False),
            use_container_width=True,
            column_config={
                "PPI": st.column_config.NumberColumn("综合评分", format="%.2f"),
                "命中率": st.column_config.NumberColumn("FG%", format="%.3f")
            }
        )

        # 可视化
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("分析分布图")
            fig = px.scatter(final_df, x='分钟', y='PPI', color='投资信号', size='得分', hover_name='球员')
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.subheader("各队新秀 PPI 贡献")
            # 假设原始数据中有 Team (Tm) 列
            if 'Tm' in final_df.columns:
                fig_team = px.box(final_df, x='Tm', y='PPI', color='Tm')
                st.plotly_chart(fig_team, use_container_width=True)
