import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据源配置 ---
CSV_LINKS = {
    "2023-24 赛季": "https://raw.githubusercontent.com/rookieflip2x/workflows/main/NBA_2023-24_rookies.csv",
    "2024-25 赛季": "https://raw.githubusercontent.com/rookieflip2x/workflows/main/NBA_2024-25_rookies%20.csv",
    "2025-26 赛季": "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/NBA_2025-26_rookies%20.csv"
}

def fetch_and_clean_data(season):
    """针对 GitHub 数据源优化的中文清洗逻辑"""
    try:
        url = CSV_LINKS.get(season)
        df_raw = pd.read_csv(url, on_bad_lines='skip')
        
        # 定位表头
        header_idx = None
        for i in range(len(df_raw.head(20))):
            if 'Player' in df_raw.iloc[i].astype(str).values:
                header_idx = i
                break
        
        if header_idx is not None:
            df = pd.read_csv(url, header=header_idx + 1)
        else:
            df = df_raw

        # 清理列名并进行中文映射
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # 建立英文原始字段与中文展示字段的映射
        mapping = {
            '球员': ['Player'], '场次': ['G', 'GP'], '分钟': ['MP'], 
            '得分': ['PTS'], '篮板': ['TRB'], '助攻': ['AST'], 
            '抢断': ['STL'], '盖帽': ['BLK'], '命中率': ['FG%'], '失误': ['TOV']
        }
        
        actual_map = {}
        for target, aliases in mapping.items():
            for col in df.columns:
                if any(alias == col for alias in aliases):
                    actual_map[col] = target
                    break
        df = df.rename(columns=actual_map)

        # 数值转换
        numeric_cols = ['得分', '篮板', '助攻', '抢断', '盖帽', '失误', '分钟', '场次', '命中率']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df[df['球员'].notna() & (df['球员'] != 'Player')]
    except Exception as e:
        st.error(f"⚠️ 数据源读取失败: {e}")
        return pd.DataFrame()

# --- 2. 三种优化的 PPI 计算模型 ---
def calculate_ppi(df, mode):
    df = df.copy()
    if mode == "基础产出型":
        # 侧重传统全能表现
        df['PPI'] = df['得分'] + df['篮板']*1.2 + df['助攻']*1.5 + df['抢断']*2 + df['盖帽']*2 - df['失误']
    
    elif mode == "效率加权型":
        # 奖励精英效率
        df['PPI'] = (df['得分'] + df['篮板']*0.8 + df['助攻']*1.2) * (df['命中率'] + 0.5) + (df['抢断'] + df['盖帽'])*2
    
    elif mode == "进阶投资型":
        # 标准化为每 36 分钟产出
        df['分钟_安全'] = df['分钟'].replace(0, 1)
        df['PPI'] = ((df['得分'] + df['篮板'] + df['助攻']) / df['分钟_安全'] * 36) * (df['命中率'] * 1.1) - (df['失误'] * 1.5)
    
    df['PPI'] = df['PPI'].clip(lower=0)
    return df

# --- 3. 动态阈值信号系统 ---
def generate_signals(df):
    if df.empty: return df
    
    p90 = df['PPI'].quantile(0.90)
    p75 = df['PPI'].quantile(0.75)
    p50 = df['PPI'].quantile(0.50)
    
    def signal_logic(val):
        if val >= p90: return '🚀 强力买入 (前10%)'
        if val >= p75: return '📈 建议买入 (前25%)'
        if val >= p50: return '📊 谨慎持有 (前50%)'
        return '⚖️ 观望回避'
    
    df['投资信号'] = df['PPI'].apply(signal_logic)
    return df

# --- 4. 主界面逻辑 ---
def main():
    st.set_page_config(page_title="RookieFlip2X 专业版", layout="wide", page_icon="🏀")
    st.title("🏀 RookieFlip2X: NBA 新秀量化评估系统")
    st.markdown("---")

    # 侧边栏配置
    with st.sidebar:
        st.header("📊 系统设置")
        season = st.selectbox("选择赛季", list(CSV_LINKS.keys()), index=2)
        mode = st.radio("选择 PPI 计算模型", ["基础产出型", "效率加权型", "进阶投资型"])
        st.divider()
        min_g = st.slider("最少出场次数", 0, 82, 5)
        min_m = st.slider("最少场均分钟", 0.0, 40.0, 10.0)

    # 数据处理
    data = fetch_and_clean_data(season)
    
    if not data.empty:
        # 过滤并计算
        filtered_data = data[(data['场次'] >= min_g) & (data['分钟'] >= min_m)].copy()
        scored_data = calculate_ppi(filtered_data, mode)
        final_df = generate_signals(scored_data).sort_values('PPI', ascending=False)
        
        # 顶部指标卡
        if not final_df.empty:
            top_player = final_df.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("当届标王", top_player['球员'], f"PPI: {top_player['PPI']:.1f}")
            c2.metric("推荐买入人数", len(final_df[final_df['投资信号'].str.contains('买入')]))
            c3.metric("赛季平均 PPI", f"{final_df['PPI'].mean():.1f}")
            c4.metric("有效样本数", len(final_df))

            # 数据表格更新为中文题目
            st.subheader("📋 球员价值量化评估清单")
            st.dataframe(
                final_df[['球员', 'PPI', '投资信号', '得分', '篮板', '助攻', '命中率', '分钟', '场次', '失误']],
                use_container_width=True,
                column_config={
                    "PPI": st.column_config.NumberColumn("综合评分", format="%.1f"),
                    "命中率": st.column_config.ProgressColumn("投篮效率", min_value=0, max_value=1)
                }
            )

            # 可视化图表
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔥 产出与信号分布图")
                fig_scatter = px.scatter(
                    final_df, x='分钟', y='PPI', color='投资信号', 
                    size='得分', hover_name='球员',
                    labels={'分钟': '场均上场时间', 'PPI': '综合评分 (PPI)'},
                    color_discrete_map={
                        '🚀 强力买入 (前10%)': '#FF4B4B',
                        '📈 建议买入 (前25%)': '#FFAA00',
                        '📊 谨慎持有 (前50%)': '#00CC96',
                        '⚖️ 观望回避': '#636EFA'
                    }
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            with col2:
                st.subheader("📈 PPI 分布直方图")
                fig_hist = px.histogram(
                    final_df, x='PPI', nbins=20, 
                    labels={'PPI': '综合评分区间', 'count': '球员人数'},
                    color_discrete_sequence=['#0083B8']
                )
                st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.warning("⚠️ 没有符合当前筛选条件的球员数据。")
    else:
        st.info("💡 系统正在载入数据，请确保网络连接正常。")

if __name__ == "__main__":
    main()
