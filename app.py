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
    """应用量化评估逻辑"""
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + 
                       (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误']).round(2)
    df['效率加权评分'] = (((df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * (df['命中率'] + 0.5)) + \
                       (df['场均抢断'] + df['场均盖帽']) * 2.0).round(2)
    df['进阶潜力评分'] = ((((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - \
                       (df['场均失误'] * 1.5)).round(2)
    return df

# --- 2. 页面设置 ---
st.set_page_config(page_title="NBA新秀量化数据看板", layout="wide")

# --- 侧边栏 ---
with st.sidebar:
    st.title("📈 NBA Quant")
    st.divider()
    
    df_raw = load_and_clean_data()
    
    if df_raw is not None:
        st.header("🎯 策略控制台")
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期快照", dates[0] if dates else None)
        
        model_name = st.radio("量化评估模型", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_name}评分"

        # --- 模型对比说明 (简化版，移除公式和方案字样) ---
        with st.expander("📝 模型选择指南", expanded=True):
            st.markdown("""
            | 模型名称 | 核心优势 | 适用场景 |
            | :--- | :--- | :--- |
            | **基础产出** | 容错率高，真实产出 | 评估最佳新秀归属 |
            | **效率加权** | 剥离刷分水分 | 寻找球星胚子 |
            | **进阶潜力** | 发现被埋没珍珠 | 挖掘高效替补 |
            """)
            st.divider()
            if model_name == "基础产出":
                st.info("**当前聚焦：赛场影响力**")
                st.write("侧重全面性，综合得分、篮板、助攻及防守表现。")
            elif model_name == "效率加权":
                st.info("**当前聚焦：进攻含金量**")
                st.write("侧重终结质量，奖励那些不浪费球权的高效进攻者。")
            else:
                st.info("**当前聚焦：未来天花板**")
                st.write("折算每36分钟标准产出，识别单位时间内表现抢眼的潜力股。")
        
        st.divider()
        st.subheader("🛠️ 样本过滤")
        min_g = st.slider("最少出场次数 (G)", 1, 82, 5)
        min_mp = st.slider("最少场均分钟 (MP)", 0, 48, 12)

        with st.expander("📌 球员状态标签说明"):
            st.caption("**🔥 手感火热**: 表现优异且近期大幅上涨")
            st.caption("**🆙 状态复苏**: 评分近期稳步上升")
            st.caption("**👑 基石表现**: 长期维持极高水准且稳定")
            st.caption("**❄️ 陷入低迷**: 评分近期出现明显下滑")
            st.caption("**🕒 待机状态**: 表现持平，波动较小")

# --- 3. 核心计算与显示逻辑 ---
if df_raw is not None:
    target_dt = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_dt)].copy()
    
    if curr_df.empty:
        st.info(f"📅 暂无日期 {sel_date} 的数据，请尝试切换日期。")
    else:
        curr_df = apply_ppi_models(curr_df)
        
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] < target_dt)]
        if not past_pool.empty:
            last_past = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past].copy())
            diff = curr_df[strategy_col] - curr_df['球员'].map(past_data.set_index('球员')[strategy_col]).fillna(curr_df[strategy_col])
            curr_df['7日涨幅'] = diff.round(2)
        else:
            curr_df['7日涨幅'] = 0.00

        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
        
        if final_df.empty:
            st.error("❌ 筛选条件过严，当前无符合条件的球员。")
        else:
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index = final_df.index + 1
            final_df.index.name = "排名"

            def get_model_signal(row):
                score, growth = row[strategy_col], row['7日涨幅']
                avg_score = final_df[strategy_col].mean()
                if growth > 1.5 and score > avg_score: return "🔥 手感火热"
                if growth > 0.5: return "🆙 状态复苏"
                if growth < -1.5: return "❄️ 陷入低迷"
                if score > avg_score * 1.3: return "👑 基石表现"
                return "🕒 待机状态"
            
            final_df['模型信号'] = final_df.apply(get_model_signal, axis=1)

            st.title(f"📊 {sel_year} 届新秀量化看板 - {model_name}模式")

            def color_cell(val):
                colors = {
                    "🔥 手感火热": "background-color: #ff4b4b; color: white; font-weight: bold;",
                    "🆙 状态复苏": "background-color: #e8f8f5; color: #117a65;",
                    "❄️ 陷入低迷": "background-color: #fdedec; color: #943126;",
                    "👑 基石表现": "background-color: #ebf5fb; color: #21618c; border: 1px solid #2e86c1;",
                    "🕒 待机状态": "background-color: #f8f9f9; color: #7f8c8d;"
                }
                return colors.get(val, "")

            st.subheader("📋 实时战力排行")
            display_cols = ['球员', '模型信号', strategy_col, '7日涨幅', '场均得分', '命中率', '场均分钟', '出场次数']
            
            st.dataframe(
                final_df[display_cols].style.format({
                    strategy_col: "{:.2f}",
                    "7日涨幅": "{:+.2f}",
                    "命中率": "{:.3f}"
                }).applymap(color_cell, subset=['模型信号']),
                use_container_width=True
            )

            st.divider()
            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("⚔️ 多维数据对标")
                pk_players = st.multiselect("选择球员 PK", final_df['球员'].unique(), default=final_df['球员'].head(2).tolist())
                if pk_players:
                    fig_radar = go.Figure()
                    radar_metrics = ['基础产出评分', '效率加权评分', '进阶潜力评分', '场均得分', '场均篮板', '场均助攻']
                    for p in pk_players:
                        p_row = final_df[final_df['球员'] == p].iloc[0]
                        r_vals = [p_row[m] / (final_df[m].max() + 0.1) for m in radar_metrics]
                        fig_radar.add_trace(go.Scatterpolar(r=r_vals, theta=['量能', '效率', '潜力', '得分', '篮板', '助攻'], fill='toself', name=p))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True)
                    st.plotly_chart(fig_radar, use_container_width=True)

            with col_right:
                st.subheader("📈 评分历史走势")
                trend_player = st.selectbox("选择球员", final_df['球员'].unique())
                if trend_player:
                    hist_data = df_raw[df_raw['球员'] == trend_player].sort_values('Fetch_Date')
                    hist_data = apply_ppi_models(hist_data)
                    fig_line = px.line(hist_data, x='Fetch_Date', y=strategy_col, markers=True, title=f"{trend_player} 评分变动")
                    fig_line.update_layout(yaxis_tickformat='.2f')
                    st.plotly_chart(fig_line, use_container_width=True)

            st.divider()
            st.subheader("💡 增长趋势分布图")
            fig_scatter = px.scatter(
                final_df, x=strategy_col, y='7日涨幅', color='模型信号',
                size='场均得分', hover_name='球员', text='球员',
                labels={strategy_col: '量化评分', '7日涨幅': '近期波动'}
            )
            fig_scatter.update_traces(textposition='top center')
            st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")
st.caption("<div style='text-align: center; color: gray;'>© 2026 NBA 新秀自动化量化看板 | 数据驱动分析</div>", unsafe_allow_html=True)
