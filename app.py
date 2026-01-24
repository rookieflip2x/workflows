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

# --- 资源链接 ---
LOGO_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/rookieflip2x.png"
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

# --- 1. 页面配置 (包含浏览器图标) ---
st.set_page_config(
    page_title="RookieFlip2x 乐翻新秀数据评价系统", 
    layout="wide",
    page_icon=LOGO_URL  # 将你的 Logo 设置为浏览器标签页图标
)

# --- 2. 数据加载与处理逻辑 ---
@st.cache_data(ttl=600)
def load_and_clean_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        # 统一球员列名
        if 'Player' in df.columns:
            df['球员'] = df['Player']
        elif '球员' not in df.columns:
            df['球员'] = df.iloc[:, 1]

        # 核心字段映射
        col_map = {
            'PTS.1': '场均得分', 'TRB.1': '场均篮板', 'AST.1': '场均助攻', 
            'STL.1': '场均抢断', 'BLK.1': '场均盖帽', 'MP.1': '场均分钟', 
            'FG%': '命中率', 'G': '出场次数', 'TOV': '总失误', 'Rookie_Year': '原始年份'
        }
        
        for eng, chn in col_map.items():
            if eng in df.columns:
                df[chn] = pd.to_numeric(df[eng], errors='coerce')
            elif eng.replace('.1', '') in df.columns:
                df[chn] = pd.to_numeric(df[eng.replace('.1', '')], errors='coerce')
        
        # --- 届别减 1 逻辑：2026年数据 -> 25届 ---
        if '原始年份' in df.columns:
            df['届别'] = (df['原始年份'] - 1).astype(int)
        
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        
        # 基础数据保留两位小数
        calc_cols = ['场均得分', '场均篮板', '场均助攻', '场均抢断', '场均盖帽', '场均分钟', '命中率', '场均失误']
        for col in calc_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0).round(2)
                
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

# --- 3. 侧边栏布局 (包含 Logo 展示) ---
with st.sidebar:
    # 展示 Logo
    st.image(LOGO_URL, use_container_width=True)
    st.title("🚀 RookieFlip2x")
    st.caption("数字化新秀量化评价系统")
    st.divider()
    
    df_raw = load_and_clean_data()
    
    if df_raw is not None:
        st.header("🎯 策略控制台")
        # 届别选择
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择新秀届别 (Draft Class)", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期快照", dates[0] if dates else None)
        
        model_name = st.radio("选择评价维度", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_name}评分"

        with st.expander("📝 评价维度指南"):
            st.markdown("""
            | 维度名称 | 适用场景 |
            | :--- | :--- |
            | **基础产出** | 评估 ROY 归属 |
            | **效率加权** | 挖掘高效核心 |
            | **进阶潜力** | 识别板凳奇兵 |
            """)
        
        st.divider()
        st.subheader("🛠️ 样本过滤")
        min_g = st.slider("最少出场次数", 1, 82, 5)
        min_mp = st.slider("最少场均分钟", 0, 48, 12)

# --- 4. 页面主体逻辑 ---
if df_raw is not None:
    st.title("🏆 RookieFlip2x 乐翻新秀评价看板")
    
    target_dt = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if curr_df.empty:
        st.info(f"📅 暂无日期 {sel_date} 的数据。")
    else:
        curr_df = apply_ppi_models(curr_df)
        
        # 趋势计算
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
            st.error("❌ 筛选后无符合条件的球员。")
        else:
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index += 1

            def get_model_signal(row):
                score, growth = row[strategy_col], row['变动趋势']
                avg_score = final_df[strategy_col].mean()
                if growth > 1.5 and score > avg_score: return "🔥 手感火热"
                if growth > 0.5: return "🆙 状态复苏"
                if growth < -1.5: return "❄️ 陷入低迷"
                if score > avg_score * 1.3: return "👑 基石表现"
                return "🕒 待机状态"
            
            final_df['模型信号'] = final_df.apply(get_model_signal, axis=1)

            # --- 战力榜 ---
            st.subheader(f"📋 {sel_year} 届实时战力榜 - {model_name}")

            def color_cell(val):
                colors = {
                    "🔥 手感火热": f"background-color: {NBA_RED}; color: white;",
                    "👑 基石表现": f"background-color: {NBA_BLUE}; color: white;",
                    "🆙 状态复苏": "background-color: #e8f8f5; color: #117a65;",
                    "❄️ 陷入低迷": "background-color: #fdedec; color: #943126;",
                    "🕒 待机状态": "background-color: #f8f9f9; color: #7f8c8d;"
                }
                return colors.get(val, "")

            display_cols = ['球员', '模型信号', strategy_col, '变动趋势', '场均得分', '命中率', '场均分钟', '出场次数']
            st.dataframe(
                final_df[display_cols].style.format({
                    strategy_col: "{:.2f}",
                    "变动趋势": "{:+.2f}",
                    "命中率": "{:.3f}",
                    "场均得分": "{:.2f}", # 保留两位小数
                    "场均分钟": "{:.2f}"  # 保留两位小数
                }).applymap(color_cell, subset=['模型信号']),
                use_container_width=True
            )

            # --- 可视化 ---
            st.divider()
            col_radar, col_line = st.columns(2)
            with col_radar:
                st.subheader("⚔️ 球员多维 PK")
                pk_players = st.multiselect("选择球员进行对比", final_df['球员'].unique(), default=final_df['球员'].head(2).tolist())
                if pk_players:
                    fig_radar = go.Figure()
                    radar_metrics = ['基础产出评分', '效率加权评分', '进阶潜力评分', '场均得分', '场均篮板', '场均助攻']
                    for p in pk_players:
                        p_row = final_df[final_df['球员'] == p].iloc[0]
                        r_vals = [p_row[m] / (final_df[m].max() + 0.1) for m in radar_metrics]
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=['量能','效率','潜力','得分','篮板','助攻'], fill='toself', name=p))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True)
                    st.plotly_chart(fig_radar, use_container_width=True)

            with col_line:
                st.subheader("📈 评分历史趋势")
                trend_player = st.selectbox("选择追踪球员", final_df['球员'].unique())
                if trend_player:
                    hist_data = apply_ppi_models(df_raw[df_raw['球员'] == trend_player].sort_values('Fetch_Date'))
                    fig_line = px.line(hist_data, x='Fetch_Date', y=strategy_col, markers=True, color_discrete_sequence=[NBA_BLUE])
                    fig_line.update_layout(yaxis_tickformat='.2f')
                    st.plotly_chart(fig_line, use_container_width=True)

            st.divider()
            st.subheader(f"📍 实时评分分布 ({sel_year} 届)")
            fig_dot = px.strip(final_df, x=strategy_col, orientation='h', color='模型信号', hover_name='球员',
                              color_discrete_map={"🔥 手感火热": NBA_RED, "👑 基石表现": NBA_BLUE, "🆙 状态复苏": "#117a65", "❄️ 陷入低迷": "#943126", "🕒 待机状态": "#7f8c8d"})
            fig_dot.update_traces(marker=dict(size=12, opacity=0.7, line=dict(width=1, color='White')))
            st.plotly_chart(fig_dot, use_container_width=True)

st.markdown("---")
st.caption("<div style='text-align: center; color: gray;'>© 2026 RookieFlip2x（乐翻新秀）数据评价系统</div>", unsafe_allow_html=True)
