import streamlit as st
import plotly.express as px

st.set_page_config(page_title="RookieFlip2X Dashboard", layout="wide")
df = pd.read_csv('data/cards_data.csv')

st.title("🏀 RookieFlip2X 投资决策看板")

# 1. 核心象限图
fig = px.scatter(df, x="price", y="ma14", size="final_score", color="final_score",
                 hover_name="player", title="价值象限图 (左上为强力买入)")
st.plotly_chart(fig, use_container_width=True)

# 2. 操作建议排名
st.subheader("🔥 实时信号排名")
top_buys = df.sort_values('final_score', ascending=False).head(5)
st.table(top_buys[['player', 'final_score', 'ma14', 'price']])
