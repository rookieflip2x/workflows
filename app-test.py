import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# --- 1. 配置：Google Sheet 发布为 CSV 的链接 ---
CSV_LINKS = {
    "2023-24 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vT_p_q7D-Pz8fL5N6z.../pub?output=csv",
    "2022-23 赛季": "你的链接2", 
    "2024-25 赛季": "你的链接3"
}

# --- 2. 核心函数：智能数据清洗 ---
@st.cache_data(ttl=600)
def fetch_and_clean_data(url):
    try:
        # 直接读取CSV
        df = pd.read_csv(url, header=None)
        
        # 搜索包含 "Player" 的行作为真正的表头
        header_row_index = 0
        for i, row in df.iterrows():
            if 'Player' in str(row.values):
                header_row_index = i
                break
        
        # 重新以该行作为表头读取
        df.columns = df.iloc[header_row_index]
        df = df.iloc[header_row_index + 1:].reset_index(drop=True)
        
        # 处理重复列名
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

        # 映射字段（基于您的文档结构优化）
        mapping = {
            'PTS': 'PTS_1' if 'PTS_1' in df.columns else 'PTS',
            'TRB': 'TRB_1' if 'TRB_1' in df.columns else 'TRB', 
            'AST': 'AST_1' if 'AST_1' in df.columns else 'AST',
            'STL': 'STL_1' if 'STL_1' in df.columns else 'STL',
            'BLK': 'BLK_1' if 'BLK_1' in df.columns else 'BLK',
            'TOV': 'TOV_1' if 'TOV_1' in df.columns else 'TOV',
            'FG%': 'FG%',
            '3P%': '3P%',
            'FT%': 'FT%', 
            'G': 'G',
            'MP': 'MP',
            'FG': 'FG',
            'FGA': 'FGA',
            'FT': 'FT',
            'FTA': 'FTA',
            '3P': '3P',
            '3PA': '3PA',
            'ORB': 'ORB',
            'PF': 'PF'
        }
        
        for final_name, raw_name in mapping.items():
            if raw_name in df.columns:
                df[final_name] = pd.to_numeric(df[raw_name], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"解析失败: {e}")
        return None

# --- 3. 优化版 PPI 计算引擎 v3.0 ---
def apply_ppi_logic_v3(df):
    if df is None:
        return None
    
    # 数据验证和预处理
    required_cols = ['PTS', 'TRB', 'AST', 'FG%', '3P%', 'FT%', 'STL', 'BLK', 'TOV', 
                    'G', 'MP', 'FG', 'FGA', 'FT', 'FTA', 'PF', 'ORB']
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0
    
    # 转换为数值类型
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 计算高阶指标
    # 1. 真实命中率（TS%）
    df['TS%'] = np.where((df['FGA'] + 0.44 * df['FTA']) > 0,
                         df['PTS'] / (2 * (df['FGA'] + 0.44 * df['FTA'])), 0)
    
    # 2. 使用率近似值
    df['USG_approx'] = np.where(df['MP'] > 0,
                               (df['FGA'] + 0.44 * df['FTA'] + df['TOV']) * 48 / (df['MP'] * 5), 0)
    
    # 3. 基础效率值
    df['EFF'] = (df['PTS'] + df['TRB'] + df['AST'] + df['STL'] + df['BLK'] - 
                df['TOV'] - (df['FGA'] - df['FG']) - (df['FTA'] - df['FT']))
    
    # PPI v3.0: 六维评分系统
    # 1. 基础产出分 (30%权重)
    base_production = (df['PTS'] * 1.2 + df['TRB'] * 1.0 + df['AST'] * 1.3)
    
    # 2. 效率质量分 (25%权重)
    efficiency_score = np.where(df['TS%'] > 0.5, 
                               (df['TS%'] - 0.5) * 200,
                               (df['TS%'] - 0.5) * 100)
    
    # 3. 防守贡献分 (20%权重)
    defense_score = (df['STL'] * 2.5 + df['BLK'] * 2.0 - df['TOV'] * 0.5 + df['ORB'] * 0.8)
    
    # 4. 效率值加成 (15%权重)
    eff_bonus = df['EFF'] * 0.1
    
    # 5. 使用率调整 (10%权重)
    usage_adjustment = np.where(df['USG_approx'] > 20,
                               (df['USG_approx'] - 20) * 0.3, 0)
    
    # 综合PPI计算
    df['PPI_v3'] = (
        base_production * 0.3 + 
        efficiency_score * 0.25 + 
        defense_score * 0.2 +
        eff_bonus * 0.15 -
        usage_adjustment * 0.1
    )
    
    # 出场稳定性系数
    games_played = df['G']
    minutes_per_game = df['MP']
    
    stability_factor = np.where(
        (games_played >= 41) & (minutes_per_game >= 20), 1.2,
        np.where((games_played >= 20) & (minutes_per_game >= 10), 1.0, 0.8)
    )
    
    df['PPI_v3'] = (df['PPI_v3'] * stability_factor).round(1)
    
    # 保留原PPI用于对比
    df['PPI_Original'] = (df['PTS'] * 1.0 + df['TRB'] * 1.2 + df['AST'] * 1.5).round(1)
    
    # 投资信号优化
    def get_signal_v3(ppi, ts_pct, usg, games, mpg):
        if ppi >= 30 and ts_pct >= 0.55 and games >= 41 and mpg >= 25:
            return "🚀 精英核心"
        if ppi >= 25 and ts_pct >= 0.52 and games >= 20:
            return "📈 高效主力" 
        if ppi >= 18 and usg <= 25:
            return "💎 性价比之星"
        if ppi >= 12:
            return "📊 潜力积累"
        if games < 20 or mpg < 10:
            return "👀 观察名单"
        return "⚖️ 需要观察"
    
    df['Signal_v3'] = df.apply(
        lambda x: get_signal_v3(x['PPI_v3'], x['TS%'], x['USG_approx'], x['G'], x['MP']), axis=1
    )
    
    # 计算改进度
    df['PPI_Improvement'] = (df['PPI_v3'] - df['PPI_Original']).round(1)
    
    return df

# --- 4. 球员风格聚类功能 ---
def cluster_players_by_style(df, n_clusters=5):
    """根据球员技术统计进行风格聚类"""
    if df is None or len(df) < n_clusters:
        return df
    
    # 选择用于聚类的特征
    features = ['PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', '3P%', 'MP']
    
    # 确保所有特征都存在
    for feature in features:
        if feature not in df.columns:
            df[feature] = 0
    
    # 准备数据
    X = df[features].fillna(0)
    
    # 标准化数据
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # K-means聚类
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['PlayStyle_Cluster'] = kmeans.fit_predict(X_scaled)
    
    # 为每个聚类定义风格标签
    cluster_descriptions = {}
    cluster_centers = kmeans.cluster_centers_
    
    for i in range(n_clusters):
        center = cluster_centers[i]
        if center[0] > 0.5 and center[2] > 0.3:  # 得分和助攻都高
            cluster_descriptions[i] = "🔄 全能型球员"
        elif center[0] > 0.8:  # 得分特别高
            cluster_descriptions[i] = "🎯 得分手"
        elif center[3] > 0.5 or center[4] > 0.5:  # 防守数据突出
            cluster_descriptions[i] = "🛡️ 防守专家" 
        elif center[5] > 0.5 or center[6] > 0.5:  # 投篮效率高
            cluster_descriptions[i] = "⚡ 高效射手"
        else:
            cluster_descriptions[i] = "📊 角色球员"
    
    df['PlayStyle'] = df['PlayStyle_Cluster'].map(cluster_descriptions)
    
    return df

def analyze_playstyle_clusters(df):
    """分析并展示球员风格聚类结果"""
    st.header("🎯 球员风格聚类分析")
    
    # 聚类参数设置
    col1, col2 = st.columns(2)
    with col1:
        n_clusters = st.slider("聚类数量", 3, 8, 5)
    with col2:
        min_mpg = st.slider("最小场均时间(风格分析)", 0, 40, 10)
    
    # 过滤数据
    analysis_df = df[df['MP'] >= min_mpg].copy()
    
    if len(analysis_df) < n_clusters:
        st.warning("样本数量不足进行聚类分析")
        return
    
    # 进行聚类
    clustered_df = cluster_players_by_style(analysis_df, n_clusters)
    
    # 显示聚类分布
    st.subheader("📊 风格分布概况")
    style_counts = clustered_df['PlayStyle'].value_counts()
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_pie = px.pie(values=style_counts.values, names=style_counts.index,
                        title="球员风格分布")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        style_ppi = clustered_df.groupby('PlayStyle')['PPI_v3'].mean().sort_values(ascending=False)
        fig_bar = px.bar(x=style_ppi.index, y=style_ppi.values,
                        title="各风格平均PPI",
                        labels={'x': '球员风格', 'y': '平均PPI'})
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 详细风格分析
    st.subheader("🔍 各风格详细分析")
    
    selected_style = st.selectbox("选择要分析的风格", clustered_df['PlayStyle'].unique())
    
    style_players = clustered_df[clustered_df['PlayStyle'] == selected_style].sort_values('PPI_v3', ascending=False)
    
    st.write(f"**{selected_style}** - 共{len(style_players)}名球员")
    
    # 显示该风格球员列表
    st.dataframe(
        style_players[['Player', 'PPI_v3', 'Signal_v3', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', 'MP']].head(10),
        use_container_width=True
    )
    
    # 风格对比雷达图
    if len(style_players) > 0:
        st.subheader("📈 风格特征对比")
        
        selected_player = st.selectbox("选择球员", style_players['Player'].values)
        compare_player = st.selectbox("对比球员", ['同风格平均'] + list(style_players['Player'].values))
        
        player_data = style_players[style_players['Player'] == selected_player].iloc[0]
        
        if compare_player == '同风格平均':
            compare_data = style_players[['PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', '3P%']].mean()
            compare_name = f"{selected_style}平均"
        else:
            compare_data = style_players[style_players['Player'] == compare_player].iloc[0]
            compare_name = compare_player
        
        # 创建雷达图
        categories = ['得分', '篮板', '助攻', '抢断', '盖帽', '投篮%', '三分%']
        
        player_values = [
            player_data['PTS'] / 30, player_data['TRB'] / 15, player_data['AST'] / 10,
            player_data['STL'] / 3, player_data['BLK'] / 3, 
            player_data['FG%'] * 100 / 60, player_data['3P%'] * 100 / 50
        ]
        
        compare_values = [
            compare_data['PTS'] / 30, compare_data['TRB'] / 15, compare_data['AST'] / 10,
            compare_data['STL'] / 3, compare_data['BLK'] / 3,
            compare_data['FG%'] * 100 / 60, compare_data['3P%'] * 100 / 50
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=player_values + [player_values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=selected_player
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=compare_values + [compare_values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=compare_name
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=True,
            title=f"{selected_player} vs {compare_name}"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 风格投资建议
    st.subheader("💡 风格投资策略建议")
    
    style_analysis = {}
    for style in clustered_df['PlayStyle'].unique():
        style_data = clustered_df[clustered_df['PlayStyle'] == style]
        avg_ppi = style_data['PPI_v3'].mean()
        elite_ratio = len(style_data[style_data['Signal_v3'].isin(['🚀 精英核心', '📈 高效主力'])]) / len(style_data)
        style_analysis[style] = {'avg_ppi': avg_ppi, 'elite_ratio': elite_ratio}
    
    # 按平均PPI排序
    sorted_styles = sorted(style_analysis.items(), key=lambda x: x[1]['avg_ppi'], reverse=True)
    
    for style, stats in sorted_styles:
        with st.expander(f"{style} - 平均PPI: {stats['avg_ppi']:.1f} (精英比例: {stats['elite_ratio']:.1%})"):
            style_players = clustered_df[clustered_df['PlayStyle'] == style]
            top_players = style_players.nlargest(3, 'PPI_v3')[['Player', 'PPI_v3', 'Signal_v3']]
            
            st.write("**重点关注球员**:")
            for _, player in top_players.iterrows():
                st.write(f"- {player['Player']} (PPI: {player['PPI_v3']}, {player['Signal_v3']})")

# --- 5. Streamlit 主应用 ---
def main():
    st.set_page_config(page_title="RookieFlip2X", layout="wide")
    st.title("🏀 RookieFlip2X: NBA 新秀量化投资系统 v3.0")
    
    # 侧边栏配置
    st.sidebar.header("⚙️ 系统配置")
    selected_label = st.sidebar.selectbox("选择赛季数据源", list(CSV_LINKS.keys()))
    
    # 数据加载
    df_raw = fetch_and_clean_data(CSV_LINKS[selected_label])
    
    if df_raw is not None:
        # PPI计算
        df_final = apply_ppi_logic_v3(df_raw)
        
        # 主内容区域
        tab1, tab2, tab3 = st.tabs(["📊 投资分析", "🎯 风格聚类", "📈 数据探索"])
        
        with tab1:
            # 投资分析标签页
            st.header("📊 新秀投资分析")
            
            # 筛选器
            col1, col2, col3 = st.columns(3)
            with col1:
                min_g = st.slider("最小出场次数", 1, 82, 10)
            with col2:
                min_mpg = st.slider("最小场均时间", 0, 40, 10)
            with col3:
                min_ppi = st.slider("最小PPI_v3", 0, 50, 5)
            
            display_df = df_final[
                (df_final['G'] >= min_g) & 
                (df_final['MP'] >= min_mpg) &
                (df_final['PPI_v3'] >= min_ppi)
            ].sort_values('PPI_v3', ascending=False)
            
            if len(display_df) > 0:
                # 核心指标
                st.subheader("🎯 核心指标")
                col1, col2, col3, col4 = st.columns(4)
                top_player = display_df.iloc[0]
                
                col1.metric("当届标王", top_player['Player'], f"PPI_v3: {top_player['PPI_v3']}")
                col2.metric("分析样本数", len(display_df))
                col3.metric("平均 PPI_v3", round(display_df['PPI_v3'].mean(), 1))
                elite_count = len(display_df[display_df['Signal_v3'] == '🚀 精英核心'])
                col4.metric("精英球员", f"{elite_count}人")
                
                # 数据表格
                st.subheader("📋 投资信号明细")
                st.dataframe(
                    display_df[['Player', 'PPI_v3', 'Signal_v3', 'PTS', 'TRB', 'AST', 'TS%', 'USG_approx', 'G', 'MP']],
                    use_container_width=True
                )
                
                # 可视化
                st.subheader("📈 数据可视化")
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_scatter = px.scatter(display_df, x='PTS', y='PPI_v3', color='Signal_v3',
                                           size='MP', hover_name='Player', title='得分 vs PPI_v3')
                    st.plotly_chart(fig_scatter, use_container_width=True)
                
                with col2:
                    signal_counts = display_df['Signal_v3'].value_counts()
                    fig_pie = px.pie(values=signal_counts.values, names=signal_counts.index,
                                   title="投资信号分布")
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("暂无符合筛选条件的球员数据")
        
        with tab2:
            # 风格聚类标签页
            if st.sidebar.checkbox("启用球员风格分析", value=True):
                analyze_playstyle_clusters(df_final)
        
        with tab3:
            # 数据探索标签页
            st.header("🔍 数据探索")
            
            if len(df_final) > 0:
                # 球员对比工具
                st.subheader("🆚 球员对比工具")
                col1, col2 = st.columns(2)
                
                with col1:
                    player1 = st.selectbox("选择球员1", df_final['Player'].unique())
                with col2:
                    player2 = st.selectbox("选择球员2", df_final['Player'].unique())
                
                if player1 and player2:
                    p1_data = df_final[df_final['Player'] == player1].iloc[0]
                    p2_data = df_final[df_final['Player'] == player2].iloc[0]
                    
                    # 对比指标
                    comparison_data = {
                        '指标': ['PPI_v3', '场均得分', '场均篮板', '场均助攻', '真实命中率', '使用率', '出场次数'],
                        player1: [
                            p1_data['PPI_v3'], p1_data['PTS'], p1_data['TRB'], p1_data['AST'],
                            f"{p1_data['TS%']:.1%}", f"{p1_data['USG_approx']:.1f}%", p1_data['G']
                        ],
                        player2: [
                            p2_data['PPI_v3'], p2_data['PTS'], p2_data['TRB'], p2_data['AST'],
                            f"{p2_data['TS%']:.1%}", f"{p2_data['USG_approx']:.1f}%", p2_data['G']
                        ]
                    }
                    
                    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True)
            
            # 数据下载
            st.subheader("💾 数据导出")
            if st.button("导出处理后的数据为CSV"):
                csv = df_final.to_csv(index=False)
                st.download_button(
                    label="下载CSV",
                    data=csv,
                    file_name=f"nba_rookies_analysis_{selected_label.replace(' ', '_')}.csv",
                    mime="text/csv"
                )
    
    else:
        st.error("❌ 数据加载失败，请检查CSV链接配置")

if __name__ == "__main__":
    main()
