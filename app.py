import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 1. 计算核心模型分数 ---
def calculate_quant_score(df):
    # 处理缺失值，防止除以0
    df['SILVER_PSA10_PRICE'] = df['SILVER_PSA10_PRICE'].replace(0, np.nan)
    # 公式：(14天均分 * 100) / (价格 * log(Pop + 1))
    df['FINAL_SCORE'] = (
        (df['MA14_INDEX'] * 100) / 
        (df['SILVER_PSA10_PRICE'] * np.log1p(df['PSA10_POP']))
    ).round(3)
    return df

# --- 2. 网页 UI ---
def main():
    st.set_page_config(page_title="RookieFlip2X Quant", layout="wide")
    st.title("💎 RookieFlip2X 量化投资仪表盘")
    
    # 加载数据 (赛场数据 + 市场数据)
    try:
        # 建议在本地将赛场csv和市场csv合并
        df = pd.read_csv("data_final.csv") 
        df = calculate_quant_score(df)
        
        # --- 视觉优化 1: 顶部核心 KPI ---
        st.subheader("🔥 全新秀年投资性价比榜首")
        cols = st.columns(3)
        for i, year in enumerate(["Rookie", "2nd Year", "3rd Year"]):
            top_player = df[df['EXPERIENCE'].str.contains(year)].sort_values("FINAL_SCORE", ascending=False).iloc[0]
            cols[i].metric(
                label=f"{year} 领跑者", 
                value=top_player['PLAYER_NAME'], 
                delta=f"Score: {top_player['FINAL_SCORE']}"
            )

        # --- 视觉优化 2: 投资象限气泡图 ---
        st.divider()
        st.subheader("🎯 投资决策象限图 (Performance vs. Price)")
        
        # 建立交互式气泡图
        fig = px.scatter(
            df, 
            x="MA14_INDEX", 
            y="SILVER_PSA10_PRICE",
            size="PSA10_POP", 
            color="FINAL_SCORE",
            text="PLAYER_NAME",
            hover_name="PLAYER_NAME",
            color_continuous_scale=px.colors.diverging.RdYlGn, # 绿好红差
            labels={"MA14_INDEX": "14日表现均分 (MA14)", "SILVER_PSA10_PRICE": "银折 PSA 10 价格 ($)"},
            height=700
        )
        
        # 优化坐标轴：价格越低（Y轴越靠下）代表性价比越高，反转Y轴
        fig.update_yaxes(autorange="reversed")
        fig.update_traces(textposition='top center')
        
        # 添加象限参考线
        fig.add_hline(y=df['SILVER_PSA10_PRICE'].median(), line_dash="dot", annotation_text="平均价格")
        fig.add_vline(x=df['MA14_INDEX'].median(), line_dash="dot", annotation_text="平均表现")

        st.plotly_chart(fig, use_container_width=True)
        st.caption("注：右下角球员（高表现、低价格）为模型锁定的最佳 Flip 标的。")

        # --- 视觉优化 3: 详细数据表 ---
        st.divider()
        st.subheader("📋 原始数据穿透")
        st.dataframe(df.sort_values("FINAL_SCORE", ascending=False), use_container_width=True)

    except Exception as e:
        st.warning(f"等待数据同步中... {e}")

if __name__ == "__main__":
    main()
