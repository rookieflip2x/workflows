import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta
import warnings

# 忽略不必要的警告
warnings.filterwarnings('ignore')

# --- 1. 数据加载与中文清洗 ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=600)
def load_and_clean_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        # 1. 确保球员姓名列存在 (探测 Player 或 球员)
        if 'Player' in df.columns:
            df['球员'] = df['Player']
        elif '球员' not in df.columns:
            # 如果都没有，尝试取第二列（通常是姓名）
            df['球员'] = df.iloc[:, 1]

        # 2. 统一字段映射（核心逻辑：锁定场均数据 Per Game）
        # Basketball-Reference 的场均列通常带有 .1 后缀
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
        
        # 3. 基础计算：场均失误
        df['场均失误'] = (df['总失误'] / df['出场次数']).fillna(0)
        
        # 填充缺失值，防止计算 PPI 时出现空值
        calc_cols = ['场均得分', '场均篮板', '场均助攻', '场均抢断', '场均盖帽', '场均分钟', '命中率', '场均失误']
        for col in calc_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
                
        return df
    except Exception as e:
        st.error(f"❌ 数据源加载失败，请检查链接或文件格式: {e}")
        return None

def apply_ppi_models(df):
    """应用三套量化模型"""
    # 模型 1: 基础产出 (量能)
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + 
                       (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误'])
    
    # 模型 2: 效率加权 (质量)
    prod = df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)
    df['效率加权评分'] = (prod * (df['命中率'] + 0.5)) + (df['场均抢断'] + df['场均盖帽']) * 2.0
    
    # 模型 3: 进阶潜力 (潜力)
    df['进阶潜力评分'] = (((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - (df['场均失误'] * 1.5)
    return df

# --- 2. 页面配置 ---
st.set_page_config(page_title="NBA新秀量化投资系统", layout="wide")
st.title("🏀 NBA 新秀量化投资分析系统")

df_raw = load_and_clean_data()

if df_raw is not None:
    # --- 侧边栏 ---
    with st.sidebar:
        st.header("🎯 策略与筛选")
        
        # 届别选择
        years = sorted(df_raw['届别'].unique(), reverse=True)
        sel_year = st.selectbox("选择新秀届别", years)
        
        # 日期选择
        dates = sorted(df_raw[df_raw['届别'] == sel_year]['Fetch_Date'].unique(), reverse=True)
        if dates:
            sel_date = st.date_input("分析日期快照", dates[0])
        else:
            sel_date = st.date_input("分析日期快照")
            
        # 模型选择
        model_name = st.radio("量化评估模型", ["基础产出", "效率加权", "进阶潜力"])
        strategy_col = f"{model_name}评分"
        
        st.divider()
        st.subheader("🛠️ 样本过滤")
        min_g = st.slider("最少出场次数 (G)", 1, 82, 5)
        min_mp = st.slider("最少场均分钟 (MP)", 0, 48, 12)

    # --- 3. 数据计算与过滤 ---
    target_date = pd.to_datetime(sel_date)
    
    # A. 提取当前日期数据
    curr_data = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] == target_date)].copy()
    
    if curr_data.empty:
        st.warning(f"⚠️ 在 {sel_date} 这一天没有找到 {sel_year} 届新秀的数据，请尝试切换日期。")
    else:
        # 计算当前 PPI
        curr_data = apply_ppi_models(curr_data)
        
        # B. 趋势计算 (寻找 7 天前的数据)
        past_date_limit = target_date - timedelta(days=7)
        past_pool = df_raw[(df_raw['届别'] == sel_year) & (df_raw['Fetch_Date'] <= past_date_limit)]
        
        if not past_pool.empty:
            last_past_date = past_pool['Fetch_Date'].max()
            past_data = apply_ppi_models(past_pool[past_pool['Fetch_Date'] == last_past_date].copy())
            trend_map = past_data.set_index('球员')[strategy_col]
            curr_data['7日涨幅'] = curr_data['球员'].map(trend_map)
            curr_data['7日涨幅'] = curr_data[strategy_col] - curr_data['7日涨幅'].fillna(curr_data[strategy_col])
        else:
            curr_data['7日涨幅'] = 0.0

        # C. 执行样本筛选
        final_df = curr_data[(curr_data['出场次数'] >= min_g) & (curr_data['场均分钟'] >= min_mp)].copy()

        if final_df.empty:
            st.error("❌ 筛选后的结果为空，请调低“最少出场次数”或“场均分钟”。")
        else:
            # D. 重排序号（按分数从高到低）
            final_df = final_df.sort_values(strategy_col, ascending=False).reset_index(drop=True)
            final_df.index = final_df.index + 1 # 排名从1开始
            final_df.index.name = '排名'

            # E. 投资建议算法
            def get_investment_signal(row):
                score = row[strategy_col]
                growth = row['7日涨幅']
                if growth > 1.5 and score > final_df[strategy_col].mean(): return "🔥 强烈推荐"
                if growth > 0.5: return "📈 状态上升"
                if growth < -1.5: return "⚠️ 表现下滑"
                return "🔎 持续观察"
            
            final_df['投资建议'] = final_df.apply(get_investment_signal, axis=1)

            # --- 4. 界面呈现 ---
            # 顶部指标栏
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("战力榜首", final_df.iloc[0]['球员'], f"{final_df.iloc[0][strategy_col]:.2f}")
            with c2:
                top_gainer = final_df.sort_values('7日涨幅', ascending=False).iloc[0]
                st.metric("近期爆发王", top_gainer['球员'], f"{top_gainer['7日涨幅']:+.2f}")
            with c3:
                st.metric("有效样本数", len(final_df))

            # 数据大表
            st.subheader(f"📊 {sel_year} 届新秀量化排行榜 ({model_name}模型)")
            # 明确指定列顺序，确保球员姓名在第一列
            display_cols = ['球员', '投资建议', strategy_col, '7日涨幅', '场均得分', '命中率', '场均分钟', '出场次数']
            
            st.dataframe(
                final_df[display_cols],
                use_container_width=True,
                column_config={
                    strategy_col: st.column_config.NumberColumn("模型评分", format="%.2f"),
                    "7日涨幅": st.column_config.NumberColumn("7日趋势", format="%+.2f"),
                    "命中率": st.column_config.NumberColumn("FG%", format="%.3f"),
                    "投资建议": st.column_config.TextColumn("信号状态")
                }
            )

            # 可视化图表
            st.divider()
            st.subheader("💡 投资机会挖掘象限 (横轴评分 / 纵轴增长)")
            fig = px.scatter(
                final_df, x=strategy_col, y='7日涨幅', color='投资建议',
                size='场均得分', hover_name='球员', text='球员',
                color_discrete_map={
                    "🔥 强烈推荐": "#FF4B4B", 
                    "📈 状态上升": "#00CC96", 
                    "⚠️ 表现下滑": "#636EFA", 
                    "🔎 持续观察": "#FFAA00"
                },
                labels={strategy_col: '当前量化评分', '7日涨幅': '近7日趋势变动'}
            )
            # 辅助线
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)

# --- 5. 页脚说明 ---
st.caption("数据来源：Basketball-Reference | 模型：自定义 PPI 量化策略 | 自动去重及清洗已启用")
