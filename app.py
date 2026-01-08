import streamlit as st
import pandas as pd
import sys
from nba_api.stats.endpoints import leaguedashplayerstats

def fetch_data():
    # 简单演示：抓取NBA新秀数据
    stats = leaguedashplayerstats.LeagueDashPlayerStats(season='2024-25', player_experience_nullable='Rookie')
    df = stats.get_data_frames()[0]
    df = df[['PLAYER_NAME', 'TEAM_ABBREVIATION', 'PTS', 'PIE']]
    df['FLIP_INDEX'] = (df['PTS'] * 0.4 + df['PIE'] * 50).round(2)
    df.to_csv("data.csv", index=False)

if "--mode" in sys.argv and "scrape" in sys.argv:
    fetch_data()
else:
    st.title("🚀 RookieFlip2X 智能评级")
    try:
        df = pd.read_csv("data.csv")
        st.dataframe(df.sort_values("FLIP_INDEX", ascending=False))
    except:
        st.warning("数据正在初始化，请稍后...")
