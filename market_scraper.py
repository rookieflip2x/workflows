import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def get_market_data(player_list):
    """
    输入球员列表，返回价格和Pop数据
    """
    options = Options()
    # options.add_argument('--headless') # 初次调试建议注释掉，观察浏览器行为
    driver = webdriver.Chrome(options=options)
    results = []

    for player in player_list:
        try:
            print(f"正在查询: {player}...")
            # 访问 130point 搜索成交价
            search_query = f"2024 Prizm Silver {player} PSA 10"
            driver.get(f"https://130point.com/cards/")
            
            # 模拟搜索框输入 (此处需根据130point实际DOM结构调整选择器)
            time.sleep(3) # 等待加载
            search_box = driver.find_element(By.ID, "search_val") # 示例ID
            search_box.send_keys(search_query + Keys.ENTER)
            time.sleep(5)

            # 提取前3笔成交价数字
            price_elements = driver.find_elements(By.CLASS_NAME, "price")[:3]
            prices = [float(re.sub(r'[^\d.]', '', p.text)) for p in price_elements]
            avg_price = sum(prices) / len(prices) if prices else 0
            
            # 记录结果
            results.append({
                "PLAYER_NAME": player,
                "SILVER_PSA10_PRICE": avg_price,
                "PSA10_POP": 150 # 示例：Pop通常在搜索详情中，逻辑类似
            })
        except Exception as e:
            print(f"查询 {player} 失败: {e}")
            
    driver.quit()
    return pd.DataFrame(results)

# 使用示例
# if __name__ == "__main__":
#     players = ["Alex Sarr", "Chet Holmgren"]
#     market_df = get_market_data(players)
#     market_df.to_csv("market_fix.csv", index=False)
