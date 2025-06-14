import requests
import redis
import schedule
import time
import os

# Redis配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

CURRENCY_API_KEY = os.environ.get('CURRENCY_API_KEY')

# API配置 
API_URL = "https://api.currencyapi.com/v3/latest?apikey=" + CURRENCY_API_KEY

def fetch_and_store_rates():
    try:
        # 发送API请求
        response = requests.get(API_URL)
        response.raise_for_status()  # 检查请求是否成功
        
        data = response.json()
        
        # 连接Redis
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True  # 自动将响应解码为字符串
        )
        
        # 存储/更新数据
        for currency, details in data['data'].items():
            # 使用currency code作为key, value作为值
            r.set(details['code'], details['value'])
            
        print(f"数据更新成功! 更新时间: {data['meta']['last_updated_at']}")
        
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {e}")
    except redis.RedisError as e:
        print(f"Redis操作失败: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")

def main():
    # 立即执行一次
    fetch_and_store_rates()
    
    # 每3小时执行一次
    schedule.every(3).hours.do(fetch_and_store_rates)
    
    # 保持程序运行
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次是否有待执行的任务

if __name__ == "__main__":
    main()
