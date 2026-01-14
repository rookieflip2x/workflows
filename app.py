import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# --- 核心修复部分：更新为 GitHub Raw 链接 ---
# 请将下方的 URL 替换为您在 GitHub 上的实际 Raw 链接
CSV_LINKS = {
    "2023-24": "https://raw.githubusercontent.com/rookieflip2x/workflows/main/NBA_2023-24_rookies.csv",
    "2024-25": "https://raw.githubusercontent.com/rookieflip2x/workflows/main/NBA_2024-25_rookies%20.csv",
    "2025-26": "https://raw.githubusercontent.com/rookieflip2x/workflows/main/NBA_2025-26_rookies%20.csv"
}

def fetch_and_clean_data(season):
    """获取并清洗数据"""
    try:
        url = CSV_LINKS.get(season)
        if not url or "yourusername" in url: # 简单的安全检查
            st.error(f"请在代码中配置 {season} 的真实 GitHub URL")
            return pd.DataFrame()
            
        # 从 GitHub 读取数据
        df_raw = pd.read_csv(url)
        
        # 自动定位表头（逻辑优化：如果第一行就是表头则不跳过）
        header_row = 0
        for idx, row in df_raw.head(10).iterrows(): # 只检查前10行
            if 'Player' in str(row.values) or 'PTS' in str(row.values):
                header_row = idx
                break
        
        # 重新读取或调整 DataFrame
        if header_row > 0:
            df = pd.read_csv(url, header=header_row)
        else:
            df = df_raw
        
        # 列名映射 (保持原逻辑不变)
        column_mapping = {
            'Unnamed: 0': 'Rk', 'Unnamed: 1': 'Player', 'Unnamed: 6': 'MP_Total',
            'Unnamed: 14': 'TRB_Total', 'Unnamed: 15': 'AST_Total',
            'Unnamed: 16': 'STL_Total', 'Unnamed: 17': 'BLK_Total',
            'Unnamed: 20': 'PTS_Total', 'Shooting': 'FG%', 'Unnamed: 22': '3P%',
            'Unnamed: 23': 'FT%', 'Per Game': 'MP', 'Unnamed: 25': 'PTS',
            'Unnamed: 26': 'TRB', 'Unnamed: 27': 'AST', 'Unnamed: 28': 'STL',
            'Unnamed: 29': 'BLK'
        }
        
        df = df.rename(columns=column_mapping)
        # 过滤掉重复的表头行
        if 'Player' in df.columns:
            df = df[df['Player'] != 'Player'].reset_index(drop=True)
        
        # 强制转换为数值
        numeric_cols = ['G', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', '3P%', 'FT%', 'TOV', 'FTA', 'FGA']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算 TS%
        if all(col in df.columns for col in ['PTS_Total', 'FGA', 'FTA']):
            df['TS%'] = df['PTS_Total'] / (2 * (df['FGA'] + 0.44 * df['FTA']))
            
        return df
        
    except Exception as e:
        st.error(f"无法从 GitHub 获取数据: {str(e)}")
        return pd.DataFrame()

# --- 后续计算函数 (保持原样) ---
def calculate_ppi(df, ppi_version="基础版"):
    df = df.copy()
    if ppi_version == "基础版":
        df['PPI'] = df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5
        df['PPI_Description'] = "基础版PPI = 得分×1.0 + 篮板×1.2 + 助攻×1.5"
    elif ppi_version == "增强版":
        base_score = df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5
        defense_score = df['STL'].fillna(0) * 1.5 + df['BLK'].fillna(0) * 2.0
        efficiency_score = (df['FG%'].fillna(0) * 5.0 + df['3P%'].fillna(0) * 3.0 + df['FT%'].fillna(0) * 2.0)
        df['PPI'] = base_score * 0.6 + defense_score * 0.25 + efficiency_score * 0.15
        df['PPI_Description'] = "增强版PPI = (基础三要素×0.6) + (防守×0.25) + (效率×0.15)"
        df['基础分'], df['防守分'], df['效率分'] = base_score, defense_score, efficiency_score
    elif ppi_version == "进阶版":
        production_score = (df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5 + df['STL'].fillna(0) * 2.0 + df['BLK'].fillna(0) * 2.5)
        efficiency_score = (df.get('FG%',0) * 6.0 + df.get('3P%',0) * 4.0 + df.get('FT%',0) * 3.0)
        mp_factor = np.minimum(df['MP'] / 30.0, 1.5) if 'MP' in df.columns else 1
        turnover_penalty = df['TOV'].fillna(0) * 0.5 if 'TOV' in df.columns else 0
        df['PPI'] = (production_score * mp_factor - turnover_penalty) * 0.7 + efficiency_score * 0.3
        df['PPI_Description'] = "进阶版PPI = (产出×0.7) + (效率×0.3) [含时间调整和失误惩罚]"
    return df

def generate_signal(df, signal_type="默认"):
    df = df.copy()
    if signal_type == "默认":
        conditions = [df['PPI'] >= 25, df['PPI'] >= 18, df['PPI'] >= 12]
        choices = ['🚀 强力买入', '📈 买入', '📊 积累']
        df['Signal'] = np.select(conditions, choices, default='⚖️ 持有')
        df['Signal_Explanation'] = "基于PPI固定阈值"
    elif signal_type == "动态阈值":
        p75, p50 = df['PPI'].quantile(0.75), df['PPI'].quantile(0.50)
        conditions = [df['PPI'] >= p75 * 1.2, df['PPI'] >= p75, df['PPI'] >= p50]
        choices = ['🚀 强力买入(超优)', '📈 买入(前25%)', '📊 积累(前50%)']
        df['Signal'] = np.select(conditions, choices, default='⚖️ 持有')
        df['Signal_Explanation'] = f"动态阈值(P75={p75:.1f})"
    return df

# --- UI 逻辑 (保持原样) ---
def main():
    st.set_page_config(page_title="RookieFlip2X", page_icon="🏀", layout="wide")
    st.title("🏀 RookieFlip2X: NBA 新秀量化投资系统")
    st.markdown("---")
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 系统设置")
        season = st.selectbox("选择赛季", list(CSV_LINKS.keys()), index=2)
        min_games = st.slider("最小出场次数", 0, 82, 15)
        min_minutes = st.slider("最小场均时间", 0.0, 40.0, 8.0)
        ppi_version = st.radio("PPI模型", ["基础版", "增强版", "进阶版"])
        signal_type = st.radio("信号策略", ["默认", "动态阈值"])

    # 获取并分析数据
    df = fetch_and_clean_data(season)
    
    if not df.empty:
        # 过滤数据
        df_filtered = df[(df['G'] >= min_games) & (df['MP'] >= min_minutes)]
        
        if df_filtered.empty:
            st.warning("⚠️ 没有符合当前过滤条件的球员。")
        else:
            df_analyzed = calculate_ppi(df_filtered, ppi_version)
            df_signals = generate_signal(df_analyzed, signal_type)
            df_display = df_signals.sort_values('PPI', ascending=False).reset_index(drop=True)
            
            # 数据概览组件
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🏆 标王", df_display.iloc[0]['Player'], f"PPI: {df_display.iloc[0]['PPI']:.1f}")
            c2.metric("👥 样本数", len(df_display))
            c3.metric("📈 均值", f"{df_display['PPI'].mean():.1f}")
            c4.metric("💡 建议买入", len(df_display[df_display['Signal'].str.contains('买入')]))
            
            # 表格展示
            st.subheader("📊 实时评估清单")
            st.dataframe(df_display[['Player', 'PPI', 'Signal', 'PTS', 'TRB', 'AST', 'MP', 'G', 'FG%']], use_container_width=True)
            
            # 可视化
            st.subheader("📈 数据可视化")
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(px.histogram(df_display, x='PPI', title="PPI 分布"), use_container_width=True)
            with col2:
                st.plotly_chart(px.scatter(df_display, x='PTS', y='PPI', color='Signal', hover_name='Player', title="得分与PPI关联"), use_container_width=True)
            
            # 下载功能
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button("📥 下载分析报告 (CSV)", data=csv, file_name=f"RookieFlip_{season}.csv", mime="text/csv")
    else:
        st.info("💡 请配置 GitHub URL 后开始分析。")

if __name__ == "__main__":
    main()
