import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 配置：Google Sheet 发布为 CSV 的链接 ---
CSV_LINKS = {
    "2022-23 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQO7FDHZNjcOQogg4iFO5f6Su-oaMyITCBny73iWUPxTNNGqe9eMrHaD5BwlIlnr21N_Rsq9gQS5Vqp/pub?gid=0&single=true&output=csv",
    "2023-24 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTh6ABCuCa4EBCvktT5WzgUHpkacmSwuw-YulyoZFm-1BiqbhAhtCcfCLj55abTn4JxxHoRYtldbDRo/pub?gid=0&single=true&output=csv",
    "2024-25 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRq5EQLiWNZzygGsgc19Svqdx6IMKfDzaH_yhui-omPcptN_orV3mL6zCxitRjsBxcT0ZCl0KUzZUnS/pub?gid=0&single=true&output=csv"
}

# --- 2. 核心函数：智能数据清洗 ---
@st.cache_data(ttl=600)
def fetch_and_clean_data(url):
    try:
        # 直接读取。由于有双层表头，我们先读取所有行。
        df = pd.read_csv(url, header=None)
        
        # 搜索包含 "Player" 的行作为真正的表头（通常在第2行，即索引1）
        header_row_index = 0
        for i, row in df.iterrows():
            if 'Player' in row.values:
                header_row_index = i
                break
        
        # 重新以该行作为表头读取
        df.columns = df.iloc[header_row_index]
        df = df.iloc[header_row_index + 1:].reset_index(drop=True)
        
        # 处理重复列名（PTS出现了两次：总分和场均）
        # Pandas 会自动把重复列重命名为 PTS, PTS.1
        # 在你的表中，最后的 PTS/TRB/AST 通常是 Per Game 数据
        new_cols = []
        counts = {}
        for col in df.columns:
            col_name = str(col).strip()
            counts[col_name] = counts.get(col_name, 0) + 1
            if counts[col_name] > 1:
                new_cols.append(f"{col_name}_{counts[col_name]-1}")
            else:
                new_cols.append(col_name)
        df.columns = new_cols

        # 映射字段（优先使用 Per Game 结尾的数据）
        mapping = {
            'PTS': 'PTS_1' if 'PTS_1' in df.columns else 'PTS',
            'TRB': 'TRB_1' if 'TRB_1' in df.columns else 'TRB',
            'AST': 'AST_1' if 'AST_1' in df.columns else 'AST',
            'G': 'G'
        }
        
        for final_name, raw_name in mapping.items():
            if raw_name in df.columns:
                df[final_name] = pd.to_numeric(df[raw_name], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"解析失败: {e}")
        return None

# --- 3. PPI 计算引擎 ---
def apply_ppi_logic(df):
    if df is None or 'PTS' not in df.columns:
        return None
    
    # PPI v1.1: 权重优化（得分1, 篮板1.2, 助攻1.5）
    df['PPI'] = (df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5).round(1)
    
    # 投资信号逻辑
    def get_signal(ppi):
        if ppi >= 25: return "🚀 强力买入"
        if ppi >= 18: return "📈 买入"
        if ppi >= 12: return "📊 积累"
        return "⚖️ 持有"
    
    df['Signal'] = df['PPI'].apply(get_signal)
    return df

# --- 4. Streamlit UI 布局 ---
st.set_page_config(page_title="RookieFlip2X", layout="wide")
st.title("🏀 RookieFlip2X: NBA 新秀量化投资系统")

selected_label = st.sidebar.selectbox("选择赛季数据源", list(CSV_LINKS.keys()))
df_raw = fetch_and_clean_data(CSV_LINKS[selected_label])
df_final = apply_ppi_logic(df_raw)

if df_final is not None:
    # 筛选器
    min_g = st.sidebar.slider("最小出场次数", 1, 82, 10)
    display_df = df_final[df_final['G'] >= min_g].sort_values('PPI', ascending=False)

    # 核心指标看板
    c1, c2, c3 = st.columns(3)
    c1.metric("当届标王", display_df.iloc[0]['Player'], f"PPI: {display_df.iloc[0]['PPI']}")
    c2.metric("分析样本数", len(display_df))
    c3.metric("平均 PPI", round(display_df['PPI'].mean(), 1))

    # 数据表展示
    st.subheader("📋 投资信号明细")
    st.dataframe(
        display_df[['Player', 'PPI', 'Signal', 'PTS', 'TRB', 'AST', 'G']],
        use_container_width=True,
        hide_index=True
    )

    # 散点图可视化
    st.subheader("🔍 表现与价值分布")
    fig = px.scatter(display_df, x="PTS", y="PPI", size="G", color="Signal",
                     hover_name="Player", title="得分 vs 综合战力指数")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 请在 Google Sheet 中发布 CSV 链接并填入代码。")
