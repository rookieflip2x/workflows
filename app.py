import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据源配置 (已修复空格与Raw路径) ---
CSV_LINKS = {
    "2023-24": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2023-24_%20rookies%20.csv",
    "2024-25": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2024-25_rookies%20.csv",
    "2025-26": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2025-26_rookies%20.csv"
}

def fetch_and_clean_data(season):
    """专门针对该数据源设计的清洗逻辑"""
    try:
        url = CSV_LINKS.get(season)
        df_raw = pd.read_csv(url, on_bad_lines='skip')
        
        # 自动定位表头
        header_idx = None
        for i in range(len(df_raw.head(20))):
            if 'Player' in df_raw.iloc[i].astype(str).values:
                header_idx = i
                break
        
        if header_idx is not None:
            df = pd.read_csv(url, header=header_idx + 1)
        else:
            df = df_raw

        # 清理列名并归一化
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        mapping = {
            'Player': ['Player'], 'G': ['G', 'GP'], 'MP': ['MP'], 
            'PTS': ['PTS'], 'TRB': ['TRB'], 'AST': ['AST'], 
            'STL': ['STL'], 'BLK': ['BLK'], 'FG%': ['FG%'], 'TOV': ['TOV']
        }
        
        actual_map = {}
        for target, aliases in mapping.items():
            for col in df.columns:
                if any(alias == col for alias in aliases):
                    actual_map[col] = target
                    break
        df = df.rename(columns=actual_map)

        # 数值转换
        numeric_cols = ['PTS', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'MP', 'G', 'FG%']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df[df['Player'].notna() & (df['Player'] != 'Player')]
    except Exception as e:
        st.error(f"⚠️ 数据源读取失败: {e}")
        return pd.DataFrame()

# --- 2. 三种优化的PPI计算模型 ---
def calculate_ppi(df, mode):
    df = df.copy()
    if mode == "基础产出型 (Basic)":
        # 侧重传统全能表现
        df['PPI'] = df['PTS'] + df['TRB']*1.2 + df['AST']*1.5 + df['STL']*2 + df['BLK']*2 - df['TOV']
    
    elif mode == "效率加权型 (Efficiency)":
        # 惩罚低效出手，奖励精英效率
        df['PPI'] = (df['PTS'] + df['TRB']*0.8 + df['AST']*1.2) * (df['FG%'] + 0.5) + (df['STL'] + df['BLK'])*2
    
    elif mode == "进阶投资型 (Potential)":
        # 标准化为每36分钟产出，挖掘“板凳奇兵”
        df['MP_safe'] = df['MP'].replace(0, 1)
        df['PPI'] = ((df['PTS'] + df['TRB'] + df['AST']) / df['MP_safe'] * 36) * (df['FG%'] * 1.1) - (df['TOV'] * 1.5)
    
    df['PPI'] = df['PPI'].clip(lower=0)
    return df

# --- 3. 动态阈值信号系统 ---
def generate_signals(df):
    """根据当前数据集的分布自动生成信号"""
    if df.empty: return df
    
    p90 = df['PPI'].quantile(0.90)  # 前10%
    p75 = df['PPI'].quantile(0.75)  # 前25%
    p50 = df['PPI'].quantile(0.50)  # 中位数
    
    def signal_logic(row):
        val = row['PPI']
        if val >= p90: return '🚀 强力买入 (Top 10%)'
        if val >= p75: return '📈 建议买入 (Top 25%)'
        if val >= p50: return '📊 谨慎持有 (Top 50%)'
        return '⚖️ 观望/回避'
    
    df['Signal'] = df.apply(signal_logic, axis=1)
    return df

# --- 4. 主界面逻辑 ---
def main():
    st.set_page_config(page_title="RookieFlip2X Pro", layout="wide", page_icon="🏀")
    st.title("🏀 RookieFlip2X: NBA 新秀量化评估系统")
    st.markdown("---")

    # 侧边栏配置
    with st.sidebar:
        st.header("📊 参数设置")
        season = st.selectbox("选择赛季", list(CSV_LINKS.keys()), index=2)
        mode = st.radio("PPI 计算模型", ["基础产出型 (Basic)", "效率加权型 (Efficiency)", "进阶投资型 (Potential)"])
        st.divider()
        min_g = st.slider("最少出场次数", 0, 82, 5)
        min_m = st.slider("最少场均分钟", 0.0, 40.0, 10.0)

    # 数据处理流
    data = fetch_and_clean_data(season)
    
    if not data.empty:
        # 过滤并计算
        filtered_data = data[(data['G'] >= min_g) & (data['MP'] >= min_m)].copy()
        scored_data = calculate_ppi(filtered_data, mode)
        final_df = generate_signals(scored_data).sort_values('PPI', ascending=False)
        
        # 顶部指标卡
        top_player = final_df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("当届标王", top_player['Player'], f"PPI: {top_player['PPI']:.1f}")
        c2.metric("信号: 买入人数", len(final_df[final_df['Signal'].str.contains('买入')]))
        c3.metric("平均 PPI", f"{final_df['PPI'].mean():.1f}")
        c4.metric("样本总数", len(final_df))

        # 数据表格
        st.subheader("📋 球员量化评估清单")
        st.dataframe(
            final_df[['Player', 'PPI', 'Signal', 'PTS', 'TRB', 'AST', 'FG%', 'MP', 'G', 'TOV']],
            use_container_width=True,
            column_config={
                "PPI": st.column_config.NumberColumn(format="%.1f"),
                "FG%": st.column_config.ProgressColumn(min_value=0, max_value=1)
            }
        )

        # 可视化图表
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔥 产出与信号分布")
            fig_scatter = px.scatter(
                final_df, x='MP', y='PPI', color='Signal', 
                size='PTS', hover_name='Player',
                color_discrete_map={
                    '🚀 强力买入 (Top 10%)': '#FF4B4B',
                    '📈 建议买入 (Top 25%)': '#FFAA00',
                    '📊 谨慎持有 (Top 50%)': '#00CC96',
                    '⚖️ 观望/回避': '#636EFA'
                }
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        with col2:
            st.subheader("📈 PPI 分布直方图")
            fig_hist = px.histogram(final_df, x='PPI', nbins=20, color_discrete_sequence=['#0083B8'])
            st.plotly_chart(fig_hist, use_container_width=True)

    else:
        st.info("💡 请确保 GitHub 链接有效且文件格式正确。")

if __name__ == "__main__":
    main()
