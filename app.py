import streamlit as st
import pandas as pd
import numpy as np

def fetch_and_clean_data(season):
    """获取并清洗数据"""
    try:
        # 模拟数据 - 实际应用中替换为真实数据源
        data = {
            'Player': ['Player A', 'Player B', 'Player C'],
            'G': [65, 72, 58],
            'MP': [32.5, 28.7, 25.3],
            'PTS': [20.5, 18.3, 15.7],
            'TRB': [5.6, 7.2, 4.8],
            'AST': [4.3, 5.1, 3.9],
            'STL': [1.2, 0.9, 1.5],
            'BLK': [0.8, 1.3, 0.5],
            'FG%': [0.456, 0.432, 0.478]
        }
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return None

def calculate_ppi(df, ppi_version="基础版"):
    """计算球员表现指数(PPI)"""
    if df is None or df.empty:
        return None
    
    # 基础版PPI计算公式
    df['PPI'] = (df['PTS'] * 1.0 + df['TRB'] * 0.7 + 
                 df['AST'] * 0.7 + df['STL'] * 1.5 + 
                 df['BLK'] * 1.5) * df['FG%']
    return df

def generate_signal(df, signal_type="默认"):
    """生成投资信号"""
    if df is None or df.empty:
        return None
    
    if signal_type == "默认":
        df['Signal'] = np.where(df['PPI'] > df['PPI'].median(), '买入', '观望')
    else:
        df['Signal'] = np.where(df['PPI'] > df['PPI'].mean(), '买入', '观望')
    return df

def main():
    st.set_page_config(
        page_title="NBA新秀量化分析系统",
        page_icon="🏀",
        layout="wide"
    )
    
    st.title("🏀 NBA新秀量化分析系统")
    
    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 系统设置")
        season = st.selectbox("选择赛季", ["2022-23", "2023-24", "2024-25"], index=1)
        min_games = st.slider("最小出场次数", 0, 100, 20)
        min_minutes = st.slider("最小场均时间(分钟)", 0.0, 40.0, 10.0, 0.5)
        ppi_version = st.radio("选择PPI版本", ["基础版", "增强版"])
        signal_type = st.radio("信号生成方式", ["默认", "动态阈值"])
    
    # 获取数据
    df = fetch_and_clean_data(season)
    
    # 检查数据是否有效
    if df is None or df.empty:
        st.error("无法获取有效数据，请检查数据源。")
        return
    
    # 应用过滤器
    df_filtered = df[(df['G'] >= min_games) & (df['MP'] >= min_minutes)].copy()
    
    if df_filtered.empty:
        st.warning("没有满足筛选条件的球员数据，请调整筛选条件。")
        return
    
    # 计算PPI和信号
    df_analyzed = calculate_ppi(df_filtered, ppi_version)
    
    if df_analyzed is None:
        st.error("PPI计算失败，数据格式可能不正确。")
        return
    
    df_signals = generate_signal(df_analyzed, signal_type)
    
    if df_signals is None:
        st.error("信号生成失败，数据格式可能不正确。")
        return
    
    # 确保数据有效后再排序
    try:
        df_display = df_signals.sort_values('PPI', ascending=False).reset_index(drop=True)
        st.dataframe(df_display)
    except Exception as e:
        st.error(f"数据处理错误: {str(e)}")
        st.info("原始数据预览:")
        st.dataframe(df)

if __name__ == "__main__":
    main()
