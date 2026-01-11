import pandas as pd
import numpy as np
from nba_api.stats.endpoints import playergamelog

def calculate_master_score(ma14, hype, price, pop):
    # 你的核心公式：Final Score = (MA14*100*(1+Hype)) / (Price * log(Pop+1))
    # 引入我们讨论过的异常过滤：Pop 底数设为 50
    adj_pop = max(pop, 50)
    numerator = ma14 * 100 * (1 + hype)
    denominator = price * np.log(adj_pop + 1)
    return round(numerator / denominator, 4)

def update_scores():
    df = pd.read_csv('data/cards_data.csv')
    for index, row in df.iterrows():
        # 1. 获取 NBA API MA14 数据
        # log = playergamelog.PlayerGameLog(player_id=row['id'], last_n_games=7)
        # ma14 = calculate_performance_index(log)
        
        # 2. 计算新分数
        new_score = calculate_master_score(row['ma14'], row['hype'], row['price'], row['pop'])
        df.at[index, 'final_score'] = new_score
    
    df.to_csv('data/cards_data.csv', index=False)
