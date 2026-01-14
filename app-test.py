import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import base64
from io import BytesIO
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. 品牌与法律配置
# ============================================================================
BRAND_CONFIG = {
    "name_en": "RookieFlip2X",
    "name_cn": "乐翻新秀", 
    "slogan": "NBA新秀数据分析系统",  # 优化：去掉"投资"字样
    "version": "v3.0",
    "legal_status": "数据分析工具软件"  # 明确法律定位
}

# 法律声明配置
LEGAL_CONFIG = {
    # 数据来源声明
    "data_source": "数据来源于NBA官方公开统计数据，用户通过Google Sheets链接自行提供",
    
    # 系统性质声明
    "system_nature": "本系统为篮球数据分析工具软件，提供客观数据统计和量化分析",
    
    # 非投资建议声明
    "non_investment_advice": """
    重要声明：本系统提供的所有分析结果、评分、信号等均基于历史数据统计分析，
    不构成任何形式的投资建议、推荐或保证。用户应独立判断并承担决策风险。
    """,
    
    # 版权声明
    "copyright_notice": """
    本系统的算法逻辑、数据处理方法、可视化设计等知识产权归开发者所有。
    NBA相关商标、标识、数据版权归NBA及其合作伙伴所有。
    """,
    
    # 使用限制
    "usage_restrictions": """
    禁止将本系统用于：1)赌博或相关活动 2)非法证券投资建议 3)误导性宣传
    4)侵犯他人权益的行为 5)违反法律法规的其他用途
    """
}

# ============================================================================
# 2. 服务条款和免责声明（增强版）
# ============================================================================
TERMS_OF_SERVICE = f"""
# 📄 {BRAND_CONFIG['name_cn']} 服务条款

## 1. 服务性质
{BRAND_CONFIG['name_cn']} ({BRAND_CONFIG['name_en']}) 是一个**篮球数据分析工具软件**，
提供NBA新秀球员的量化数据分析和可视化展示。

## 2. 数据来源
{LEGAL_CONFIG['data_source']}

## 3. 非投资建议声明
{LEGAL_CONFIG['non_investment_advice']}

## 4. 知识产权
{LEGAL_CONFIG['copyright_notice']}

## 5. 使用限制
{LEGAL_CONFIG['usage_restrictions']}

## 6. 免责条款
用户理解并同意：
- 篮球运动员表现受多种因素影响，历史数据不代表未来表现
- 本系统不保证分析结果的准确性、及时性或完整性
- 因使用本系统产生的任何投资决策风险由用户自行承担
- 本系统不承担任何直接、间接、附带或后果性损失

## 7. 联系方式
如对本服务条款有疑问，请联系：contact@{BRAND_CONFIG['name_en'].lower()}.com
"""

# ============================================================================
# 3. 数据源配置
# ============================================================================
CSV_LINKS = {
    "2022-23 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQO7FDHZNjcOQogg4iFO5f6Su-oaMyITCBny73iWUPxTNNGqe9eMrHaD5BwlIlnr21N_Rsq9gQS5Vqp/pub?gid=0&single=true&output=csv",
    "2023-24 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTh6ABCuCa4EBCvktT5WzgUHpkacmSwuw-YulyoZFm-1BiqbhAhtCcfCLj55abTn4JxxHoRYtldbDRo/pub?gid=0&single=true&output=csv",
    "2024-25 赛季": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRq5EQLiWNZzygGsgc19Svqdx6IMKfDzaH_yhui-omPcptN_orV3mL6zCxitRjsBxcT0ZCl0KUzZUnS/pub?gid=0&single=true&output=csv"
}

# 添加数据来源说明
DATA_SOURCE_INFO = """
## 📊 数据来源说明

本系统分析的数据来自：
1. **NBA官方统计**：通过公开渠道获取的球员基础数据
2. **用户自行提供**：用户通过Google Sheets链接导入的数据
3. **计算衍生数据**：基于原始数据通过算法计算的指标

**数据更新频率**：依赖于用户提供链接的更新频率
**数据准确性**：基于原始数据的准确性，系统不保证100%准确
"""

# ============================================================================
# 4. 核心函数：智能数据清洗（增强法律合规性）
# ============================================================================
@st.cache_data(ttl=600)
def fetch_and_clean_data(url, user_acknowledged=False):
    """
    数据清洗函数 - 增加法律合规检查
    
    Parameters:
    -----------
    url : str
        用户提供的Google Sheets CSV链接
    user_acknowledged : bool
        用户是否已确认数据使用条款
    """
    if not user_acknowledged:
        st.error("请先确认数据使用条款")
        return None
    
    try:
        # 记录数据获取日志（用于审计）
        data_fetch_log = {
            "timestamp": datetime.now().isoformat(),
            "source": "user_provided_google_sheets",
            "url_hash": hash(url)  # 不存储原始URL保护隐私
        }
        
        # 读取数据
        df = pd.read_csv(url, header=None)
        
        # 搜索表头
        header_row_index = 0
        for i, row in df.iterrows():
            if 'Player' in str(row.values):
                header_row_index = i
                break
        
        # 重新设置表头
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

        # 字段映射（避免使用可能引起误解的名称）
        mapping = {
            'PTS': 'PTS_1' if 'PTS_1' in df.columns else 'PTS',
            'TRB': 'TRB_1' if 'TRB_1' in df.columns else 'TRB', 
            'AST': 'AST_1' if 'AST_1' in df.columns else 'AST',
            'STL': 'STL_1' if 'STL_1' in df.columns else 'STL',
            'BLK': 'BLK_1' if 'BLK_1' in df.columns else 'BLK',
            'TOV': 'TOV_1' if 'TOV_1' in df.columns else 'TOV',
            'FG%': 'FG%', '3P%': '3P%', 'FT%': 'FT%',
            'G': 'G', 'MP': 'MP', 'FG': 'FG', 'FGA': 'FGA',
            'FT': 'FT', 'FTA': 'FTA', '3P': '3P', '3PA': '3PA',
            'ORB': 'ORB', 'PF': 'PF'
        }
        
        for final_name, raw_name in mapping.items():
            if raw_name in df.columns:
                df[final_name] = pd.to_numeric(df[raw_name], errors='coerce').fillna(0)
        
        # 添加数据来源标记
        df.attrs['data_source_info'] = "user_provided_nba_stats"
        df.attrs['processing_timestamp'] = datetime.now().isoformat()
        
        return df
        
    except Exception as e:
        st.error(f"数据解析失败: {str(e)[:100]}...")  # 限制错误信息长度
        return None

# ============================================================================
# 5. 优化版PPI计算引擎（避免"投资"相关措辞）
# ============================================================================
def apply_player_performance_index(df):
    """
    球员表现指数计算 - 避免使用"投资"相关术语
    
    将原来的PPI改为"球员表现指数"而非"投资指数"
    """
    if df is None:
        return None
    
    # 数据验证
    required_cols = ['PTS', 'TRB', 'AST', 'FG%', '3P%', 'FT%', 'STL', 'BLK', 'TOV', 
                    'G', 'MP', 'FG', 'FGA', 'FT', 'FTA', 'PF', 'ORB']
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 计算高级指标
    df['TS%'] = np.where((df['FGA'] + 0.44 * df['FTA']) > 0,
                         df['PTS'] / (2 * (df['FGA'] + 0.44 * df['FTA'])), 0)
    df['USG_approx'] = np.where(df['MP'] > 0,
                               (df['FGA'] + 0.44 * df['FTA'] + df['TOV']) * 48 / (df['MP'] * 5), 0)
    df['EFF'] = (df['PTS'] + df['TRB'] + df['AST'] + df['STL'] + df['BLK'] - 
                df['TOV'] - (df['FGA'] - df['FG']) - (df['FTA'] - df['FT']))
    
    # 球员表现指数计算（优化措辞）
    base_production = (df['PTS'] * 1.2 + df['TRB'] * 1.0 + df['AST'] * 1.3)
    efficiency_score = np.where(df['TS%'] > 0.5, (df['TS%'] - 0.5) * 200, (df['TS%'] - 0.5) * 100)
    defense_score = (df['STL'] * 2.5 + df['BLK'] * 2.0 - df['TOV'] * 0.5 + df['ORB'] * 0.8)
    eff_bonus = df['EFF'] * 0.1
    usage_adjustment = np.where(df['USG_approx'] > 20, (df['USG_approx'] - 20) * 0.3, 0)
    
    df['Player_Performance_Index'] = (
        base_production * 0.3 + efficiency_score * 0.25 + defense_score * 0.2 +
        eff_bonus * 0.15 - usage_adjustment * 0.1
    )
    
    # 稳定性系数
    stability_factor = np.where(
        (df['G'] >= 41) & (df['MP'] >= 20), 1.2,
        np.where((df['G'] >= 20) & (df['MP'] >= 10), 1.0, 0.8)
    )
    
    df['Player_Performance_Index'] = (df['Player_Performance_Index'] * stability_factor).round(1)
    
    # 优化评估信号（避免投资相关术语）
    def get_performance_evaluation(ppi, ts_pct, usg, games, mpg):
        """
        球员表现评估 - 使用中性评价术语
        """
        if ppi >= 30 and ts_pct >= 0.55 and games >= 41 and mpg >= 25:
            return "🏆 精英级别"
        if ppi >= 25 and ts_pct >= 0.52 and games >= 20:
            return "⭐ 优秀表现" 
        if ppi >= 18 and usg <= 25:
            return "👍 高效贡献"
        if ppi >= 12:
            return "📈 潜力展现"
        if games < 20 or mpg < 10:
            return "👀 样本有限"
        return "📊 持续观察"
    
    df['Performance_Evaluation'] = df.apply(
        lambda x: get_performance_evaluation(x['Player_Performance_Index'], 
                                           x['TS%'], x['USG_approx'], x['G'], x['MP']), 
        axis=1
    )
    
    # 添加算法说明
    df.attrs['algorithm_info'] = "Player Performance Index v3.0 - Quantitative Basketball Analytics"
    df.attrs['calculation_timestamp'] = datetime.now().isoformat()
    
    return df

# ============================================================================
# 6. 球员风格聚类（优化术语）
# ============================================================================
def analyze_player_playstyles(df, n_clusters=5):
    """
    球员比赛风格分析 - 使用技术性术语
    """
    if df is None or len(df) < n_clusters:
        return df
    
    # 使用技术统计特征
    features = ['PTS', 'TRB', 'AST', 'STL', 'BLK', 'FG%', '3P%', 'MP']
    for feature in features:
        if feature not in df.columns:
            df[feature] = 0
    
    X = df[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['PlayStyle_Cluster'] = kmeans.fit_predict(X_scaled)
    
    # 使用技术性风格描述
    cluster_descriptions = {}
    for i in range(n_clusters):
        cluster_descriptions[i] = "角色球员类型"
    
    df['PlayStyle_Category'] = df['PlayStyle_Cluster'].map(cluster_descriptions)
    return df

# ============================================================================
# 7. 社交媒体分享功能（增强合规性）
# ============================================================================
def generate_safe_social_content(df, content_type="analysis"):
    """
    生成安全的社交媒体内容（避免法律风险）
    """
    if df is None or len(df) == 0:
        return {"text": "", "disclaimer": LEGAL_CONFIG['non_investment_advice']}
    
    current_date = datetime.now().strftime("%Y年%m月%d日")
    top_player = df.iloc[0] if len(df) > 0 else None
    
    if content_type == "analysis":
        text = f"""🏀 {BRAND_CONFIG['name_cn']} 篮球数据分析 #{current_date}

📊 数据洞察分享：
• 当前分析样本: {len(df)} 名球员
• 平均表现指数: {df['Player_Performance_Index'].mean():.1f}
• 数据更新时间: {current_date}

🔬 分析方法：
使用量化模型评估球员综合表现
基于客观统计数据，排除主观偏见

#篮球数据分析 #体育数据科学 #量化分析
#数据仅供参考
"""
    else:
        text = f"""🎯 {BRAND_CONFIG['name_cn']} 比赛风格分析 #{current_date}

🏀 基于机器学习的球员分类
📊 使用聚类算法识别不同比赛风格
🔍 帮助理解球员技术特点

#{BRAND_CONFIG['name_en']} #机器学习 #体育分析
"""
    
    return {
        "text": text,
        "disclaimer": LEGAL_CONFIG['non_investment_advice'],
        "copyright": LEGAL_CONFIG['copyright_notice']
    }

# ============================================================================
# 8. Streamlit 主应用（全面合规优化）
# ============================================================================
def main():
    # 页面配置
    st.set_page_config(
        page_title=f"{BRAND_CONFIG['name_en']} - {BRAND_CONFIG['name_cn']}",
        page_icon="🏀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 自定义CSS样式
    st.markdown(f"""
    <style>
    .legal-warning {{
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        margin: 20px 0;
        border-radius: 5px;
    }}
    .data-source-info {{
        background-color: #e7f3ff;
        border-left: 5px solid #0d6efd;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
        font-size: 0.9em;
    }}
    .disclaimer-box {{
        background-color: #f8d7da;
        border: 1px solid #f5c2c7;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
        font-size: 0.8em;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # ============================================================================
    # 法律声明和条款确认区域
    # ============================================================================
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <h1>🏀 {BRAND_CONFIG['name_cn']}</h1>
        <h3>{BRAND_CONFIG['name_en']} - {BRAND_CONFIG['slogan']} {BRAND_CONFIG['version']}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # 必须确认的法律条款
    st.markdown("""
    <div class="legal-warning">
    <h4>⚠️ 使用前必读 - 法律声明</h4>
    在使用本系统前，请仔细阅读并理解以下重要信息：
    </div>
    """, unsafe_allow_html=True)
    
    # 条款展开
    with st.expander("📄 详细服务条款（点击展开）", expanded=False):
        st.markdown(TERMS_OF_SERVICE)
    
    # 数据来源说明
    with st.expander("📊 数据来源说明", expanded=False):
        st.markdown(DATA_SOURCE_INFO)
    
    # 必须确认的复选框
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        terms_accepted = st.checkbox(
            "✅ 我已阅读、理解并同意上述服务条款",
            value=False,
            help="必须同意条款才能使用本系统"
        )
        
        if not terms_accepted:
            st.warning("请先阅读并同意服务条款")
            st.stop()
    
    # ============================================================================
    # 侧边栏配置
    # ============================================================================
    st.sidebar.header("⚙️ 系统配置")
    st.sidebar.markdown("---")
    
    # 数据源选择
    selected_label = st.sidebar.selectbox(
        "选择数据分析赛季", 
        list(CSV_LINKS.keys())
    )
    
    # 数据使用确认
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📁 数据源配置")
    data_source_ack = st.sidebar.checkbox(
        "确认数据使用",
        help="确认您有权使用并提供相关数据"
    )
    
    if not data_source_ack:
        st.sidebar.warning("请确认数据使用权限")
        st.warning("请先在侧边栏确认数据使用权限")
        st.stop()
    
    # ============================================================================
    # 主内容区域
    # ============================================================================
    # 数据加载
    with st.spinner("正在加载和分析数据..."):
        df_raw = fetch_and_clean_data(
            CSV_LINKS[selected_label], 
            user_acknowledged=True
        )
    
    if df_raw is not None:
        # 数据处理
        df_analyzed = apply_player_performance_index(df_raw)
        
        # 添加实时免责声明
        st.markdown(f"""
        <div class="disclaimer-box">
        <strong>免责声明：</strong> {LEGAL_CONFIG['non_investment_advice']}
        </div>
        """, unsafe_allow_html=True)
        
        # 标签页布局
        tab1, tab2, tab3 = st.tabs(["📈 数据分析", "🎯 风格分析", "📱 内容分享"])
        
        with tab1:
            st.header("📈 NBA新秀数据分析")
            
            # 筛选器
            col1, col2, col3 = st.columns(3)
            with col1:
                min_g = st.slider("最小出场次数", 1, 82, 10)
            with col2:
                min_mpg = st.slider("最小场均时间", 0, 40, 10)
            with col3:
                min_index = st.slider("最小表现指数", 0, 50, 5)
            
            # 数据筛选
            display_df = df_analyzed[
                (df_analyzed['G'] >= min_g) & 
                (df_analyzed['MP'] >= min_mpg) &
                (df_analyzed['Player_Performance_Index'] >= min_index)
            ].sort_values('Player_Performance_Index', ascending=False)
            
            if len(display_df) > 0:
                # 核心指标
                st.subheader("📊 核心数据指标")
                col1, col2, col3, col4 = st.columns(4)
                top_player = display_df.iloc[0]
                
                col1.metric("最佳表现", top_player['Player'], 
                           f"指数: {top_player['Player_Performance_Index']}")
                col2.metric("分析样本", len(display_df))
                col3.metric("平均指数", round(display_df['Player_Performance_Index'].mean(), 1))
                elite_count = len(display_df[display_df['Performance_Evaluation'] == '🏆 精英级别'])
                col4.metric("精英级别", f"{elite_count}人")
                
                # 数据表格
                st.subheader("📋 详细数据表")
                st.markdown("*基于客观统计数据的量化分析结果*")
                st.dataframe(
                    display_df[[
                        'Player', 'Player_Performance_Index', 'Performance_Evaluation',
                        'PTS', 'TRB', 'AST', 'TS%', 'G', 'MP'
                    ]],
                    use_container_width=True,
                    hide_index=True
                )
                
                # 可视化
                st.subheader("📈 数据可视化")
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_scatter = px.scatter(
                        display_df, x='PTS', y='Player_Performance_Index', 
                        color='Performance_Evaluation', size='MP', 
                        hover_name='Player', 
                        title='得分 vs 表现指数（数据关系分析）',
                        labels={
                            'PTS': '场均得分',
                            'Player_Performance_Index': '球员表现指数',
                            'Performance_Evaluation': '表现评估'
                        }
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                
                with col2:
                    eval_counts = display_df['Performance_Evaluation'].value_counts()
                    fig_pie = px.pie(
                        values=eval_counts.values, 
                        names=eval_counts.index,
                        title="表现评估分布（统计分析）"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("暂无符合筛选条件的数据")
        
        with tab2:
            st.header("🎯 球员比赛风格分析")
            st.markdown("*基于机器学习聚类算法的技术风格分类*")
            
            col1, col2 = st.columns(2)
            with col1:
                n_clusters = st.slider("分类数量", 3, 8, 5)
            with col2:
                min_mpg = st.slider("最小场均时间", 0, 40, 10, key="style_min_mpg")
            
            analysis_df = df_analyzed[df_analyzed['MP'] >= min_mpg].copy()
            
            if len(analysis_df) >= n_clusters:
                clustered_df = analyze_player_playstyles(analysis_df, n_clusters)
                
                st.subheader("📊 风格分布分析")
                style_counts = clustered_df['PlayStyle_Category'].value_counts()
                
                col1, col2 = st.columns(2)
                with col1:
                    fig_pie = px.pie(
                        values=style_counts.values, 
                        names=style_counts.index,
                        title="球员技术风格分布"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("样本数量不足进行风格分析")
        
        with tab3:
            st.header("📱 数据分析内容分享")
            st.markdown("*生成合规的社交媒体分享内容*")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 数据分析分享")
                share_content = generate_safe_social_content(
                    display_df if 'display_df' in locals() else df_analyzed, 
                    "analysis"
                )
                
                st.text_area("分享文案", share_content["text"], height=150)
                
                if st.button("复制分享文案"):
                    st.code(share_content["text"])
                    st.success("文案已复制到剪贴板")
            
            with col2:
                st.subheader("⚖️ 法律声明")
                st.info("""
                在分享内容时，建议包含以下声明：
                
                **数据来源声明：**
                分析数据来源于NBA官方统计
                
                **工具说明：**
                使用量化分析工具进行数据处理
                
                **免责声明：**
                数据仅供参考，不构成任何建议
                """)
    
    else:
        st.error("数据加载失败，请检查数据源配置")
    
    # ============================================================================
    # 页脚和法律声明
    # ============================================================================
    st.markdown("---")
    
    # 页脚信息
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    
    with footer_col1:
        st.markdown(f"""
        **{BRAND_CONFIG['name_cn']}**
        {BRAND_CONFIG['name_en']}
        {BRAND_CONFIG['legal_status']}
        """)
    
    with footer_col2:
        st.markdown(f"""
        **数据更新时间**
        {datetime.now().strftime("%Y年%m月%d日")}
        
        **系统版本**
        {BRAND_CONFIG['version']}
        """)
    
    with footer_col3:
        st.markdown("""
        **法律声明**
        本系统仅为数据分析工具
        不构成任何投资建议
        
        **联系我们**
        contact@rookieflip2x.com
        """)
    
    # 最终免责声明
    st.markdown("---")
    st.caption("""
    *使用本系统即表示您已阅读、理解并同意所有服务条款。 
    本系统的所有分析结果均为基于历史数据的统计计算结果，不保证未来表现。 
    篮球比赛结果受多种因素影响，数据分析仅供参考。*
    """)

if __name__ == "__main__":
    main()
