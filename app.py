import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import warnings

# 忽略不必要的警告
warnings.filterwarnings('ignore')

# --- 1. 页面配置 & 资源定义 ---
# 确保使用的是带有透明背景的最新 Logo
LOGO_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/rookieflip2x_3.png"
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

st.set_page_config(
    page_title="RookieFlip2x 评价系统", 
    layout="wide",
    page_icon=LOGO_URL
)

# --- 定义配色方案 (适配深色模式) ---
# 使用稍微柔和一点的色调，提升深色背景下的舒适度
DARK_BLUE = "#3B82F6"  # 亮蓝色
DARK_RED = "#EF4444"   # 亮红色
TEXT_COLOR = "#E2E8F0" # 浅灰色文字

# --- 2. 数据加载与处理 ---
@st.cache_data(ttl=600)
def load_and_clean_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        if 'Player' in df.columns:
            df['球员'] = df['Player']
        
        col_map = {
            'PTS.1': '场均得分', 'TRB.1': '场均篮板', 'AST.1': '场均助攻', 
            'STL.1': '场均抢断', 'BLK.1': '场均盖帽', 'MP.1': '场均分钟', 
            'FG%': '命中率', 'G': '出场次数', 'TOV': '总失误', 'Rookie_Year': '原始年份'
        }
        
        for eng, chn in col_map.items():
            if eng in df.columns:
                df[chn] = pd.to_numeric(df[eng], errors='coerce')
        
        # 届别逻辑：2026年 -> 25届
        if '原始年份' in df.columns:
            df['届别'] = (df['原始年份'] - 1).astype(int)
        
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        
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

# --- 3. 侧边栏 ---
with st.sidebar:
    st.image(LOGO_URL, use_container_width=True)
    st.title("RookieFlip2x")
    st.caption("NBA 新锐量化数据评价看板")
    st.divider()
    
    df_raw = load_and_clean_data()
    
    if df_raw is not None:
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择新秀届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期", dates[0] if dates else None)
        
        model_name = st.radio("评价模型", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_name}评分"
        
        st.divider()
        min_g = st.slider("最少场次", 1, 82, 5)
        min_mp = st.slider("最少分钟", 0, 48, 12)

# --- 4. 主页面内容 ---
if df_raw is not None:
    st.title(f"🏆 {sel_year} 届新秀战力榜")
    
    target_dt = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if not curr_df.empty:
        curr_df = apply_ppi_models(curr_df)
        
        # 变动计算
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] < target_dt)]
        if not past_pool.empty:
            last_past = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past].copy())
            diff = curr_df[strategy_col] - curr_df['球员'].map(past_data.set_index('球员')[strategy_col]).fillna(curr_df[strategy_col])
            curr_df['变动趋势'] = diff.round(2)
        else:
            curr_df['变动趋势'] = 0.00

        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].sort_values(strategy_col, ascending=False).reset_index(drop=True)
        final_df.index += 1

        # --- 信号标记 (深色模式色彩优化) ---
        def get_model_signal(row):
            score, growth = row[strategy_col], row['变动趋势']
            avg = final_df[strategy_col].mean()
            if growth > 1.5 and score > avg: return "🔥 手感火热"
            if score > avg * 1.3: return "👑 基石表现"
            if growth < -1.5: return "❄️ 陷入低迷"
            return "🕒 待机状态"
        
        final_df['模型信号'] = final_df.apply(get_model_signal, axis=1)

        # --- 表格显示 ---
        def style_signal(val):
            # 在深色模式下使用带有透明度的背景色，更加高级
            colors = {
                "🔥 手感火热": "color: #FFA39E; background-color: rgba(255, 77, 79, 0.2); border: 1px solid #FF4D4F;",
                "👑 基石表现": "color: #91CAFF; background-color: rgba(24, 144, 255, 0.2); border: 1px solid #1890FF;",
                "❄️ 陷入低迷": "color: #D9D9D9; background-color: rgba(140, 140, 140, 0.2);",
                "🕒 待机状态": "color: #B7EB8F; background-color: rgba(82, 196, 26, 0.1);"
            }
            return colors.get(val, "")

        st.dataframe(
            final_df[['球员', '模型信号', strategy_col, '变动趋势', '场均得分', '命中率', '场均分钟', '出场次数']].style.format({
                strategy_col: "{:.2f}", "变动趋势": "{:+.2f}", "命中率": "{:.3f}", "场均得分": "{:.2f}", "场均分钟": "{:.2f}"
            }).applymap(style_signal, subset=['模型信号']),
            use_container_width=True
        )

        # --- 可视化适配深色模式 ---
        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("⚔️ 多维对标")
            pk = st.multiselect("PK 球员", final_df['球员'].unique(), default=final_df['球员'].head(2).tolist())
            if pk:
                fig_radar = go.Figure()
                metrics = ['基础产出评分', '效率加权评分', '进阶潜力评分', '场均得分', '场均篮板', '场均助攻']
                for p in pk:
                    p_row = final_df[final_df['球员'] == p].iloc[0]
                    r_vals = [p_row[m] / (final_df[m].max() + 0.1) for m in metrics]
                    fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=['量能','效率','潜力','得分','篮板','助攻'], fill='toself', name=p))
                
                # 关键：雷达图深色适配
                fig_radar.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1], gridcolor="#475569"), angularaxis=dict(gridcolor="#475569")),
                    margin=dict(t=20, b=20)
                )
                st.plotly_chart(fig_radar, use_container_width=True)

        with c2:
            st.subheader("📈 趋势追踪")
            t_player = st.selectbox("目标球员", final_df['球员'].unique())
            if t_player:
                h_data = apply_ppi_models(df_raw[df_raw['球员'] == t_player].sort_values('Fetch_Date'))
                fig_line = px.line(h_data, x='Fetch_Date', y=strategy_col, template="plotly_dark")
                fig_line.update_traces(line_color=DARK_BLUE, marker=dict(size=8, color=DARK_BLUE, line=dict(width=2, color="#FFF")))
                fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_line, use_container_width=True)

        st.divider()
        st.subheader("📍 评分分布洞察")
        fig_strip = px.strip(final_df, x=strategy_col, color='模型信号', template="plotly_dark",
                            color_discrete_map={"🔥 手感火热": DARK_RED, "👑 基石表现": DARK_BLUE, "🕒 待机状态": "#52C41A", "❄️ 陷入低迷": "#8C8C8C"})
        fig_strip.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_strip, use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #94A3B8; font-size: 0.8rem;'>© 2026 RookieFlip2x Data Intelligence System</div>", unsafe_allow_html=True)
