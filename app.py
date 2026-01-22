import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import warnings

# 忽略不必要的警告
warnings.filterwarnings('ignore')

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
    """应用量化评估逻辑，结果严格保留两位小数"""
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + 
                       (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误']).round(2)
    df['效率加权评分'] = (((df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * (df['命中率'] + 0.5)) + \
                       (df['场均抢断'] + df['场均盖帽']) * 2.0).round(2)
    df['进阶潜力评分'] = ((((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - \
                       (df['场均失误'] * 1.5)).round(2)
    return df

# --- 2. 页面设置 ---
st.set_page_config(page_title="NBA新秀量化看板", layout="wide")

# --- 3. 侧边栏与免责声明 ---
with st.sidebar:
    st.warning("⚠️ **免责声明**")
    st.caption("本工具仅供数据分析参考，不构成任何投资建议。数据取自公开统计。")
    st.divider()
    
    df_raw = load_and_clean_data()
    
    if df_raw is not None:
        st.header("🎯 策略控制")
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期", dates[0] if dates else None)
        
        model_name = st.radio("模型", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_name}评分"
        
        st.divider()
        min_g = st.slider("最少出场 (G)", 1, 82, 5)
        min_mp = st.slider("最少分钟 (MP)", 0, 48, 12)
        
        # 针对移动端的精简开关
        is_mobile = st.checkbox("移动端精简模式", value=True)

# --- 4. 核心逻辑处理 ---
if df_raw is not None:
    target_dt = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if not curr_df.empty:
        curr_df = apply_ppi_models(curr_df)
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] < target_dt)]
        if not past_pool.empty:
            last_past = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past].copy())
            curr_df['7日涨幅'] = (curr_df[strategy_col] - curr_df['球员'].map(past_data.set_index('球员')[strategy_col])).fillna(0.00).round(2)
        else:
            curr_df['7日涨幅'] = 0.00

        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
        
        if not final_df.empty:
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index = final_df.index + 1
            
            def get_signal(row):
                score, growth = row[strategy_col], row['7日涨幅']
                if growth > 1.5 and score > final_df[strategy_col].mean(): return "🔥 数据爆发"
                if growth > 0.5: return "📈 趋势上扬"
                if growth < -1.5: return "📉 动态回撤"
                return "🔎 数据持平"
            final_df['模型信号'] = final_df.apply(get_signal, axis=1)

            # --- 5. UI 呈现 ---
            st.title(f"📊 {sel_year} 新秀量化看板")
            
            # 表格颜色逻辑
            def color_cell(val):
                colors = {"🔥 数据爆发": "background-color: #ff4b4b; color: white;", 
                          "📈 趋势上扬": "background-color: #e8f8f5; color: #117a65;",
                          "📉 动态回撤": "background-color: #fdedec; color: #943126;",
                          "🔎 数据持平": "background-color: #fcf3cf; color: #9a7d0a;"}
                return colors.get(val, "")

            # 根据精简模式选择列
            if is_mobile:
                display_cols = ['球员', '模型信号', strategy_col, '7日涨幅']
            else:
                display_cols = ['球员', '模型信号', strategy_col, '7日涨幅', '场均得分', '命中率', '场均分钟', '出场次数']

            st.dataframe(
                final_df[display_cols].style.format({strategy_col: "{:.2f}", "7日涨幅": "{:+.2f}"}).applymap(color_cell, subset=['模型信号']),
                use_container_width=True
            )

            # --- 6. 交互对比 (移动端自动上下排列) ---
            st.divider()
            col_l, col_r = st.columns([1, 1])
            
            with col_l:
                st.subheader("⚔️ 多维对标")
                pk_players = st.multiselect("选择球员", final_df['球员'].unique(), default=final_df['球员'].head(2).tolist())
                if pk_players:
                    fig_radar = go.Figure()
                    metrics = ['基础产出评分', '效率加权评分', '进阶潜力评分', '场均得分', '场均篮板', '场均助攻']
                    for p in pk_players:
                        p_row = final_df[final_df['球员'] == p].iloc[0]
                        r_vals = [p_row[m] / (final_df[m].max() + 0.1) for m in metrics]
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=['量能','效率','潜力','得分','篮板','助攻'], fill='toself', name=p))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1])), margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig_radar, use_container_width=True)

            with col_r:
                st.subheader("📈 成长走势")
                trend_p = st.selectbox("选择球员", final_df['球员'].unique())
                if trend_p:
                    hist_data = apply_ppi_models(df_raw[df_raw['球员'] == trend_p].copy()).sort_values('Fetch_Date')
                    fig_line = px.line(hist_data, x='Fetch_Date', y=strategy_col, markers=True)
                    fig_line.update_layout(margin=dict(l=20, r=20, t=20, b=20), yaxis_tickformat='.2f')
                    st.plotly_chart(fig_line, use_container_width=True)

# 页脚
st.markdown("---")
st.caption("<center>© 2026 NBA Quant | 数据已保留两位小数</center>", unsafe_allow_html=True)
