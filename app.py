import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 数据源配置 - 添加本地文件支持
DATA_SOURCES = {
    "2022-23": {
        "type": "url",
        "path": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRfK4Q1d1pXZ4t7vq5Q3V0XwY8W7X8X8X8X8X8X8X8X8/pub?gid=0&single=true&output=csv"
    },
    "2023-24": {
        "type": "local",
        "path": "NBA_2023-24_rookies.csv"  # 使用您提供的本地文件
    },
    "2024-25": {
        "type": "url", 
        "path": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRfK4Q1d1pXZ4t7vq5Q3V0XwY8W7X8X8X8X8X8X8X8X8/pub?gid=0&single=true&output=csv"
    }
}

def fetch_and_clean_data(season):
    """获取并清洗数据"""
    try:
        data_source = DATA_SOURCES.get(season, DATA_SOURCES["2023-24"])
        
        if data_source["type"] == "local":
            # 读取本地CSV文件
            df = pd.read_csv(data_source["path"])
        else:
            # 尝试从URL读取（备用方案）
            st.warning(f"正在尝试在线获取{season}数据，如失败将使用2023-24本地数据")
            df = pd.read_csv(data_source["path"])
        
        # 简化的数据清洗逻辑
        df_clean = clean_nba_data(df)
        return df_clean
        
    except Exception as e:
        st.warning(f"数据获取失败: {str(e)}，使用备用数据源")
        # 尝试使用2023-24本地数据作为备用
        try:
            backup_df = pd.read_csv("NBA_2023-24_rookies.csv")
            return clean_nba_data(backup_df)
        except:
            return create_sample_data()

def clean_nba_data(df):
    """清洗NBA数据"""
    # 查找表头行
    header_idx = find_header_row(df)
    
    if header_idx > 0:
        df = pd.read_csv(DATA_SOURCES["2023-24"]["path"], header=header_idx)
    
    # 清理球员名字段
    if 'Player' in df.columns:
        df = df[df['Player'] != 'Player']
        df = df.dropna(subset=['Player'])
    
    # 重命名列（简化版）
    column_mapping = {
        'Totals': 'G',
        'Shooting': 'FG%', 
        'Per Game': 'MP',
        'PTS': 'PTS',
        'TRB': 'TRB',
        'AST': 'AST',
        'STL': 'STL', 
        'BLK': 'BLK',
        'FG%': 'FG%',
        '3P%': '3P%',
        'FT%': 'FT%'
    }
    
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    # 转换数值类型
    numeric_cols = ['G', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', '3P%', 'FT%']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df.reset_index(drop=True)

def find_header_row(df):
    """查找表头行"""
    for idx, row in df.iterrows():
        if 'Player' in str(row.values) and ('PTS' in str(row.values) or 'Totals' in str(row.values)):
            return idx
    return 0

def create_sample_data():
    """创建示例数据（备用方案）"""
    st.info("使用示例数据进行演示")
    return pd.DataFrame({
        'Player': ['Player A', 'Player B', 'Player C'],
        'PTS': [20.5, 18.3, 15.7],
        'TRB': [5.6, 7.2, 4.8],
        'AST': [4.3, 5.1, 3.9],
        'STL': [1.2, 0.9, 1.5],
        'BLK': [0.8, 1.3, 0.5],
        'FG%': [0.456, 0.432, 0.478],
        'G': [65, 72, 58],
        'MP': [32.5, 28.7, 25.3]
    })

# 其余函数保持不变（calculate_ppi, generate_signal, main等）
def calculate_ppi(df, ppi_version="基础版"):
    """计算球员表现指数(PPI) - 保持不变"""
    # ... 保持原代码不变

def generate_signal(df, signal_type="默认"):
    """生成投资信号 - 保持不变""" 
    # ... 保持原代码不变

def main():
    """主应用函数 - 添加错误处理"""
    st.set_page_config(
        page_title="RookieFlip2X: NBA 新秀量化投资系统",
        page_icon="🏀",
        layout="wide"
    )
    
    st.title("🏀 RookieFlip2X: NBA 新秀量化投资系统")
    st.markdown("### 基于高阶统计数据的球员价值评估")
    
    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 系统设置")
        season = st.selectbox("选择赛季", list(DATA_SOURCES.keys()), index=1)
        
        # 添加数据源说明
        st.info(f"当前数据源: {'本地文件' if DATA_SOURCES[season]['type'] == 'local' else '在线数据'}")
        
        st.subheader("🔍 数据过滤")
        min_games = st.slider("最小出场次数", 0, 100, 20)
        min_minutes = st.slider("最小场均时间(分钟)", 0.0, 40.0, 10.0, 0.5)
        
        st.subheader("📊 PPI模型设置")
        ppi_version = st.radio("选择PPI版本", ["基础版", "增强版", "进阶版"])
        
        st.subheader("📈 信号生成")
        signal_type = st.radio("信号生成方式", ["默认", "动态阈值"])
    
    try:
        # 获取并处理数据
        with st.spinner(f"正在获取{season}赛季数据..."):
            df = fetch_and_clean_data(season)
        
        if df.empty:
            st.error("无法获取有效数据，请检查数据文件。")
            return
        
        # 应用过滤器
        df_filtered = df.copy()
        if 'G' in df.columns:
            df_filtered = df_filtered[df_filtered['G'] >= min_games]
        if 'MP' in df.columns:
            df_filtered = df_filtered[df_filtered['MP'] >= min_minutes]
        
        if df_filtered.empty:
            st.warning("没有满足筛选条件的球员数据，请调整筛选条件。")
            return
        
        # 计算PPI和信号
        df_analyzed = calculate_ppi(df_filtered, ppi_version)
        df_signals = generate_signal(df_analyzed, signal_type)
        df_display = df_signals.sort_values('PPI', ascending=False).reset_index(drop=True)
        
        # 显示结果（保持原有可视化代码）
        # ... 其余显示代码保持不变
        
    except Exception as e:
        st.error(f"处理数据时发生错误: {str(e)}")
        st.info("建议：1. 检查CSV文件路径 2. 确认文件格式正确 3. 调整筛选条件")

if __name__ == "__main__":
    main()
