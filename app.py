import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 数据源配置
CSV_LINKS = {
    "2023-24": "https://docs.google.com/spreadsheets/d/13fmn1LXuvm3tpHI2ZVJ2OYlaUJi3hzbYLe07_n29T1w/edit?usp=sharing",
    "2024-25": "https://docs.google.com/spreadsheets/d/1ooZVm8U3fsfG_UtHyy7dpD_r4eMlsgwt1gg-4AGoZQo/edit?usp=sharing",
    "2025-26": "https://docs.google.com/spreadsheets/d/1PVB1XRfrYrLTPLhCu5T08-tJdT--iHDV6mnUdENubws/edit?usp=sharing"
}

def fetch_and_clean_data(season):
    """获取并清洗数据"""
    try:
        url = CSV_LINKS.get(season, CSV_LINKS["2023-24"])
        df_raw = pd.read_csv(url)
        
        # 查找包含关键字段的行作为表头
        header_row = 0
        for idx, row in df_raw.iterrows():
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
        df = df[df['Player'] != 'Player'].reset_index(drop=True)
        
        # 转换为数值类型
        numeric_cols = ['G', 'MP_Total', 'FG', 'FGA', '3P', '3PA', 'FT', 'FTA', 'ORB',
                       'TRB_Total', 'AST_Total', 'STL_Total', 'BLK_Total', 'TOV', 'PF',
                       'PTS_Total', 'FG%', '3P%', 'FT%', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算高级统计
        if all(col in df.columns for col in ['FGA', 'FG', 'FTA', 'PTS_Total']):
            df['TS%'] = df['PTS_Total'] / (2 * (df['FGA'] + 0.44 * df['FTA']))
        
        return df
        
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return pd.DataFrame()

def calculate_ppi(df, ppi_version="基础版"):
    """计算球员表现指数(PPI)"""
    df = df.copy()
    
    if ppi_version == "基础版":
        df['PPI'] = df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5
        df['PPI_Description'] = "基础版PPI = 得分×1.0 + 篮板×1.2 + 助攻×1.5"
    
    elif ppi_version == "增强版":
        base_score = df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5
        defense_score = df['STL'].fillna(0) * 1.5 + df['BLK'].fillna(0) * 2.0
        efficiency_score = (df['FG%'].fillna(0) * 5.0 + 
                          df['3P%'].fillna(0) * 3.0 + 
                          df['FT%'].fillna(0) * 2.0)
        
        df['PPI'] = base_score * 0.6 + defense_score * 0.25 + efficiency_score * 0.15
        df['PPI_Description'] = "增强版PPI = (基础三要素×0.6) + (防守×0.25) + (效率×0.15)"
        df['基础分'] = base_score
        df['防守分'] = defense_score
        df['效率分'] = efficiency_score
    
    elif ppi_version == "进阶版":
        production_score = (df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5 +
                          df['STL'].fillna(0) * 2.0 + df['BLK'].fillna(0) * 2.5)
        
        efficiency_score = (df['FG%'].fillna(0) * 6.0 + df['3P%'].fillna(0) * 4.0 + 
                          df['FT%'].fillna(0) * 3.0)
        
        if 'MP' in df.columns:
            mp_factor = np.minimum(df['MP'] / 30.0, 1.5)
            production_score = production_score * mp_factor
        
        if 'TOV' in df.columns:
            turnover_penalty = df['TOV'].fillna(0) * 0.5
            production_score = production_score - turnover_penalty
        
        df['PPI'] = production_score * 0.7 + efficiency_score * 0.3
        df['PPI_Description'] = "进阶版PPI = (产出×0.7) + (效率×0.3) [含时间调整和失误惩罚]"
    
    return df

def generate_signal(df, signal_type="默认"):
    """生成投资信号"""
    df = df.copy()
    
    if signal_type == "默认":
        conditions = [
            df['PPI'] >= 25,
            df['PPI'] >= 18,
            df['PPI'] >= 12
        ]
        choices = ['🚀 强力买入', '📈 买入', '📊 积累']
        df['Signal'] = np.select(conditions, choices, default='⚖️ 持有')
        df['Signal_Explanation'] = "基于PPI阈值"
    
    elif signal_type == "动态阈值":
        p75 = df['PPI'].quantile(0.75)
        p50 = df['PPI'].quantile(0.50)
        p25 = df['PPI'].quantile(0.25)
        
        conditions = [
            df['PPI'] >= p75 * 1.2,
            df['PPI'] >= p75,
            df['PPI'] >= p50
        ]
        choices = [f'🚀 强力买入(前{int((1-0.75)*100)}%)', 
                  f'📈 买入(前{int((1-0.5)*100)}%)', 
                  f'📊 积累(前{int((1-0.25)*100)}%)']
        df['Signal'] = np.select(conditions, choices, default='⚖️ 持有')
        df['Signal_Explanation'] = f"动态阈值(P75={p75:.1f}, P50={p50:.1f}, P25={p25:.1f})"
    
    return df

def main():
    """主应用函数"""
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
        season = st.selectbox("选择赛季", list(CSV_LINKS.keys()), index=1)
        
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
            st.error("数据获取失败，请检查网络连接或数据源。")
            return
        
        # 应用过滤器
        df_filtered = df.copy()
        if 'G' in df.columns:
            df_filtered = df_filtered[df_filtered['G'] >= min_games]
        if 'MP' in df.columns:
            df_filtered = df_filtered[df_filtered['MP'] >= min_minutes]
        
        if df_filtered.empty:
            st.warning("没有满足筛选条件的球员数据。")
            return
        
        # 计算PPI和信号
        df_analyzed = calculate_ppi(df_filtered, ppi_version)
        df_signals = generate_signal(df_analyzed, signal_type)
        df_display = df_signals.sort_values('PPI', ascending=False).reset_index(drop=True)
        
        # 显示关键指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if not df_display.empty:
                top_player = df_display.iloc[0]
                st.metric("🏆 当届标王", f"{top_player.get('Player', 'N/A')}", 
                         f"PPI: {top_player.get('PPI', 0):.1f}")
        
        with col2:
            st.metric("👥 分析样本数", f"{len(df_display)}人", 
                     f"出场≥{min_games}场, ≥{min_minutes}分钟")
        
        with col3:
            avg_ppi = df_display['PPI'].mean() if 'PPI' in df_display.columns else 0
            st.metric("📈 平均PPI", f"{avg_ppi:.1f}", f"{ppi_version}")
        
        with col4:
            buy_signals = len(df_display[df_display['Signal'].str.contains('买入')])
            st.metric("💡 推荐投资", f"{buy_signals}人", 
                     f"{buy_signals/len(df_display)*100:.1f}%")
        
        st.divider()
        
        # 数据表格
        st.subheader("📊 球员数据表")
        display_cols = ['Player', 'PPI', 'Signal', 'PTS', 'TRB', 'AST', 'STL', 'BLK']
        if 'FG%' in df_display.columns:
            display_cols.extend(['FG%', '3P%', 'FT%'])
        if 'MP' in df_display.columns:
            display_cols.append('MP')
        if 'G' in df_display.columns:
            display_cols.append('G')
        
        if ppi_version == "增强版":
            display_cols.extend(['基础分', '防守分', '效率分'])
        
        display_cols = [col for col in display_cols if col in df_display.columns]
        
        st.dataframe(df_display[display_cols], use_container_width=True, height=400)
        
        # 可视化
        st.subheader("📈 可视化分析")
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.histogram(df_display, x='PPI', title='PPI分布直方图', nbins=20, 
                               color_discrete_sequence=['#2E86AB'])
            fig1.update_layout(xaxis_title='PPI值', yaxis_title='球员数量', showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = px.scatter(df_display, x='PTS', y='PPI', size='TRB' if 'TRB' in df_display.columns else None,
                             color='Signal', hover_name='Player', title='得分 vs PPI（点大小=篮板）',
                             labels={'PTS': '场均得分', 'PPI': 'PPI值'},
                             color_discrete_map={'🚀 强力买入': '#00CC96', '📈 买入': '#636EFA', 
                                                '📊 积累': '#EF553B', '⚖️ 持有': '#AB63FA'})
            st.plotly_chart(fig2, use_container_width=True)
        
        # 雷达图展示顶级球员
        if len(df_display) >= 5:
            st.subheader("🎯 顶级球员多维能力图")
            top_players = df_display.head(5)
            radar_metrics = ['PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%']
            radar_metrics = [m for m in radar_metrics if m in top_players.columns]
            
            radar_data = []
            for idx, player in top_players.iterrows():
                player_data = {'Player': player['Player'], 'PPI': player['PPI']}
                for metric in radar_metrics:
                    if metric in ['FG%', '3P%', 'FT%']:
                        player_data[metric] = player.get(metric, 0) * 100
                    else:
                        player_data[metric] = player.get(metric, 0)
                radar_data.append(player_data)
            
            fig3 = go.Figure()
            for player in radar_data:
                fig3.add_trace(go.Scatterpolar(
                    r=[player.get(m, 0) for m in radar_metrics],
                    theta=radar_metrics,
                    fill='toself',
                    name=f"{player['Player']} (PPI:{player['PPI']:.1f})"
                ))
            
            fig3.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                showlegend=True,
                title="前5名球员能力雷达图"
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        # 下载按钮
        st.divider()
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 下载分析结果(CSV)",
            data=csv,
            file_name=f"rookie_analysis_{season}.csv",
            mime="text/csv"
        )
        
        # 模型解释
        with st.expander("ℹ️ 模型解释"):
            st.markdown(f"""
            ### PPI模型说明
            **当前使用版本**: {ppi_version}
            **{df_display['PPI_Description'].iloc[0] if 'PPI_Description' in df_display.columns else ''}
            **信号生成方式**: {signal_type}
            - {df_display['Signal_Explanation'].iloc[0] if 'Signal_Explanation' in df_display.columns else ''}
            **筛选条件**:
            - 最少出场次数: {min_games}场
            - 最少场均时间: {min_minutes}分钟
            - 有效样本数: {len(df_display)}人
            """)
    
    except Exception as e:
        st.error(f"处理数据时发生错误: {str(e)}")
        st.info("请尝试调整筛选条件或选择其他赛季。")

if __name__ == "__main__":
    main()
