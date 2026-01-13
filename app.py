import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 配置：替换为你发布后的 CSV 链接
CSV_LINKS = {
    "2022-23 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQO7FDHZNjcOQogg4iFO5f6Su-oaMyITCBny73iWUPxTNNGqe9eMrHaD5BwlIlnr21N_Rsq9gQS5Vqp/pub?gid=0&single=true&output=csv",
    "2023-24 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTh6ABCuCa4EBCvktT5WzgUHpkacmSwuw-YulyoZFm-1BiqbhAhtCcfCLj55abTn4JxxHoRYtldbDRo/pub?gid=0&single=true&output=csv",
    "2024-25 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRq5EQLiWNZzygGsgc19Svqdx6IMKfDzaH_yhui-omPcptN_orV3mL6zCxitRjsBxcT0ZCl0KUzZUnS/pub?gid=0&single=true&output=csv"
}

# 2. 核心算法：PPI 计算引擎
def calculate_ppi(df):
    # 统一字段名逻辑（防止不同年份表头差异）
    mapping = {'PTS': ['PTS', 'Points'], 'TRB': ['TRB', 'Total Rebounds'], 'AST': ['AST', 'Assists']}
    for target, alternates in mapping.items():
        for alt in alternates:
            if alt in df.columns:
                df = df.rename(columns={alt: target})
    
    # 转为数值
    for col in ['PTS', 'TRB', 'AST', 'G']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # PPI 公式 v1.0
    df['PPI'] = (df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5).round(1)
    return df

# 3. Streamlit UI
st.set_page_config(page_title="RookieFlip2X", layout="wide")
st.sidebar.title("🏀 RookieFlip2X 量化控制台")

# 年份切换
year_choice = st.sidebar.selectbox("选择新秀届次", list(CSV_LINKS.keys()))

@st.cache_data(ttl=600) # 缓存10分钟，防止重复请求
def fetch_data(url):
    return pd.read_csv(url)

try:
    raw_data = fetch_data(CSV_LINKS[year_choice])
    processed_data = calculate_ppi(raw_data)
    
    # 顶部排名
    st.header(f"🏆 {year_choice} 新秀 PPI 投资排名")
    top_10 = processed_data.sort_values('PPI', ascending=False).head(10)
    st.table(top_10[['Player', 'PPI', 'PTS', 'TRB', 'AST']])

    # 年份对比雷达图或散点图
    st.divider()
    st.subheader("分析视图")
    fig = px.scatter(processed_data, x="PTS", y="PPI", size="TRB", hover_name="Player", color="PPI")
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"连接 Google Sheet 失败，请检查链接是否已发布为 CSV 格式。错误详情: {e}")
