import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def fetch_market_data(player_name):
    options = Options()
    options.add_argument("--headless") # 无头模式
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    
    # 模拟搜索 130point (或 eBay)
    query = f"{player_name} Prizm Silver PSA 10"
    url = f"https://130point.com/cards/#/search?q={query}"
    driver.get(url)
    
    # 此处逻辑根据 2026 年网页 DOM 结构抓取最近 3 笔均价
    # 示例返回模拟数据
    price = 450.0  
    pop = 1200     
    driver.quit()
    return price, pop
