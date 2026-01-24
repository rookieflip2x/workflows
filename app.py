import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import warnings

# 忽略不必要的警告
warnings.filterwarnings('ignore')

# --- NBA 官方配色定义 ---
NBA_BLUE = "#17408B"
NBA_RED = "#C9082A"
NBA_WHITE = "#FFFFFF"

# --- 1. 数据加载与处理逻辑 ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=600)
def load_and_clean_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        if 'Player' in df.columns:
            df['球员'] = df['Player']
        elif '球员' not in df.columns:
            df['球员'] = df.iloc[:, 1]

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
        
        calc_cols = ['场均得分', '场均篮板', '场均助攻', '场均抢断', '场均盖帽', '场均分钟', '命中率', '场均失误']
        for col in calc_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
                
        return df
    except Exception as e:
        st.error(f"❌ 数据源加载失败: {e}")
        return None

def apply_ppi_models(df):
    """应用 RookieFlip2x 评价模型逻辑"""
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + 
                       (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误']).round(2)
    df['效率加权评分'] = (((df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * (df['命中率'] + 0.5)) + \
                       (df['场均抢断'] + df['场均盖帽']) * 2.0).round(2)
    df['进阶潜力评分'] = ((((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - \
                       (df['场均失误'] * 1.5)).round(2)
    return df

# --- 2. 页面设置 ---
st.set_page_config(page_title="RookieFlip2x 乐翻新秀数据评价系统", layout="wide")

# --- 侧边栏 ---
with st.sidebar:
    st.title("🚀 RookieFlip2x")
    st.caption("乐翻新秀 · 数字化评价系统")
    st.divider()
    
    df_raw = load_and_clean_data()
    
    if df_raw is not None:
        st.header("🎯 策略控制台")
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期快照", dates[0] if dates else None)
        
        model_name = st.radio("选择评价维度", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_name}评分"

        with st.expander("📝 评价维度指南", expanded=True):
            st.markdown("""
            | 维度名称 | 核心优势 | 适用场景 |
            | :--- | :--- | :--- |
            | **基础产出** | 全面反映产出 | 评估最佳新秀归属 |
            | **效率加权** | 衡量进攻纯度 | 发现高效球星胚子 |
            | **进阶潜力** | 挖掘单位上限 | 识别潜力“板凳匪徒” |
            """)
        
        st.divider()
        st.subheader("🛠️ 样本过滤")
        min_g = st.slider("最少出场次数", 1, 82, 5)
        min_mp = st.slider("最少场均分钟", 0, 48, 12)

# --- 3. 核心计算逻辑 ---
if df_raw is not None:
    # 3.1 届别成色分析 (大年/小年对比)
    st.title("🏆 RookieFlip2x 乐翻新秀数据评价系统")
    
    # 计算各届平均分
    all_years_data = apply_ppi_models(df_raw.copy())
    # 取每个球员最新的快照进行统计
    latest_stats = all_years_data.sort_values('Fetch_Date').groupby(['届别', '球员']).tail(1)
    year_comparison = latest_stats.groupby('届别')[strategy_col].mean().round(2).reset_index()
    year_comparison.columns = ['届别', '平均产出评分']
    
    with st.container():
        st.subheader("📅 届别成色分析 (大年/小年对比)")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write(f"当前策略：**{model_name}**")
            st.dataframe(year_comparison.sort_values('平均产出评分', ascending=False), hide_index=True)
        with col2:
            fig_year = px.bar(year_comparison, x='届别', y='平均产出评分', 
                             title="各届新秀整体表现对比",
                             color='平均产出评分',
                             color_continuous_scale=[NBA_RED, NBA_BLUE])
            fig_year.update_layout(height=300, margin=dict(t=30, b=0))
            st.plotly_chart(fig_year, use_container_width=True)

    st.divider()

    # 3.2 实时数据处理
    target_dt = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if curr_df.empty:
        st.info(f"📅 暂无日期 {sel_date} 的数据，请切换日期。")
    else:
        curr_df = apply_ppi_models(curr_df)
        
        # 变动趋势计算
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] < target_dt)]
        if not past_pool.empty:
            last_past = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past].copy())
            diff = curr_df[strategy_col] - curr_df['球员'].map(past_data.set_index('球员')[strategy_col]).fillna(curr_df[strategy_col])
            curr_df['变动趋势'] = diff.round(2)
        else:
            curr_df['变动趋势'] = 0.00

        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
        
        if final_df.empty:
            st.error("❌ 筛选条件过严，当前无符合条件的球员。")
        else:
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index = final_df.index + 1
            final_df.index.name = "排名"

            def get_model_signal(row):
                score, growth = row[strategy_col], row['变动趋势']
                avg_score = final_df[strategy_col].mean()
                if growth > 1.5 and score > avg_score: return "🔥 手感火热"
                if growth > 0.5: return "🆙 状态复苏"
                if growth < -1.5: return "❄️ 陷入低迷"
                if score > avg_score * 1.3: return "👑 基石表现"
                return "🕒 待机状态"
            
            final_df['模型信号'] = final_df.apply(get_model_signal, axis=1)

            # --- 4. 战力榜展示 ---
            st.subheader(f"📋 {sel_year} 届实时战力榜 - {model_name}")

            def color_cell(val):
                colors = {
                    "🔥 手感火热": f"background-color: {NBA_RED}; color: white; font-weight: bold;",
                    "🆙 状态复苏": "background-color: #e8f8f5; color: #117a65;",
                    "❄️ 陷入低迷": "background-color: #fdedec; color: #943126;",
                    "👑 基石表现": f"background-color: {NBA_BLUE}; color: white; font-weight: bold;",
                    "🕒 待机状态": "background-color: #f8f9f9; color: #7f8c8d;"
                }
                return colors.get(val, "")

            display_cols = ['球员', '模型信号', strategy_col, '变动趋势', '场均得分', '命中率', '场均分钟', '出场次数']
            st.dataframe(
                final_df[display_cols].style.format({
                    strategy_col: "{:.2f}",
                    "变动趋势": "{:+.2f}",
                    "命中率": "{:.3f}"
                }).applymap(color_cell, subset=['模型信号']),
                use_container_width=True
            )

            # 4.2 球员对标与曲线 (NBA 配色)
            st.divider()
            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("⚔️ 球员多维对标")
                pk_players = st.multiselect("对比球员", final_df['球员'].unique(), default=final_df['球员'].head(2).tolist())
                if pk_players:
                    fig_radar = go.Figure()
                    radar_colors = [NBA_BLUE, NBA_RED, "#007A33", "#FDB927"] # 蓝、红、绿、金
                    radar_metrics = ['基础产出评分', '效率加权评分', '进阶潜力评分', '场均得分', '场均篮板', '场均助攻']
                    for i, p in enumerate(pk_players):
                        p_row = final_df[final_df['球员'] == p].iloc[0]
                        r_vals = [p_row[m] / (final_df[m].max() + 0.1) for m in radar_metrics]
                        fig_radar.add_trace(go.Scatterpolar(
                            r=r_vals, theta=['量能', '效率', '潜力', '得分', '篮板', '助攻'], 
                            fill='toself', name=p, line_color=radar_colors[i % len(radar_colors)]
                        ))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True)
                    st.plotly_chart(fig_radar, use_container_width=True)

            with col_right:
                st.subheader("📈 历史评分曲线")
                trend_player = st.selectbox("选择球员", final_df['球员'].unique())
                if trend_player:
                    hist_data = df_raw[df_raw['球员'] == trend_player].sort_values('Fetch_Date')
                    hist_data = apply_ppi_models(hist_data)
                    fig_line = px.line(hist_data, x='Fetch_Date', y=strategy_col, markers=True, 
                                       title=f"{trend_player} 变动记录",
                                       color_discrete_sequence=[NBA_BLUE])
                    fig_line.update_layout(yaxis_tickformat='.2f')
                    st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")
st.caption("<div style='text-align: center; color: gray;'>© 2026 RookieFlip2x（乐翻新秀）评价系统 | 数字化量化看板</div>", unsafe_allow_html=True)
