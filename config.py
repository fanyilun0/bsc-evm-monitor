import os
import json
from dotenv import load_dotenv
from logger import log
import requests

# 是否已经输出过配置日志
_config_logged = False

# 加载环境变量
load_dotenv(override=True)

# Etherscan V2 API 配置 - 支持多个API密钥
ETHERSCAN_API_KEYS_STR = os.getenv('ETHERSCAN_API_KEYS', '')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')

# 处理API密钥配置
if ETHERSCAN_API_KEYS_STR:
    # 支持多个API密钥，用逗号分隔
    try:
        ETHERSCAN_API_KEYS = [key.strip() for key in ETHERSCAN_API_KEYS_STR.split(',') if key.strip()]
        ETHERSCAN_API_KEY = ETHERSCAN_API_KEYS[0] if ETHERSCAN_API_KEYS else ''  # 使用第一个密钥作为默认值
    except Exception as e:
        ETHERSCAN_API_KEYS = [ETHERSCAN_API_KEY] if ETHERSCAN_API_KEY else []
else:
    # 兼容单个API密钥配置
    ETHERSCAN_API_KEYS = [ETHERSCAN_API_KEY] if ETHERSCAN_API_KEY else []

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

PROXY_URL = 'http://host.docker.internal:7890' if os.getenv('IS_DOCKER') else 'http://localhost:7890'
USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'

# 监听配置 - 支持数组格式
MONITOR_ADDRESSES_STR = os.getenv('MONITOR_ADDRESSES', '[]')
try:
    MONITOR_ADDRESSES = json.loads(MONITOR_ADDRESSES_STR)
    if not isinstance(MONITOR_ADDRESSES, list):
        raise ValueError("MONITOR_ADDRESSES 必须是数组格式")
except json.JSONDecodeError:
    # 兼容字符串格式
    MONITOR_ADDRESSES = [addr.strip() for addr in MONITOR_ADDRESSES_STR.split(',') if addr.strip()]
except Exception as e:
    MONITOR_ADDRESSES = []

# 新代币数量阈值 (默认min = 1_000_000, max = 1_000_000_000)
NEW_TOKEN_AMOUNT_THRESHOLD_MIN = int(os.getenv('NEW_TOKEN_AMOUNT_THRESHOLD_MIN', '1_000_000'))
NEW_TOKEN_AMOUNT_THRESHOLD_MAX = int(os.getenv('NEW_TOKEN_AMOUNT_THRESHOLD_MAX', '1_000_000_000'))

CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))

# 时间窗口配置
TIME_WINDOW_MINUTES = CHECK_INTERVAL / 60 + 1

# API限制控制配置
MIN_REQUEST_INTERVAL = float(os.getenv('MIN_REQUEST_INTERVAL', '1'))  # 最小请求间隔（秒）
RATE_LIMIT_RETRY_DELAY = int(os.getenv('RATE_LIMIT_RETRY_DELAY', '5'))  # 遇到限制时的重试延迟（秒）
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '1'))  # 最大重试次数

# 代币记录文件 - 按链ID分别存储
def get_token_records_file(chain_id=None):
    """获取指定链的代币记录文件名"""
    if chain_id is None:
        chain_id = CHAIN_ID
    return f'token_records_chain_{chain_id}.json'

TOKEN_RECORDS_FILE = get_token_records_file(CHAIN_ID)

# Twitter API 配置
TWITTER_API_BASE_URL = os.getenv('TWITTER_API_BASE_URL', 'http://127.0.0.1:8000')
TWITTER_TWEET_ENDPOINT = os.getenv('TWITTER_TWEET_ENDPOINT', '/tweet')
TWITTER_SEARCH_ENDPOINT = os.getenv('TWITTER_SEARCH_ENDPOINT', '/search/user_tweets')
TWITTER_USERNAME = os.getenv('TWITTER_USERNAME', 'binance')
TWITTER_ENABLED = os.getenv('TWITTER_ENABLED', 'true').lower() == 'true'

# Config 类 - 为了兼容其他模块的使用
class Config:
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Twitter API 配置
    TWITTER_API_BASE_URL = TWITTER_API_BASE_URL
    TWITTER_TWEET_ENDPOINT = TWITTER_TWEET_ENDPOINT
    TWITTER_SEARCH_ENDPOINT = TWITTER_SEARCH_ENDPOINT
    TWITTER_USERNAME = TWITTER_USERNAME
    TWITTER_ENABLED = TWITTER_ENABLED

# 将日志输出分组到不同的函数中
def log_api_keys_config():
    """输出API密钥配置相关的日志"""
    if ETHERSCAN_API_KEYS_STR:
        log(f'🔑 配置了 {len(ETHERSCAN_API_KEYS)} 个Etherscan API密钥')
        for i, key in enumerate(ETHERSCAN_API_KEYS, 1):
            log(f'  密钥 {i}: {key[:10]}...' if key else f'  密钥 {i}: 未设置')
    else:
        log(f'🔑 使用单个Etherscan API密钥: {ETHERSCAN_API_KEY[:10]}...' if ETHERSCAN_API_KEY else '❌ API密钥未设置')

def log_proxy_config():
    """输出代理配置相关的日志"""
    log(f'🌐 代理设置: {"启用" if USE_PROXY else "禁用"}')
    if PROXY_URL:
        log(f'🌐 代理URL: {PROXY_URL}')

def log_monitor_addresses():
    """输出监控地址配置相关的日志"""
    log(f'📍 监控地址配置:')
    if MONITOR_ADDRESSES:
        log(f'   共配置 {len(MONITOR_ADDRESSES)} 个地址:')
        for i, addr in enumerate(MONITOR_ADDRESSES, 1):
            log(f'   {i}. {addr}')
    else:
        log('   ❌ 未配置监控地址')

def log_threshold_config():
    """输出阈值配置相关的日志"""
    log(f'💰 新代币数量阈值: {NEW_TOKEN_AMOUNT_THRESHOLD_MIN:,} - {NEW_TOKEN_AMOUNT_THRESHOLD_MAX:,}')
    log(f'⏰ 检查间隔: {CHECK_INTERVAL} 秒 ({CHECK_INTERVAL // 60} 分钟)')
    log(f'⏰ 时间窗口: 最近 {TIME_WINDOW_MINUTES} 分钟')

def log_api_limit_config():
    """输出API限制控制配置相关的日志"""
    log(f'🔧 API限制控制: 最小间隔={MIN_REQUEST_INTERVAL}s, 重试延迟={RATE_LIMIT_RETRY_DELAY}s, 最大重试={MAX_RETRIES}次')
    log(f'📁 代币记录文件: {TOKEN_RECORDS_FILE}')

def log_config_validation():
    """输出配置验证相关的日志"""
    if not ETHERSCAN_API_KEYS:
        log('❌ 错误: 未配置Etherscan API密钥，请在.env文件中设置ETHERSCAN_API_KEYS')
    if not MONITOR_ADDRESSES:
        log('❌ 错误: 未配置监控地址，请在.env文件中设置MONITOR_ADDRESSES')
    if not WEBHOOK_URL:
        log('⚠️ 警告: 未配置Webhook URL，告警消息将无法发送')

    # Twitter 推文发送开关状态
    log(f'🐦 推文发送功能: {"✅ 启用" if TWITTER_ENABLED else "❌ 禁用"}')

    # 警告仅使用默认Twitter API配置
    twitter_api_url = os.getenv('TWITTER_API_BASE_URL')
    if not twitter_api_url or twitter_api_url == 'http://127.0.0.1:8008':
        log('⚠️ 警告: 未配置自定义Twitter API URL，使用默认配置')
    if ETHERSCAN_API_KEYS and MONITOR_ADDRESSES:
        log('✅ 配置验证通过，可以启动监听器')

def log_chain_info():
    """输出链信息相关的日志"""
    log(f'🔗 目标链: {CHAIN_NAME} (Chain ID: {CHAIN_ID})')
    log(f'🔗 API URL: {ETHERSCAN_API_URL}')
    log(f'🔗 Explorer URL: {get_explorer_url(CHAIN_ID)}')

def log_supported_chains():
    """输出支持的所有链相关的日志"""
    log(f'🌐 支持的链配置:')
    for chain_id, config in CHAINS_CONFIG.items():
        status = "✅ 启用" if config['enabled'] else "❌ 禁用"
        log(f'{status} Chain ID {chain_id}: {config["name"]}')

def log_all_config():
    """输出所有配置相关的日志"""
    global _config_logged
    if _config_logged:
        return
    
    # 输出基本配置信息
    log_api_keys_config()
    log_proxy_config()
    log_chain_info()
    
    # 先测试Twitter API端点连接
    test_twitter_api_endpoint()
    
    # 输出其他配置信息
    log_monitor_addresses()
    log_threshold_config()
    log_api_limit_config()
    log_config_validation()
    log_supported_chains()
    
    _config_logged = True

def test_twitter_api_endpoint():
    """测试Twitter API端点连接"""
    try:
        log(f"🔍 测试连接Twitter API端点: {TWITTER_API_BASE_URL}")
        
        # 设置代理（如果启用）
        proxies = None
        if USE_PROXY and PROXY_URL:
            proxies = {
                "http": PROXY_URL,
                "https": PROXY_URL
            }
        
        # 设置超时
        timeout = 10
        
        # 请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 发送请求
        response = requests.get(
            TWITTER_API_BASE_URL, 
            proxies=proxies, 
            timeout=timeout,
            headers=headers
        )
        
        # 输出结果
        log(f"✅ Twitter API连接成功: 状态码 {response.status_code}")
        
        # 尝试解析JSON响应
        try:
            json_response = response.json()
            log(f"📄 Twitter API响应: {json.dumps(json_response, ensure_ascii=False)[:100]}..." 
                if len(json.dumps(json_response, ensure_ascii=False)) > 100 
                else f"📄 Twitter API响应: {json.dumps(json_response, ensure_ascii=False)}")
        except:
            # 如果不是JSON格式，输出文本
            log(f"📄 Twitter API响应内容: {response.text[:100]}..." 
                if len(response.text) > 100 
                else f"📄 Twitter API响应内容: {response.text}")
        
        # 检查其他端点
        log(f"🔍 Twitter API可用端点:")
        log(f"  - 推文端点: {TWITTER_API_BASE_URL}{TWITTER_TWEET_ENDPOINT}")
        log(f"  - 搜索端点: {TWITTER_API_BASE_URL}{TWITTER_SEARCH_ENDPOINT}")
        log(f"  - 默认用户: {TWITTER_USERNAME}")
        
        return response
    except Exception as e:
        log(f"❌ Twitter API连接失败: {str(e)}")
        if USE_PROXY:
            log(f"⚠️ 请检查代理设置是否正确: {PROXY_URL}")
        return None 