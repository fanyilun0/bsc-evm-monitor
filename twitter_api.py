import aiohttp
import asyncio
import json
from datetime import datetime, timedelta
from logger import log
from config import (
    TWITTER_API_BASE_URL, 
    TWITTER_TWEET_ENDPOINT, 
    TWITTER_SEARCH_ENDPOINT, 
    TWITTER_USERNAME,
    PROXY_URL, 
    USE_PROXY
)
from webhook import send_message_async

async def send_tweet(content, in_reply_to_tweet_id=None, retry_count=0, max_retries=3):
    """发送推文
    
    Args:
        content (str): 推文内容
        in_reply_to_tweet_id (str, optional): 回复的推文ID
        retry_count (int): 当前重试次数
        max_retries (int): 最大重试次数
        
    Returns:
        dict: API响应
    """
    if not content:
        log("❌ 推文内容为空，跳过发送")
        return None
        
    endpoint = f"{TWITTER_API_BASE_URL}{TWITTER_TWEET_ENDPOINT}"
    headers = {'Content-Type': 'application/json'}
    proxy = PROXY_URL if USE_PROXY else None
    
    # 构建请求数据
    payload = {"content": content}
    if in_reply_to_tweet_id:
        # 确保tweet_id是字符串类型
        payload["in_reply_to_tweet_id"] = str(in_reply_to_tweet_id)
    
    if in_reply_to_tweet_id:
        log(f"🔄 回复推文ID: {in_reply_to_tweet_id}")
    else:
        log(f"🐦 发送推文: {content[:30]}..." if len(content) > 30 else f"🐦 发送推文: {content}")

    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers, proxy=proxy) as response:
                if response.status == 200:
                    response_data = await response.json()
                    log(f"✅ 推文发送成功!")
                    return response_data
                else:
                    error_text = await response.text()
                    log(f"❌ 推文发送失败: 状态码 {response.status}, 错误: {error_text}")
                    
                    # 如果是服务器错误(5xx)，尝试重试
                    if 500 <= response.status < 600 and retry_count < max_retries:
                        retry_delay = 2 ** retry_count  # 指数退避
                        log(f"⏳ {retry_delay}秒后进行第{retry_count + 1}次重试...")
                        await asyncio.sleep(retry_delay)
                        return await send_tweet(content, in_reply_to_tweet_id, retry_count + 1, max_retries)
                    return None
                    
    except asyncio.TimeoutError:
        log(f"⏰ 推文发送超时")
        if retry_count < max_retries:
            retry_delay = 2 ** retry_count  # 指数退避
            log(f"⏳ {retry_delay}秒后进行第{retry_count + 1}次重试...")
            await asyncio.sleep(retry_delay)
            return await send_tweet(content, in_reply_to_tweet_id, retry_count + 1, max_retries)
        return None
    except Exception as e:
        log(f"❌ 推文发送请求异常: {str(e)}")
        if retry_count < max_retries:
            retry_delay = 2 ** retry_count  # 指数退避
            log(f"⏳ {retry_delay}秒后进行第{retry_count + 1}次重试...")
            await asyncio.sleep(retry_delay)
            return await send_tweet(content, in_reply_to_tweet_id, retry_count + 1, max_retries)
        return None

async def search_user_tweets(username, keywords, max_results=10, retry_count=0, max_retries=3):
    """搜索用户推文
    
    Args:
        username (str): 用户名
        keywords (str): 关键词
        max_results (int, optional): 最大结果数
        retry_count (int): 当前重试次数
        max_retries (int): 最大重试次数
        
    Returns:
        list: 推文列表
    """
    endpoint = f"{TWITTER_API_BASE_URL}{TWITTER_SEARCH_ENDPOINT}"
    params = {
        "username": username,
        "keywords": keywords,
        "max_results": max_results
    }
    headers = {'Content-Type': 'application/json'}
    proxy = PROXY_URL if USE_PROXY else None
    
    log(f"🔍 搜索推文: 用户={username}, 关键词={keywords}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(endpoint, params=params, headers=headers, proxy=proxy) as response:
                if response.status == 200:
                    return await response.json()

                else:
                    error_text = await response.text()
                    log(f"❌ 搜索推文失败: 状态码 {response.status}, 错误: {error_text}")
                    
                    # 如果是服务器错误(5xx)，尝试重试
                    if 500 <= response.status < 600 and retry_count < max_retries:
                        retry_delay = 2 ** retry_count  # 指数退避
                        log(f"⏳ {retry_delay}秒后进行第{retry_count + 1}次重试...")
                        await asyncio.sleep(retry_delay)
                        return await search_user_tweets(username, keywords, max_results, retry_count + 1, max_retries)
                    return []
                    
    except asyncio.TimeoutError:
        log(f"⏰ 搜索推文超时")
        if retry_count < max_retries:
            retry_delay = 2 ** retry_count  # 指数退避
            log(f"⏳ {retry_delay}秒后进行第{retry_count + 1}次重试...")
            await asyncio.sleep(retry_delay)
            return await search_user_tweets(username, keywords, max_results, retry_count + 1, max_retries)
        return []
    except Exception as e:
        log(f"❌ 搜索推文请求异常: {str(e)}")
        if retry_count < max_retries:
            retry_delay = 2 ** retry_count  # 指数退避
            log(f"⏳ {retry_delay}秒后进行第{retry_count + 1}次重试...")
            await asyncio.sleep(retry_delay)
            return await search_user_tweets(username, keywords, max_results, retry_count + 1, max_retries)
        return []

def is_tweet_recent(created_at_str, days=7):
    """检查推文是否在指定天数内发布
    
    Args:
        created_at_str (str): 推文发布时间字符串
        days (int): 检查天数，默认7天
        
    Returns:
        bool: 是否在指定时间内
    """
    try:
        # 解析推文时间 (假设格式为 ISO 8601: 2025-09-23T13:02:21+00:00)
        if created_at_str:
            # 移除时区信息进行简单比较，或者使用更复杂的时区处理
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            
            # 获取当前时间 (UTC)
            now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
            
            # 计算时间差
            time_diff = now - created_at
            
            # 检查是否在指定天数内
            is_recent = time_diff.days <= days
            
            log(f"📅 推文时间检查: 发布于 {created_at_str}, {time_diff.days} 天前, {'✅ 时效内' if is_recent else '❌ 已过期'}")
            return is_recent
    except Exception as e:
        log(f"❌ 推文时间解析失败: {e}, 原始时间: {created_at_str}")
        # 如果解析失败，保守地返回False，不发送推文
        return False
    
    return False

async def process_token_event(token_info):
    """处理代币事件，搜索相关推文并发送回复
    
    Args:
        token_info (dict): 代币信息
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 提取代币名称作为关键词
        token_name = token_info.get('name', '')
        token_symbol = token_info.get('symbol', '')
        
        # 检查代币信息是否有效
        if (not token_name or token_name == 'Unknown' or token_name == 'Unknown Token') and \
           (not token_symbol or token_symbol == 'Unknown'):
            log(f"⚠️ 代币信息无效，仅发送新推文")
            # 构建推文内容
            tweet_content = generate_token_tweet(token_info)
            if tweet_content:
                # 发送新推文
                result = await send_tweet(tweet_content)
                return result is not None
            return False
            
        # 优先使用代币符号作为关键词
        search_keyword = token_symbol if token_symbol and token_symbol != 'Unknown' else token_name
        if not search_keyword:
            log(f"⚠️ 无法获取有效的代币关键词，仅发送新推文")
            # 构建推文内容
            tweet_content = generate_token_tweet(token_info)
            if tweet_content:
                # 发送新推文
                result = await send_tweet(tweet_content)
                return result is not None
            return False
        
        # 拼接 alpha 关键字来限制查询的推文
        search_keyword_with_alpha = f"{search_keyword} alpha"
        log(f"🔍 使用关键词 '{search_keyword_with_alpha}' 搜索 {TWITTER_USERNAME} 的推文")
        
        # 搜索相关推文
        tweets = await search_user_tweets(TWITTER_USERNAME, search_keyword_with_alpha)
        
        if not tweets:
            log(f"⚠️ 未找到关于 '{search_keyword_with_alpha}' 的推文，仅发送新推文")
            # 构建推文内容
            tweet_content = generate_token_tweet(token_info)
            # 发送新推文
            result = await send_tweet(tweet_content)
            return result is not None
        
        await send_message_async(f"🔍 搜索到 {len(tweets)} 条推文")

        # 过滤出最近一周内的推文
        recent_tweets = []
        for tweet in tweets:
            created_at = tweet.get('created_at')
            if created_at and is_tweet_recent(created_at):
                recent_tweets.append(tweet)
                log(f"✅ 保留时效内推文: {tweet.get('text', '')[:50]}...")
            else:
                log(f"❌ 过滤过期推文: {tweet.get('text', '')[:50]}...")
        
        # 如果没有时效内的推文，只发送新推文
        if not recent_tweets:
            log(f"⚠️ 没有时效内的推文，仅发送新推文")
            tweet_content = generate_token_tweet(token_info)
            # 发送新推文
            result = await send_tweet(tweet_content)
            return result is not None

        await send_message_async(f"✅ 筛选后剩余 {len(recent_tweets)} 条时效内推文")

        # 构建推文内容
        tweet_content = generate_token_tweet(token_info)
        success_count = 0
        total_attempts = len(recent_tweets) + 1  # 包括新推文
        
        # 先发送一条普通推文
        if await send_tweet(tweet_content):
            success_count += 1
        
        # 对每条找到的时效内推文发送回复
        for tweet in recent_tweets:
            tweet_id = tweet.get('id')
            if tweet_id:
                # 发送回复
                if await send_tweet(tweet_content, in_reply_to_tweet_id=tweet_id):
                    success_count += 1
                # 避免频率限制
                await asyncio.sleep(1)
        
        # 如果至少有一条推文发送成功，就认为处理成功
        success_rate = success_count / total_attempts
        log(f"📊 推文发送成功率: {success_count}/{total_attempts} ({success_rate:.0%})")
        return success_count > 0
        
    except Exception as e:
        log(f"❌ 处理代币事件失败: {str(e)}")
        return False

def generate_token_tweet(token_info):
    """生成关于代币的推文内容
    
    Args:
        token_info (dict): 代币信息
        
    Returns:
        str: 推文内容
    """
    # 读取模板文件
    try:
        with open('template.txt', 'r', encoding='utf-8') as f:
            template = f.read()
    except Exception as e:
        log(f"❌ 读取模板文件失败: {e}")
        template = """🚨 监测到币安Alpha分发钱包收到新代币！

📍 地址: {address}
🆕 代币: {name} (${symbol})
📦 数量: {amount}
📜 合约: {contract}
⛓️ 链: {chain}
🔎 浏览器: {explorer}

⚠️ 首次出现上述代币，请注意风险！
#BinanceAlpha #Airdrop #Wallet"""
    
    # 准备模板变量
    name = token_info.get('name', 'Unknown')
    symbol = token_info.get('symbol', 'Unknown')
    amount = token_info.get('amount', 0)
    address = token_info.get('address', 'Unknown')
    contract = token_info.get('contract', 'Unknown')
    chain = token_info.get('chain', 'Unknown Chain')
    explorer = token_info.get('explorer', '')
    
    # 格式化数字
    amount_str = f"{amount:,}"
    
    # 使用模板生成内容
    try:
        tweet_content = template.format(
            address=address,
            name=name,
            symbol=symbol,
            amount=amount_str,
            contract=contract,
            chain=chain,
            explorer=explorer or f"https://etherscan.io/token/{contract}"
        )
        return tweet_content
    except Exception as e:
        log(f"❌ 生成推文内容失败: {e}")
        return None
