import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings
from urllib.parse import quote

# 过滤不必要的警告
warnings.filterwarnings('ignore')

# ==========================================
# 1. 安全与配置管理
# ==========================================
# 建议通过 Streamlit Secrets 管理 URL，此处为示范
DEFAULT_BASE_URL = "https://raw.githubusercontent.com/rookieflip2x/workflows/refs/heads/main/"

CSV_FILES = {
    "2023-24": "NBA_2023-24_%20rookies%20.csv",
    "2024-25": "NBA_2024-25_rookies%20.csv",
    "2025-26": "NBA_2025-26_rookies%20.csv"
}

@st.cache_data(ttl=3600)  # 合规缓存：1小时刷新一次，减轻服务器压力
def fetch_and_clean_data(season):
    """
    合规化的数据获取函数：
    - 强制 HTTPS
    - 脱敏异常处理
    - 自动路径转义
    """
    try:
        filename = CSV_FILES.get(season)
        if not filename:
            raise ValueError("非法请求：未授权的赛季数据")
        
        # 构建安全的 URL
        target_url = f"{DEFAULT_BASE_URL}{filename}"
        if not target_url.startswith("https://"):
            raise Security+Error("非法协议：必须使用 HTTPS")

        # 读取数据 (设置超时与读取限制)
        df_raw = pd.read_csv(target_url, on_bad_lines='warn', storage_options={'timeout': 10})
        
        # 定位表头
        header_idx = None
        for i, row in df_raw.head(20).iterrows():
            if 'Player' in row.values:
                header_idx = i
                break
        
        if header_idx is not None:
            df = pd.read_csv(target_url, header=header_idx + 1)
        else:
            df = df_raw

        # 列名清理与归一化
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # 核心字段映射
        field_mapping = {
            'Player': ['Player'], 'G': ['G', 'GP'], 'MP': ['MP'],
            'PTS': ['PTS'], 'TRB': ['TRB'], 'AST': ['AST'],
            'STL': ['STL'], 'BLK': ['BLK'], 'FG%': ['FG%'], 'TOV': ['TOV']
        }
        
        rename_dict = {}
        for target, aliases in field_mapping.items():
            for col in df.columns:
                if any(alias == col for alias in aliases):
                    rename_dict[col] = target
                    break
        df = df.rename(columns=rename_dict)

        # 类型转换与脱敏
        essential_cols = ['G', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', 'TOV']
        for col in essential_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0

        return df[df['Player'].notna() & (df['Player'] != 'Player')].copy()

    except Exception as e:
        # 合规处理：日志记录错误，但前端只展示脱敏信息
        # logger.error(f"Internal Error: {e}") 
        st.error("🔒 数据获取受限：请检查网络连接或稍后再试。")
        return pd.DataFrame()

# ==========================================
# 2. 核心量化模型
# ==========================================
def run_quant_model(df, mode):
    """
    计算逻辑：限制结果范围，防止数值溢出攻击
    """
    df = df.copy()
    if mode == "效率加权型":
        # 归一化 FG% 权重
        df['PPI'] = (df['PTS'] + df['TRB']*0.8 + df['AST']*1.2) * (df['FG%'].clip(0, 1) + 0.5) + (df['STL'] + df['BLK'])*2
    elif mode == "进阶投资型":
        # 这里的 36 分钟标准化需处理异常极小值
        safe_mp = df['MP'].apply(lambda x: x if x > 2 else np.nan) 
        df['PPI'] = ((df['PTS'] + df['TRB'] + df['AST']) / safe_mp * 36) * (df['FG%'].clip(0, 1) * 1.1) - (df['TOV'] * 1.5)
    else:
        df['PPI'] = df['PTS'] + df['TRB']*1.2 + df['AST']*1.5 + df['STL']*2 + df['BLK']*2 - df['TOV']
    
    df['PPI'] = df['PPI'].replace([np.inf, -np.inf], 0).fillna(0).clip(0, 100)
    return df

# ==========================================
# 3. 动态合规信号系统
# ==========================================
def get_investment_signals(df):
    if df.empty: return df
    
    # 使用中位数和四分位距（IQR）比标准差更稳健，防止个别离群数据干扰
    q3 = df['PPI'].quantile(0.75)
    q1 = df['PPI'].quantile(0.25)
    iqr = q3 - q1
    
    def classify(val):
        if val >= q3 + 1.5 * iqr: return '💎 顶级标的 (Alpha)'
        if val >= q3: return '✅ 优质资产 (Beta)'
        if val >= df['PPI'].median(): return 'Hold 保持观察'
        return 'Underperform 减持'
    
    df['Recommendation'] = df['PPI'].apply(classify)
    return df

# 4. 前端展示 (Streamlit UI)
# ==========================================
def main():
    st.set_page_config(page_title="RookieFlip2X Compliance", layout="wide")
    st.title("🔒 RookieFlip2X 量化决策系统 (合规版)")
    
    # 侧边栏：加入合规声明
    with st.sidebar:
        st.info("⚖️ **合规声明**：本系统所提供之数据与信号仅供学术参考，不构成任何投资建议。")
        season = st.selectbox("数据赛季", list(CSV_FILES.keys()), index=2)
        mode = st.radio("模型算法", ["基础产出型", "效率加权型", "进阶投资型"])
        st.divider()
        min_g = st.number_input("最小样本 (场次)", 0, 82, 5)
        min_m = st.number_input("最小出场 (分钟)", 0.0, 48.0, 10.0)

    # 处理流程
    data = fetch_and_clean_data(season)
    if not data.empty:
        # 输入验证过滤
        mask = (data['G'] >= min_g) & (data['MP'] >= min_m)
        df_processed = run_quant_model(data[mask], mode)
        final_df = get_investment_signals(df_processed).sort_values('PPI', ascending=False)
        
        # 关键指标展示
        top_p = final_df.iloc[0]
        st.metric("核心资产：", top_p['Player'], f"评分: {top_p['PPI']:.2f}")

        # 图表展示 (使用合规调色盘)
        fig = px.scatter(final_df, x='MP', y='PPI', color='Recommendation',
                         hover_name='Player', size='PTS',
                         title=f"{season} 赛季新秀资产评估分布",
                         color_discrete_map={
                             '💎 顶级标的 (Alpha)': '#FF4B4B',
                             '✅ 优质资产 (Beta)': '#00CC96',
                             'Hold 保持观察': '#FFAA00',
                             'Underperform 减持': '#9EA8B1'
                         })
        st.plotly_chart(fig, use_container_width=True)

        # 数据审计表
        st.subheader("📋 审计与明细数据")
        st.dataframe(final_df[['Player', 'PPI', 'Recommendation', 'PTS', 'FG%', 'MP', 'G']], use_container_width=True)
    else:
        st.warning("⚠️ 无法载入数据，请确认您的访问权限或联系系统管理员。")

if __name__ == "__main__":
    main()
