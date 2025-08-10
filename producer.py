# producer.py - Alpha 事件测试数据生成器
# 生成符合 alpha.json 标准格式的测试事件并推送到 Redis 队列

import redis
import json
import time
import random
from datetime import datetime
from config import Config

# 连接到 Redis 服务
try:
    redis_config = {
        'host': Config.REDIS_HOST,
        'port': Config.REDIS_PORT,
        'db': Config.REDIS_DB,
        'decode_responses': True,
    }
    if Config.REDIS_PASSWORD:
        redis_config['password'] = Config.REDIS_PASSWORD
        
    r = redis.Redis(**redis_config)
    r.ping()
    print(f"成功连接到 Redis: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
except redis.exceptions.ConnectionError as e:
    print(f"无法连接到 Redis，请确保 Redis 服务正在运行: {e}")
    exit()
except Exception as e:
    print(f"配置错误: {e}")
    exit()

def generate_alpha_event():
    """生成符合 alpha.json 格式规范的测试事件"""
    
    # 示例代币数据
    test_tokens = [
        {
            "name": "Sidekick",
            "symbol": "K", 
            "contract": "0x0a73d885cdd66adf69c6d64c0609e55c527db2be"
        },
        {
            "name": "TestToken",
            "symbol": "TT",
            "contract": "0x1234567890abcdef1234567890abcdef12345678"
        },
        {
            "name": "AlphaToken", 
            "symbol": "ALPHA",
            "contract": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        }
    ]
    
    # 示例监控地址
    test_addresses = [
        "0x73D8bD54F7Cf5FAb43fE4Ef40A62D390644946Db",
        "0x742d35Cc7F3c6Ad14DD75E6e6b2e0c04aE5D5119", 
        "0x8888888888888888888888888888888888888888"
    ]
    
    # 随机选择代币和地址
    token = random.choice(test_tokens)
    address = random.choice(test_addresses)
    
    # 生成随机数量（超过阈值确保能触发告警）
    amount = random.randint(50000, 10000000)
    threshold = random.randint(10000, 50000)
    
    # 生成标准化的 alpha 事件
    event = {
        "type": "alpha_new_token",
        "chain": "BNB Smart Chain Mainnet", 
        "address": address,
        "name": token["name"],
        "symbol": token["symbol"],
        "amount": amount,
        "contract": token["contract"],
        "explorer": f"https://bscscan.com/token/{token['contract']}?a={address}",
        "threshold": threshold,
        "detected_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return event

if __name__ == "__main__":
    # 生成 alpha 事件
    alpha_event = generate_alpha_event()
    
    print("生成的 Alpha 事件:")
    print(json.dumps(alpha_event, indent=2, ensure_ascii=False))
    
    # 推送到监控队列（模拟 main.py 的输出）
    queue_name = getattr(Config, 'TWEET_QUEUE_NAME', 'monitor_queue')
    r.lpush(queue_name, json.dumps(alpha_event, ensure_ascii=False))
    
    print(f"\n✅ Alpha 事件已推送到队列: {queue_name}")
    print(f"🎯 代币: {alpha_event['name']} ({alpha_event['symbol']})")
    print(f"💰 数量: {alpha_event['amount']:,}")
    print(f"📍 地址: {alpha_event['address']}")
    print(f"🔗 浏览器: {alpha_event['explorer']}")

# ===================================================================

