import os
import json
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

# 监听配置 - 支持数组格式
MONITOR_ADDRESSES_STR = os.getenv('MONITOR_ADDRESSES', '[]')
try:
    MONITOR_ADDRESSES = json.loads(MONITOR_ADDRESSES_STR)
except json.JSONDecodeError:
    # 兼容字符串格式
    MONITOR_ADDRESSES = [addr.strip() for addr in MONITOR_ADDRESSES_STR.split(',') if addr.strip()]

# 新代币数量阈值 (默认 1M = 1000000)
NEW_TOKEN_AMOUNT_THRESHOLD = int(os.getenv('NEW_TOKEN_AMOUNT_THRESHOLD', '1000000'))

# 检查间隔 (秒) - 默认10分钟
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '600'))

# 代币记录文件
TOKEN_RECORDS_FILE = 'token_records.json' 