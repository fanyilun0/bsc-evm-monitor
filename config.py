import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# BSC 相关配置
BSC_API_KEY = os.getenv('BSC_API_KEY')
BSC_API_URL = 'https://api.bscscan.com/api'

# Webhook 配置
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PROXY_URL = os.getenv('PROXY_URL')
USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'

# 监听配置
MONITOR_ADDRESSES = os.getenv('MONITOR_ADDRESSES', '').split(',')
MONITOR_ADDRESSES = [addr.strip() for addr in MONITOR_ADDRESSES if addr.strip()]

# 指定代币合约地址 (用逗号分隔)
MONITOR_TOKENS = os.getenv('MONITOR_TOKENS', '').split(',')
MONITOR_TOKENS = [token.strip() for token in MONITOR_TOKENS if token.strip()]

# 监听的转入数额阈值 (原始数量，不考虑小数点)
TRANSFER_AMOUNT_THRESHOLD = os.getenv('TRANSFER_AMOUNT_THRESHOLD', '1000000000000000000')

# 检查间隔 (秒) - 默认10分钟
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '600'))

# 余额记录文件
BALANCE_FILE = 'balance_records.json' 