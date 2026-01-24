import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import warnings

# 忽略警告
warnings.filterwarnings('ignore')

# --- NBA 官方配色 ---
NBA_BLUE = "#17408B"
NBA_RED = "#C9082A"

# --- 1. 数据加载与处理 ---
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
            col_name = eng if eng in df.columns else eng.replace('.1', '')
            if col_name in df.columns:
                df[chn] = pd.to_numeric(df[col_name], errors='coerce').fillna(0)
        
        df['场均失误'] = (df['总失误'] / df.get('出场次数', 1)).fillna(0)
        return df
    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        return None

def apply_ppi_models(df):
    """RookieFlip2x 评价模型"""
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误']).round(2)
    df['效率加权评分'] = (((df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * (df['命中率'] + 0.5)) + (df['场均抢断'] + df['场均盖帽']) * 2.0).round(2)
    df['进阶潜力评分'] = ((((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - (df['场均失误'] * 1.5)).round(2)
    return df

# --- 2. 页面配置 ---
st.set_page_config(page_title="RookieFlip2x 乐翻新秀数据评价系统", layout="wide")

with st.sidebar:
    st.title("🚀 RookieFlip2x")
    st.caption("数字化新秀评价系统")
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
        st.divider()
        st.subheader("🛠️ 样本过滤")
        min_g = st.slider("最少出场次数", 1, 82, 5)
        min_mp = st.slider("最少场均分钟", 0, 48, 12)

# --- 3. 核心逻辑 ---
if df_raw is not None:
    st.title("🏆 RookieFlip2x 乐翻新秀数据评价系统")
    target_dt = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if not curr_df.empty:
        curr_df = apply_ppi_models(curr_df)
        
        # 趋势计算
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] < target_dt)]
        if not past_pool.empty:
            last_past = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past].copy())
            curr_df['变动趋势'] = (curr_df[strategy_col] - curr_df['球员'].map(past_data.set_index('球员')[strategy_col])).fillna(0).round(2)
        else:
            curr_df['变动趋势'] = 0.0

        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
        
        if not final_df.empty:
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index += 1
            
            # 模型信号
            avg_s = final_df[strategy_col].mean()
            def get_sig(r):
                if r['变动趋势'] > 1.5 and r[strategy_col] > avg_s: return "🔥 手感火热"
                if r[strategy_col] > avg_s * 1.3: return "👑 基石表现"
                if r['变动趋势'] < -1.5: return "❄️ 陷入低迷"
                return "🕒 待机状态"
            final_df['模型信号'] = final_df.apply(get_sig, axis=1)

            # --- 表格 ---
            st.subheader(f"📋 {sel_year} 战力榜 - {model_name}")
            st.dataframe(final_df[['球员', '模型信号', strategy_col, '变动趋势', '场均得分', '命中率']].style.format({strategy_col: "{:.2f}", "变动趋势": "{:+.2f}"}), use_container_width=True)

            # --- 点状分布 (修复版) ---
            st.divider()
            st.subheader(f"📍 实时评分扫描分布 ({sel_year}届)")
            
            # 预处理绘图数据防止 TypeError
            plot_df = final_df.copy()
            # 关键修复：确保 size 参数对应的列是正浮点数且无 NaN
            plot_df['点大小'] = pd.to_numeric(plot_df['场均得分'], errors='coerce').fillna(0).apply(lambda x: max(x, 2.0))
            
            fig_dot = px.strip(
                plot_df, x=strategy_col, orientation='h', color='模型信号',
                size='点大小', hover_name='球员',
                color_discrete_map={"🔥 手感火热": NBA_RED, "👑 基石表现": NBA_BLUE, "❄️ 陷入低迷": "#943126", "🕒 待机状态": "#7f8c8d"}
            )
            fig_dot.add_vline(x=avg_s, line_dash="dash", line_color="gray", annotation_text=f"均线:{avg_s:.2f}")
            fig_dot.update_layout(xaxis_title="评分", yaxis_title="", height=300)
            st.plotly_chart(fig_dot, use_container_width=True)

            # --- 届别分析 (底部) ---
            st.divider()
            st.subheader("📅 届别成色分析 (大年/小年)")
            latest_all = apply_ppi_models(df_raw.copy()).sort_values('Fetch_Date').groupby(['届别', '球员']).tail(1)
            year_avg = latest_all.groupby('届别')[strategy_col].mean().reset_index()
            
            c1, c2 = st.columns([1, 2])
            c1.dataframe(year_avg.sort_values(strategy_col, ascending=False), hide_index=True)
            fig_y = px.bar(year_avg, x='届别', y=strategy_col, color=strategy_col, color_continuous_scale=[NBA_RED, NBA_BLUE])
            st.plotly_chart(fig_y, use_container_width=True)

st.markdown("---")
st.caption("<div style='text-align: center; color: gray;'>© 2026 RookieFlip2x（乐翻新秀）数据评价系统</div>", unsafe_allow_html=True)
