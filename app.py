import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# --- 1. 数据加载与处理 ---
DATA_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/main/nba_rookies_combined.csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(DATA_URL)
        df['Fetch_Date'] = pd.to_datetime(df['Fetch_Date'])
        
        # 字段映射
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
    """三套量化评估逻辑"""
    df['基础产出评分'] = (df['场均得分'] + (df['场均篮板'] * 1.2) + (df['场均助攻'] * 1.5) + (df['场均抢断'] * 2.0) + (df['场均盖帽'] * 2.0) - df['场均失误'])
    df['效率加权评分'] = ((df['场均得分'] + (df['场均篮板'] * 0.8) + (df['场均助攻'] * 1.2)) * (df['命中率'] + 0.5)) + (df['场均抢断'] + df['场均盖帽']) * 2.0
    df['进阶潜力评分'] = (((df['场均得分'] + df['场均篮板'] + df['场均助攻']) / (df['场均分钟'] + 0.1) * 36) * (df['命中率'] * 1.1)) - (df['场均失误'] * 1.5)
    return df

# --- 2. 页面配置与合规声明 ---
st.set_page_config(page_title="NBA新秀量化数据分析", layout="wide")

with st.sidebar:
    st.warning("⚠️ **免责声明**")
    st.
