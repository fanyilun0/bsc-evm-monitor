import os
import json
from dotenv import load_dotenv
from datetime import datetime
from logger import log, get_logger

# 加载环境变量
load_dotenv(override=True)

# 环境配置
ENV = os.getenv('ENV', 'dev').lower()  # dev 或 prod
IS_DEV = ENV == 'dev'
IS_PROD = ENV == 'prod'

# 初始化日志记录器
logger = get_logger(ENV)

# Etherscan V2 API 配置 - 支持多个API密钥
ETHERSCAN_API_KEYS_STR = os.getenv('ETHERSCAN_API_KEYS', '')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')

# 处理API密钥配置
if ETHERSCAN_API_KEYS_STR:
    # 支持多个API密钥，用逗号分隔
    try:
        ETHERSCAN_API_KEYS = [key.strip() for key in ETHERSCAN_API_KEYS_STR.split(',') if key.strip()]
        ETHERSCAN_API_KEY = ETHERSCAN_API_KEYS[0] if ETHERSCAN_API_KEYS else ''  # 使用第一个密钥作为默认值
        log(f'🔑 配置了 {len(ETHERSCAN_API_KEYS)} 个Etherscan API密钥')
        for i, key in enumerate(ETHERSCAN_API_KEYS, 1):
            log(f'  密钥 {i}: {key[:10]}...' if key else f'  密钥 {i}: 未设置')
    except Exception as e:
        log(f'❌ 解析API密钥配置失败: {e}')
        ETHERSCAN_API_KEYS = [ETHERSCAN_API_KEY] if ETHERSCAN_API_KEY else []
else:
    # 兼容单个API密钥配置
    ETHERSCAN_API_KEYS = [ETHERSCAN_API_KEY] if ETHERSCAN_API_KEY else []
    log(f'🔑 使用单个Etherscan API密钥: {ETHERSCAN_API_KEY[:10]}...' if ETHERSCAN_API_KEY else '❌ API密钥未设置')

API_URL_V2="https://api.etherscan.io/v2/api"

# 多链配置
CHAINS_CONFIG = {
    1: {
        'name': 'Ethereum Mainnet',
        'api_url': API_URL_V2,
        'explorer_url': 'https://etherscan.io',
        'enabled': True
    },
    56: {
        'name': 'BNB Smart Chain Mainnet',
        'api_url': API_URL_V2,
        'explorer_url': 'https://bscscan.com',
        'enabled': True
    },
    8453: {
        'name': 'Base Mainnet',
            'api_url': API_URL_V2,
        'explorer_url': 'https://basescan.org',
        'enabled': True
    }
}

# 默认链配置
DEFAULT_CHAIN_ID = 1  # Ethereum Mainnet
CHAIN_ID = int(os.getenv('CHAIN_ID', str(DEFAULT_CHAIN_ID)))
CHAIN_NAME = CHAINS_CONFIG.get(CHAIN_ID, {}).get('name', 'Unknown Chain')

# 获取当前链的API URL
def get_api_url(chain_id=None):
    """获取指定链的API URL"""
    if chain_id is None:
        chain_id = CHAIN_ID
    return CHAINS_CONFIG.get(chain_id, {}).get('api_url', API_URL_V2)

def get_explorer_url(chain_id=None):
    """获取指定链的浏览器URL"""
    if chain_id is None:
        chain_id = CHAIN_ID
    return CHAINS_CONFIG.get(chain_id, {}).get('explorer_url', 'https://etherscan.io')

def get_chain_name(chain_id=None):
    """获取指定链的名称"""
    if chain_id is None:
        chain_id = CHAIN_ID
    return CHAINS_CONFIG.get(chain_id, {}).get('name', 'Unknown Chain')

# 当前链的API URL
ETHERSCAN_API_URL = get_api_url(CHAIN_ID)

# Webhook 配置
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
log(f'🔗 Webhook URL: {WEBHOOK_URL}' if WEBHOOK_URL else '❌ Webhook URL未设置')

PROXY_URL = 'http://host.docker.internal:7890' if os.getenv('IS_DOCKER') else 'http://localhost:7890'
USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
log(f'🌐 代理设置: {"启用" if USE_PROXY else "禁用"}')
if PROXY_URL:
    log(f'🌐 代理URL: {PROXY_URL}')

# 监听配置 - 支持数组格式
MONITOR_ADDRESSES_STR = os.getenv('MONITOR_ADDRESSES', '[]')
try:
    MONITOR_ADDRESSES = json.loads(MONITOR_ADDRESSES_STR)
    if not isinstance(MONITOR_ADDRESSES, list):
        raise ValueError("MONITOR_ADDRESSES 必须是数组格式")
except json.JSONDecodeError:
    # 兼容字符串格式
    MONITOR_ADDRESSES = [addr.strip() for addr in MONITOR_ADDRESSES_STR.split(',') if addr.strip()]
    log(f'⚠️ 使用逗号分隔的地址格式，建议使用JSON数组格式')
except Exception as e:
    log(f'❌ 解析监控地址配置失败: {e}')
    MONITOR_ADDRESSES = []

# 输出监控地址配置
log(f'📍 监控地址配置:')
if MONITOR_ADDRESSES:
    log(f'   共配置 {len(MONITOR_ADDRESSES)} 个地址:')
    for i, addr in enumerate(MONITOR_ADDRESSES, 1):
        log(f'   {i}. {addr}')
else:
    log('   ❌ 未配置监控地址')

# 新代币数量阈值 (默认 1M = 1000000)
NEW_TOKEN_AMOUNT_THRESHOLD = int(os.getenv('NEW_TOKEN_AMOUNT_THRESHOLD', '1000000'))
log(f'💰 新代币数量阈值: {NEW_TOKEN_AMOUNT_THRESHOLD:,}')

# 检查间隔 (秒) - 默认10分钟
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '600'))
log(f'⏰ 检查间隔: {CHECK_INTERVAL} 秒 ({CHECK_INTERVAL // 60} 分钟)')

# 时间窗口配置 (分钟) - 只检查最近N分钟内的交易
TIME_WINDOW_MINUTES = int(os.getenv('TIME_WINDOW_MINUTES', '10'))
log(f'⏰ 时间窗口: 最近 {TIME_WINDOW_MINUTES} 分钟')

# API限制控制配置
MIN_REQUEST_INTERVAL = float(os.getenv('MIN_REQUEST_INTERVAL', '0.5'))  # 最小请求间隔（秒）
RATE_LIMIT_RETRY_DELAY = int(os.getenv('RATE_LIMIT_RETRY_DELAY', '5'))  # 遇到限制时的重试延迟（秒）
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))  # 最大重试次数
log(f'🔧 API限制控制: 最小间隔={MIN_REQUEST_INTERVAL}s, 重试延迟={RATE_LIMIT_RETRY_DELAY}s, 最大重试={MAX_RETRIES}次')

# 代币记录文件 - 按链ID分别存储
def get_token_records_file(chain_id=None):
    """获取指定链的代币记录文件名"""
    if chain_id is None:
        chain_id = CHAIN_ID
    return f'token_records_chain_{chain_id}.json'

TOKEN_RECORDS_FILE = get_token_records_file(CHAIN_ID)
log(f'📁 代币记录文件: {TOKEN_RECORDS_FILE}')

# 配置验证
log('\n🔍 配置验证:')
if not ETHERSCAN_API_KEYS:
    log('❌ 错误: 未配置Etherscan API密钥，请在.env文件中设置ETHERSCAN_API_KEYS')
if not MONITOR_ADDRESSES:
    log('❌ 错误: 未配置监控地址，请在.env文件中设置MONITOR_ADDRESSES')
if not WEBHOOK_URL:
    log('⚠️ 警告: 未配置Webhook URL，告警消息将无法发送')
if ETHERSCAN_API_KEYS and MONITOR_ADDRESSES:
    log('✅ 配置验证通过，可以启动监听器')

# 输出链信息
log(f'🔗 目标链: {CHAIN_NAME} (Chain ID: {CHAIN_ID})')
log(f'🔗 API URL: {ETHERSCAN_API_URL}')
log(f'🔗 Explorer URL: {get_explorer_url(CHAIN_ID)}')

# 输出支持的所有链
log(f'\n🌐 支持的链配置:')
for chain_id, config in CHAINS_CONFIG.items():
    status = "✅ 启用" if config['enabled'] else "❌ 禁用"
    log(f'{status} Chain ID {chain_id}: {config["name"]}') 