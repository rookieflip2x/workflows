import pandas as pd
import numpy as np

def get_combined_quant_data():
    """
    合并逻辑：
    - data.csv: 云端自动抓取的 14 天表现均分
    - market_fix.csv: 你本地上传的银折 PSA 10 价格与 Pop
    """
    try:
        # 加载赛场数据
        perf_df = pd.read_csv("data.csv")
        # 加载市场数据
        market_df = pd.read_csv("market_fix.csv")
        
        # 以球员姓名为键值进行合并 (Left Join)
        combined = pd.merge(perf_df, market_df, on="PLAYER_NAME", how="left")
        
        # 清洗数据：防止空值导致计算错误
        combined['SILVER_PSA10_PRICE'] = pd.to_numeric(combined['SILVER_PSA10_PRICE'], errors='coerce').fillna(0)
        combined['PSA10_POP'] = pd.to_numeric(combined['PSA10_POP'], errors='coerce').fillna(0)
        
        # --- 核心模型分数计算 ---
        # 公式：(MA14均分 * 100) / (均价 * log(Pop + 1))
        # 使用 np.log1p (即 log(x+1)) 处理存世量，防止 Pop 为 0 时无限大
        combined['FINAL_SCORE'] = (
            (combined['MA14_INDEX'] * 100) / 
            (combined['SILVER_PSA10_PRICE'].replace(0, np.nan) * np.log1p(combined['PSA10_POP']))
        ).round(3)
        
        return combined.sort_values("FINAL_SCORE", ascending=False)
    except Exception as e:
        print(f"数据合并错误: {e}")
        return pd.DataFrame()
