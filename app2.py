import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 页面配置
st.set_page_config(
    page_title="RookieFlip2X: NBA 新秀量化投资系统",
    page_icon="🏀",
    layout="wide"
)

# CSV数据链接
CSV_LINKS = {
    "2022-23": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRfK4Q1d1pXZ4t7vq5Q3V0XwY8W7X8X8X8X8X8X8X8X8X8/pub?gid=0&single=true&output=csv",
    "2023-24": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRfK4Q1d1pXZ4t7vq5Q3V0XwY8W7X8X8X8X8X8X8X8X8/pub?gid=0&single=true&output=csv",
    "2024-25": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRfK4Q1d1pXZ4t7vq5Q3V0XwY8W7X8X8X8X8X8X8X8X8/pub?gid=0&single=true&output=csv"
}

@st.cache_data(ttl=600)
def fetch_and_clean_data(season):
    """获取并清洗数据，处理多级表头"""
    try:
        # 获取数据
        url = CSV_LINKS.get(season, CSV_LINKS["2023-24"])
        df = pd.read_csv(url)
        
        # 查找包含'Player'的行作为表头
        header_row = 0
        for idx, row in df.iterrows():
            if 'Player' in str(row.values) and 'PTS' in str(row.values):
                header_row = idx
                break
        
        # 读取正确的表头
        df = pd.read_csv(url, header=header_row)
        
        # 手动构建列名映射
        column_mapping = {
            'Unnamed: 0': 'Rk',
            'Unnamed: 1': 'Player',
            'Unnamed: 2': 'Debut',
            'Unnamed: 3': 'Age',
            'Unnamed: 4': 'Yrs',
            'Totals': 'G',
            'Unnamed: 6': 'MP_Total',
            'Unnamed: 7': 'FG',
            'Unnamed: 8': 'FGA',
            'Unnamed: 9': '3P',
            'Unnamed: 10': '3PA',
            'Unnamed: 11': 'FT',
            'Unnamed: 12': 'FTA',
            'Unnamed: 13': 'ORB',
            'Unnamed: 14': 'TRB_Total',
            'Unnamed: 15': 'AST_Total',
            'Unnamed: 16': 'STL_Total',
            'Unnamed: 17': 'BLK_Total',
            'Unnamed: 18': 'TOV',
            'Unnamed: 19': 'PF',
            'Unnamed: 20': 'PTS_Total',
            'Shooting': 'FG%',
            'Unnamed: 22': '3P%',
            'Unnamed: 23': 'FT%',
            'Per Game': 'MP',
            'Unnamed: 25': 'PTS',
            'Unnamed: 26': 'TRB',
            'Unnamed: 27': 'AST',
            'Unnamed: 28': 'STL',
            'Unnamed: 29': 'BLK'
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 删除重复的表头行
        df = df[df['Player'] != 'Player'].reset_index(drop=True)
        
        # 转换为数值类型
        numeric_cols = ['G', 'MP_Total', 'FG', 'FGA', '3P', '3PA', 'FT', 'FTA', 'ORB',
                       'TRB_Total', 'AST_Total', 'STL_Total', 'BLK_Total', 'TOV', 'PF',
                       'PTS_Total', 'FG%', '3P%', 'FT%', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 添加高级统计计算
        if all(col in df.columns for col in ['FGA', 'FG']):
            df['TS%'] = df['PTS_Total'] / (2 * (df['FGA'] + 0.44 * df['FTA']))
        if all(col in df.columns for col in ['TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF']):
            df['GameScore'] = (df['PTS'] + 0.4 * df['FG'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FT']) 
                             + 0.7 * df['ORB'] + 0.3 * df['TRB'] - df['TRB_Total'] + df['AST'] 
                             + df['STL'] + 0.7 * df['BLK'] - 0.4 * df['PF'] - df['TOV'])
        
        return df
        
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return pd.DataFrame()

def calculate_ppi(df, ppi_version="基础版", use_advanced_stats=False):
    """计算PPI（球员表现指数）"""
    df = df.copy()
    
    if ppi_version == "基础版":
        # 原始PPI公式
        df['PPI'] = df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5
        df['PPI_Description'] = "基础版PPI = 得分×1.0 + 篮板×1.2 + 助攻×1.5"
    
    elif ppi_version == "增强版":
        # 增强版PPI公式（包含防守和效率）
        base_score = df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5
        
        # 防守贡献
        defense_score = df['STL'].fillna(0) * 1.5 + df['BLK'].fillna(0) * 2.0
        
        # 效率贡献（考虑命中率）
        efficiency_score = (
            df['FG%'].fillna(0) * 5.0 +  # 投篮命中率贡献
            df['3P%'].fillna(0) * 3.0 +  # 三分命中率贡献
            df['FT%'].fillna(0) * 2.0    # 罚球命中率贡献
        )
        
        # 综合PPI
        df['PPI'] = (base_score * 0.6 + 
                    defense_score * 0.25 + 
                    efficiency_score * 0.15)
        df['PPI_Description'] = "增强版PPI = (基础三要素×0.6) + (防守×0.25) + (效率×0.15)"
        
        # 添加细分指标
        df['基础分'] = base_score
        df['防守分'] = defense_score
        df['效率分'] = efficiency_score
    
    elif ppi_version == "进阶版" and use_advanced_stats:
        # 进阶版PPI公式（包含更多高阶数据）
        try:
            # 基础产出
            production_score = (
                df['PTS'] * 1.0 + 
                df['TRB'] 
