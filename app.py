import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据加载与清洗 ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        # 字段映射：确保找到球员名并锁定场均数据
        if 'Player' in df.columns: df['球员'] = df['Player']
        elif '球员' not in df.columns: df['球员'] = df.iloc[:, 1]

        col_map = {
            'PTS.1': '场均得分', 'TRB.1': '场均篮板', 'AST.1': '场均助攻', 
            'STL.1': '场均抢断', 'BLK.1': '场均盖帽', 'MP.1': '场均分钟', 
            'FG%': '命中率', 'G': '出场次数', 'TOV': '总失误', 'Rookie_Year': '届别'
        }
        for eng, chn in col_map.items():
            if eng in df.columns: df[chn] = pd.to_numeric(df[eng], errors='coerce')
            elif eng.replace('.1', '') in df.columns: df[chn] = pd.to_numeric(df[eng.replace('.1', '')], errors='coerce')
        
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        calc_cols = ['场均得分', '场均篮板', '场均助攻', '场均抢断', '场均盖帽', '场均分钟', '命中率', '场均失误']
        for col in calc_cols:
            if col in df.columns: df[col] = df[col].fillna(0)
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

def apply_ppi_models(df):
    """应用三套量化模型"""
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误'])
    df['效率加权评分'] = ((df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * (df['命中率'] + 0.5)) + (df['场均抢断'] + df['场均盖帽']) * 2.0
    df['进阶潜力评分'] = (((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - (df['场均失误'] * 1.5)
    return df

# --- 2. 页面配置 ---
st.set_page_config(page_title="NBA新秀量化投资系统", layout="wide")

df_raw = load_data()

if df_raw is not None:
    with st.sidebar:
        st.header("🎯 策略控制台")
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择届别", years)
        
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        sel_date = st.date_input("分析日期", dates[0] if dates else None)
        
        model_type = st.radio("量化评估模型", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_type}评分"
        
        st.divider()
        min_g = st.slider("最少出场次数 (G)", 1, 82, 5)
        min_mp = st.slider("最少场均分钟 (MP)", 0, 48, 12)

        with st.expander("📚 模型及信号说明"):
            st.markdown("""
            **模型用法：**
            - **基础产出**: 找数据全面的核心。
            - **效率加权**: 找不浪费球权的精英。
            - **进阶潜力**: 挖时间少产出高的潜力股。
            
            **信号说明：**
            - 🔥 **强烈推荐**: 高分+近期暴涨。
            - 📈 **状态上升**: 近期表现提升。
            - ⚠️ **表现下滑**: 数据大幅缩水。
            """)

    # --- 3. 计算与过滤 ---
    target_date = pd.to_datetime(sel_date)
    curr_df = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_date)].copy()
    
    if not curr_df.empty:
        curr_df = apply_ppi_models(curr_df)
        
        # 寻找 7 天前的数据算趋势
        past_date_limit = target_date - timedelta(days=7)
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] <= past_date_limit)]
        
        if not past_pool.empty:
            last_past = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past].copy())
            curr_df['7日涨幅'] = curr_df[strategy_col] - curr_df['球员'].map(past_data.set_index('球员')[strategy_col]).fillna(curr_df[strategy_col])
        else:
            curr_df['7日涨幅'] = 0.0

        final_df = curr_df[(curr_df['出场次数'] >= min_g) & (curr_df['场均分钟'] >= min_mp)].copy()
        
        if not final_df.empty:
            # 排序与排名
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index = final_df.index + 1

            def get_signal(row):
                if row['7日涨幅'] > 1.5 and row[strategy_col] > final_df[strategy_col].mean(): return "🔥 强烈推荐"
                if row['7日涨幅'] > 0.5: return "📈 状态上升"
                if row['7日涨幅'] < -1.5: return "⚠️ 表现下滑"
                return "🔎 持续观察"
            
            final_df['投资建议'] = final_df.apply(get_signal, axis=1)

            # --- 4. 界面呈现 ---
            st.title(f"🏀 {sel_year} 届新秀量化排行榜 ({model_type})")
            
            # 4.1 表格背景颜色渲染
            def style_signal(val):
                colors = {"🔥 强烈推荐": "background-color: #ff4b4b; color: white", 
                          "📈 状态上升": "background-color: #e8f8f5; color: #117a65",
                          "⚠️ 表现下滑": "background-color: #fdedec; color: #943126",
                          "🔎 持续观察": "background-color: #fef9e7; color: #9a7d0a"}
                return colors.get(val, "")

            st.subheader("📋 实时战力排行")
            display_cols = ['球员', '投资建议', strategy_col, '7日涨幅', '场均得分', '命中率', '场均分钟', '出场次数']
            st.dataframe(final_df[display_cols].style.applymap(style_signal, subset=['投资建议']), use_container_width=True)

            # 4.2 球员 PK 模块
            st.divider()
            st.subheader("⚔️ 球员多维 PK")
            pk_players = st.multiselect("选择球员进行对比", final_df['球员'].unique(), default=final_df['球员'].head(2).tolist())
            
            if pk_players:
                pk_df = final_df[final_df['球员'].isin(pk_players)]
                fig_radar = go.Figure()
                # 雷达图维度
                radar_metrics = ['基础产出评分', '效率加权评分', '进阶潜力评分', '场均得分', '场均篮板', '场均助攻']
                
                for p in pk_players:
                    p_row = pk_df[pk_df['球员'] == p].iloc[0]
                    # 归一化展示
                    r_values = [p_row[m] / (final_df[m].max() + 0.1) for m in radar_metrics]
                    fig_radar.add_trace(go.Scatterpolar(r=r_values, theta=['量能', '效率', '潜力', '得分', '篮板', '助攻'], fill='toself', name=p))
                
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), title="新秀多维战力雷达 (数值已归一化)")
                
                col_left, col_right = st.columns([1.5, 1])
                with col_left:
                    st.plotly_chart(fig_radar, use_container_width=True)
                with col_right:
                    st.write("**具体属性对标**")
                    st.table(pk_df[['球员', strategy_col, '场均得分', '命中率', '场均分钟']].set_index('球员'))

            # 4.3 象限散点图
            st.divider()
            st.subheader("💡 投资趋势挖掘")
            fig_scatter = px.scatter(final_df, x=strategy_col, y='7日涨幅', color='投资建议', size='场均得分', hover_name='球员', text='球员', labels={strategy_col: '量化评分', '7日涨幅': '7日变动'})
            st.plotly_chart(fig_scatter, use_container_width=True)
