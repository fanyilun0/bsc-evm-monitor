import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime, timedelta
from config import (
    ETHERSCAN_API_KEYS, MONITOR_ADDRESSES,
    NEW_TOKEN_AMOUNT_THRESHOLD, CHECK_INTERVAL, 
    PROXY_URL, USE_PROXY, CHAIN_ID,
    CHAINS_CONFIG, get_api_url, get_explorer_url, get_chain_name, get_token_records_file,
    MIN_REQUEST_INTERVAL, RATE_LIMIT_RETRY_DELAY, MAX_RETRIES, TIME_WINDOW_MINUTES
)
from logger import log
from webhook import send_message_async
import os

import json
from twitter_api import process_token_event

class NewTokenMonitor:
    def __init__(self, chain_id=None):
        self.chain_id = chain_id or CHAIN_ID
        self.chain_name = get_chain_name(self.chain_id)
        self.api_url = get_api_url(self.chain_id)
        self.explorer_url = get_explorer_url(self.chain_id)
        self.session = None
        self.token_records = self.load_token_records()
        self.proxy = PROXY_URL if USE_PROXY else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.api_keys = ETHERSCAN_API_KEYS
        
        # API限制控制
        self.last_request_time = 0
        self.min_request_interval = MIN_REQUEST_INTERVAL
        self.rate_limit_retry_delay = RATE_LIMIT_RETRY_DELAY
        self.max_retries = MAX_RETRIES
        
        # 时间窗口配置（分钟）
        self.time_window_minutes = TIME_WINDOW_MINUTES
        
        log(f"🔗 初始化监听器 - 链: {self.chain_name} (ID: {self.chain_id})")
        log(f"🔗 API URL: {self.api_url}")
        log(f"🔗 Explorer URL: {self.explorer_url}")
        log(f"⏰ 时间窗口: 最近 {self.time_window_minutes} 分钟")
    
    def generate_alpha_event(self, qualified_token):
        """生成符合 alpha.json 格式的事件数据"""
        try:
            # 确保地址字段存在
            address = qualified_token.get('address', 'Unknown')
            contract = qualified_token.get('contract', 'Unknown')
            token_name = qualified_token.get('token', 'Unknown Token')
            amount = qualified_token.get('amount', 0)
            
            # 从 token 字段解析名称和符号
            # 格式通常为 "TokenName (SYMBOL)"
            if '(' in token_name and ')' in token_name:
                name_part = token_name.split('(')[0].strip()
                symbol_part = token_name.split('(')[1].split(')')[0].strip()
            else:
                name_part = token_name
                symbol_part = 'Unknown'
            
            # 生成浏览器链接
            explorer_link = f"{self.explorer_url}/token/{contract}?a={address}"
            
            # 构建 alpha 事件
            alpha_event = {
                "type": "alpha_new_token",
                "chain": self.chain_name,
                "address": address,
                "name": name_part,
                "symbol": symbol_part,
                "amount": amount,
                "contract": contract,
                "explorer": explorer_link,
                "threshold": NEW_TOKEN_AMOUNT_THRESHOLD,
                "detected_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return alpha_event
        except Exception as e:
            log(f"❌ 生成 Alpha 事件失败: {e}")
            return None
    
    async def process_alpha_event(self, qualified_token):
        """处理符合条件的代币事件（调用Twitter API）"""
        try:
            # 生成 alpha 事件数据
            alpha_event = self.generate_alpha_event(qualified_token)
            if not alpha_event:
                log("❌ 生成 Alpha 事件失败")
                return False
            
            log(f"🚀 开始处理 Alpha 事件:")
            log(f"   代币: {alpha_event['name']} ({alpha_event['symbol']})")
            log(f"   数量: {alpha_event['amount']}")
            log(f"   地址: {alpha_event['address']}")
            log(f"   合约: {alpha_event['contract']}")
            
            # 使用Twitter API处理事件
            success = await process_token_event(alpha_event)
            
            if success:
                log(f"✅ Alpha 事件处理成功，已发送推文")
            else:
                log(f"⚠️ Alpha 事件处理失败或未找到相关推文")
            
            return success
        except Exception as e:
            log(f"❌ 处理 Alpha 事件失败: {e}")
            return False
    

        
    def load_token_records(self):
        """加载代币记录 - 新格式，按链ID分别存储"""
        records_file = get_token_records_file(self.chain_id)
        try:
            with open(records_file, 'r') as f:
                data = json.load(f)
                log(f"📂 加载代币记录文件: {records_file}, {len(data)} 个地址")
                
                # 验证数据格式
                if not isinstance(data, dict):
                    log("⚠️ 代币记录文件格式错误，使用空数据")
                    return {}
                
                # 检查每个地址的数据格式
                for address, tokens in data.items():
                    if not isinstance(tokens, list):
                        log(f"⚠️ 地址 {address} 的代币数据格式错误，重置为空列表")
                        data[address] = []
                        continue
                    
                    # 验证每个代币对象
                    valid_tokens = []
                    for token in tokens:
                        if isinstance(token, dict) and 'contract' in token:
                            # 确保所有必需字段都存在
                            token_obj = {
                                'token': token.get('token', 'Unknown'),
                                'contract': token['contract'],
                                'number': token.get('number', 0)
                            }
                            valid_tokens.append(token_obj)
                        else:
                            log(f"⚠️ 跳过无效的代币数据: {token}")
                    
                    data[address] = valid_tokens
                
                return data
                
        except FileNotFoundError:
            log(f"📂 代币记录文件不存在: {records_file}，将创建新文件")
            return {}
        except json.JSONDecodeError as e:
            log(f"❌ 代币记录文件JSON格式错误: {e}")
            return {}
        except Exception as e:
            log(f"❌ 加载代币记录文件失败: {e}")
            return {}
    
    def save_token_records(self):
        """保存代币记录"""
        records_file = get_token_records_file(self.chain_id)
        with open(records_file, 'w') as f:
            json.dump(self.token_records, f, indent=2)
    
    def get_random_api_key(self):
        """随机获取一个API密钥"""
        if not self.api_keys:
            return None
        return random.choice(self.api_keys)
    
    async def wait_for_rate_limit(self):
        """等待API限制，确保请求间隔"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def make_api_request(self, params, retry_count=0):
        """发送API请求，带重试和限制处理"""
        await self.wait_for_rate_limit()
        
        # 每次请求都随机选择API密钥
        current_key = self.get_random_api_key()
        if not current_key:
            log("❌ 没有可用的API密钥")
            return None
        
        params['apikey'] = current_key
        
        # 提取API调用信息用于日志
        module = params.get('module', 'unknown')
        action = params.get('action', 'unknown')
        chain_id = params.get('chainid', self.chain_id)
        
        log(f"🔗 请求URL: {self.api_url}")
        log(f"📋 请求参数: {params}")
        log(f"🔑 使用API密钥: {current_key[:10]}...")
        log(f"🌐 Etherscan API调用: module={module}, action={action}, chain_id={chain_id}")
        
        try:
            async with self.session.get(self.api_url, params=params, proxy=self.proxy, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 检查API限制
                    if data.get('status') == '0' and 'rate limit' in data.get('result', '').lower():
                        log(f"⚠️ 遇到API限制: {data.get('result')} (module={module}, action={action})")
                        
                        if retry_count < self.max_retries:
                            log(f"🔄 等待 {self.rate_limit_retry_delay} 秒后重试...")
                            await asyncio.sleep(self.rate_limit_retry_delay)
                            
                            # 增加重试延迟
                            self.rate_limit_retry_delay = min(self.rate_limit_retry_delay * 2, 30)
                            
                            return await self.make_api_request(params, retry_count + 1)
                        else:
                            log(f"❌ 达到最大重试次数，API请求失败 (module={module}, action={action})")
                            return None
                    
                    # 检查API密钥无效
                    if data.get('status') == '0' and 'invalid api key' in data.get('result', '').lower():
                        log(f"⚠️ API密钥无效: {data.get('result')} (module={module}, action={action})")
                        if retry_count < self.max_retries:
                            log(f"🔄 重试使用不同的API密钥...")
                            return await self.make_api_request(params, retry_count + 1)
                        else:
                            log(f"❌ 所有API密钥尝试失败 (module={module}, action={action})")
                            return None
                    
                    return data
                else:
                    response_text = await response.text()
                    log(f"❌ API响应状态码错误: {response.status} (module={module}, action={action})")
                    log(f"❌ 错误响应内容: {response_text}")
                    return None
                    
        except Exception as e:
            log(f"❌ API请求失败: {e} (module={module}, action={action})")
            import traceback
            traceback.print_exc()
            return None

    async def get_block_by_timestamp(self, timestamp):
        """根据时间戳获取最接近的区块号"""
        log(f"🔍 根据时间戳获取区块号: {timestamp}")
        log(f"📅 目标时间: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        
        params = {
            'chainid': self.chain_id,
            'module': 'block',
            'action': 'getblocknobytime',
            'timestamp': int(timestamp),
            'closest': 'before',
        }
        
        log(f"🌐 调用Etherscan API: block.getblocknobytime - 获取时间戳对应的区块号")
        data = await self.make_api_request(params)
        if data and data.get('status') == '1':
            block_number = int(data.get('result', 0))
            log(f"📊 时间戳 {timestamp} 对应区块号: {block_number}")
            return block_number
        else:
            log(f"❌ 根据时间戳获取区块号失败")
            return None

    async def get_latest_block_number(self):
        """获取最新区块号"""
        log(f"🔍 获取最新区块号...")
        
        params = {
            'chainid': self.chain_id,
            'module': 'proxy',
            'action': 'eth_blockNumber',
        }
        
        log(f"🌐 调用Etherscan API: proxy.eth_blockNumber - 获取最新区块号")
        data = await self.make_api_request(params)
        if data and data.get('result'):
            try:
                # 结果是十六进制格式，需要转换为十进制
                latest_block = int(data['result'], 16)
                log(f"📊 最新区块号: {latest_block}")
                return latest_block
            except ValueError as e:
                log(f"❌ 解析最新区块号失败: {e}, 原始结果: {data.get('result')}")
                return None
        else:
            log(f"❌ 获取最新区块号失败")
            return None

    async def estimate_block_by_time(self, minutes_ago):
        """根据时间估算区块号 - 严格使用时间戳API"""
        # 计算目标时间戳
        target_time = datetime.now() - timedelta(minutes=minutes_ago)
        target_timestamp = int(target_time.timestamp())
        
        # 使用时间戳API获取区块号
        return await self.get_block_by_timestamp(target_timestamp)
    
    async def get_recent_erc20_tokens(self, address, minutes_ago=None):
        """获取地址在指定时间窗口内的ERC20代币交易记录"""
        if minutes_ago is None:
            minutes_ago = self.time_window_minutes
            
        log(f"🔍 获取 {address} 最近 {minutes_ago} 分钟的ERC20代币交易记录...")
        
        # 获取时间范围对应的区块范围
        start_block = await self.estimate_block_by_time(minutes_ago)
        latest_block = 99999999999
        
        params = {
            'chainid': self.chain_id,
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': start_block,
            'endblock': latest_block,
            'page': 1,
            'offset': 10000,  # 最多10000笔交易
            'sort': 'desc',
        }
        
        log(f"📊 查询区块范围: {start_block} - {latest_block}")
        log(f"🌐 调用Etherscan API: account.tokentx - 获取地址的代币转账记录")
        log(f"📍 目标地址: {address}")
        log(f"⏰ 时间窗口: 最近 {minutes_ago} 分钟")
        
        data = await self.make_api_request(params)
        if data and data.get('status') == '1':
            transactions = data.get('result', [])
            log(f"📈 获取到 {len(transactions)} 笔最近交易记录")
            
            if not transactions:
                log(f"📊 最近 {minutes_ago} 分钟内没有代币交易")
                return []
            
            # 提取唯一的代币合约地址
            token_info = {}
            recent_contracts = set()
            
            for tx in transactions:
                contract = tx.get('contractAddress')
                if contract and contract.lower() not in token_info:
                    # 获取代币基本信息
                    token_name = tx.get('tokenName', 'Unknown')
                    token_symbol = tx.get('tokenSymbol', 'Unknown')
                    
                    # 记录最近交易涉及的合约
                    recent_contracts.add(contract.lower())
                    
                    # 确保数据格式正确
                    token_obj = {
                        'token': f"{token_name} ({token_symbol})" if token_name != 'Unknown' else 'Unknown',
                        'contract': contract.lower(),
                        'number': 0,  # 余额稍后获取
                        'recent_activity': True  # 标记为最近有活动
                    }
                    
                    # 验证数据完整性
                    if all(key in token_obj for key in ['token', 'contract', 'number']):
                        token_info[contract.lower()] = token_obj
                    else:
                        log(f"⚠️ 跳过不完整的代币数据: {token_obj}")
            
            result = list(token_info.values())
            log(f"🎯 最近 {minutes_ago} 分钟内发现 {len(result)} 个代币有交易活动")
            log(f"📝 涉及合约: {list(recent_contracts)[:5]}{'...' if len(recent_contracts) > 5 else ''}")
            return result
        else:
            log(f"❌ 获取最近代币交易失败，跳过此地址")
            return []
    
    async def get_token_balance(self, address, token_contract):
        """获取指定地址的代币余额"""
        params = {
            'chainid': self.chain_id,
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': token_contract,
            'address': address,
            'tag': 'latest',
        }
        
        log(f"💰 获取代币余额 - 地址: {address}, 代币: {token_contract}")
        log(f"🌐 调用Etherscan API: account.tokenbalance - 获取代币余额")
        
        data = await self.make_api_request(params)
        if data and data.get('status') == '1':
            balance = int(data.get('result', 0))
            log(f"💰 代币余额: {token_contract[:10]}... = {balance}")
            return balance
        else:
            log(f"⚠️ 获取余额失败")
            return 0
    
    async def get_token_info_simple(self, token_contract):
        """仅通过tokentx接口获取代币信息"""
        log(f"🔍 获取代币详细信息: {token_contract}")
        log(f"🌐 调用Etherscan API: account.tokentx - 获取代币基本信息")
        
        params = {
            'chainid': self.chain_id,
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': token_contract,
            'page': 1,
            'offset': 1,
            'sort': 'desc',
        }
        
        data = await self.make_api_request(params)
        if data and data.get('status') == '1' and data.get('result'):
            tx = data['result'][0]
            token_name = tx.get('tokenName', 'Unknown')
            token_symbol = tx.get('tokenSymbol', 'Unknown')
            token_decimals = int(tx.get('tokenDecimal', 18))
            log(f"✅ 代币信息: 名称={token_name}, 符号={token_symbol}, 精度={token_decimals}")
            return token_name, token_symbol, token_decimals
        else:
            log(f"❌ 获取代币交易记录失败，无法获取代币信息")
            return 'Unknown', 'Unknown', 18
    
    def format_token_amount(self, amount, decimals):
        """格式化代币数量 - 修复精度显示问题"""
        formatted = amount / (10 ** decimals)
        # 如果是整数，不显示小数点
        if formatted == int(formatted):
            return int(formatted)
        # 否则显示适当的小数位数
        return formatted
    
    async def check_new_tokens(self, address):
        """检查地址的新代币 - 基于最近时间窗口内的交易"""
        log(f"🔍 检查地址 {address} 的代币...")
        
        # 获取最近时间窗口内有活动的代币
        recent_tokens = await self.get_recent_erc20_tokens(address)
        log(f"🔍 最近活动代币数据类型: {type(recent_tokens)}, 长度: {len(recent_tokens) if recent_tokens else 0}")
        
        # 获取上次记录的代币
        previous_tokens = self.token_records.get(address, [])
        log(f"🔍 上次记录代币数据类型: {type(previous_tokens)}, 长度: {len(previous_tokens)}")
        
        # 提取上次记录的合约地址集合
        try:
            previous_contracts = {token['contract'] for token in previous_tokens}
            log(f"🔍 上次记录合约地址集合: {len(previous_contracts)} 个")
        except Exception as e:
            log(f"❌ 创建合约地址集合失败: {e}")
            log(f"🔍 上次记录代币数据: {previous_tokens}")
            previous_contracts = set()
        
        # 找出新代币（比较合约地址）- 只考虑最近有活动的代币
        new_tokens = []
        try:
            for token in recent_tokens:
                if isinstance(token, dict) and 'contract' in token:
                    if token['contract'] not in previous_contracts:
                        new_tokens.append(token)
                        log(f"🆕 发现新代币: {token.get('token', 'Unknown')} - {token['contract']}")
                else:
                    log(f"⚠️ 跳过无效的代币数据: {token}")
        except Exception as e:
            log(f"❌ 比较代币时出错: {e}")
            log(f"🔍 最近活动代币数据: {recent_tokens}")
        
        log(f"📊 地址 {address}: 最近活动代币 {len(recent_tokens)} 个，上次记录 {len(previous_tokens)} 个，新代币 {len(new_tokens)} 个")
        
        # 获取新代币的余额
        qualified_tokens = []
        for token in new_tokens:
            try:
                # 获取余额
                balance = await self.get_token_balance(address, token['contract'])
                token['number'] = balance
                
                if balance > 0:
                    # 获取详细信息
                    token_name, token_symbol, token_decimals = await self.get_token_info_simple(token['contract'])
                    formatted_amount = self.format_token_amount(balance, token_decimals)
                    
                    # 更新token名称
                    token['token'] = f"{token_name} ({token_symbol})"
                    
                    log(f"🆕 新代币: {token['token']} - 数量: {formatted_amount}")
                    
                    # 判断是否超过阈值
                    if formatted_amount >= NEW_TOKEN_AMOUNT_THRESHOLD:
                        log(f"✅ 新代币 {token_symbol} 数量 {formatted_amount} 超过阈值 {NEW_TOKEN_AMOUNT_THRESHOLD:,}")
                        qualified_token = {
                            'address': address,
                            'contract': token['contract'],
                            'token': token['token'],
                            'decimals': token_decimals,
                            'amount': formatted_amount,
                            'raw_balance': balance
                        }
                        qualified_tokens.append(qualified_token)
                        
                        # 处理 Alpha 事件
                        await self.process_alpha_event(qualified_token)
                    else:
                        log(f"📉 新代币数量 {formatted_amount} 未达到阈值 {NEW_TOKEN_AMOUNT_THRESHOLD:,}")
                else:
                    log(f"⚪ 新代币 {token['contract'][:10]}... 余额为 0，跳过")
            except Exception as e:
                log(f"❌ 处理新代币失败: {e}")
        
        # 更新记录（将新代币添加到记录中）
        try:
            # 只添加真正的新代币到记录中
            for token in new_tokens:
                # 移除临时标记字段
                clean_token = {
                    'token': token.get('token', 'Unknown'),
                    'contract': token['contract'],
                    'number': token.get('number', 0)
                }
                previous_tokens.append(clean_token)
            
            self.token_records[address] = previous_tokens
        except Exception as e:
            log(f"❌ 更新代币记录失败: {e}")
        
        return qualified_tokens
    
    def generate_alert_message(self, all_qualified_tokens):
        """生成统一的告警消息 - 修复格式问题"""
        if not all_qualified_tokens:
            return None
        
        # 按地址分组
        tokens_by_address = {}
        for token in all_qualified_tokens:
            address = token['address']
            if address not in tokens_by_address:
                tokens_by_address[address] = []
            tokens_by_address[address].append(token)
        
        # 生成消息
        message_parts = []
        message_parts.append(f"🚨 检测到新代币超过阈值！({self.chain_name})")
        message_parts.append("")
        
        total_tokens = len(all_qualified_tokens)
        total_addresses = len(tokens_by_address)
        
        message_parts.append(f"📊 统计信息:")
        message_parts.append(f"- 链: {self.chain_name}")
        message_parts.append(f"- 涉及地址: {total_addresses} 个")
        message_parts.append(f"- 新代币总数: {total_tokens} 个")
        message_parts.append(f"- 阈值: {NEW_TOKEN_AMOUNT_THRESHOLD:,}")
        message_parts.append(f"- 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        message_parts.append("")
        
        # 详细信息
        for address, tokens in tokens_by_address.items():
            message_parts.append(f"📍 地址: {address}")
            message_parts.append(f"🆕 新代币数量: {len(tokens)} 个")
            message_parts.append("")
            
            for i, token in enumerate(tokens, 1):
                message_parts.append(f"  {i}. {token['token']}")
                message_parts.append(f"     数量: {token['amount']}")
                message_parts.append(f"     合约: {token['contract']}")
                # 使用正确的浏览器URL
                explorer_url = f"{self.explorer_url}/token/{token['contract']}?a={address}"
                message_parts.append(f"     浏览器: {explorer_url}")
                message_parts.append("")
        
        message_parts.append("⚠️ 这些地址首次出现上述代币，请注意风险！")
        
        return "\n".join(message_parts)
    
    async def run_monitor(self):
        """运行监听器"""
        log(f"🚀 开始监听 {len(MONITOR_ADDRESSES)} 个地址的新代币... (链: {self.chain_name})")
        log("-" * 80)
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # 验证基本配置
            if not self.api_keys:
                log("❌ 错误: 请在 .env 文件中设置ETHERSCAN_API_KEY或ETHERSCAN_API_KEYS")
                return
            
            if not MONITOR_ADDRESSES:
                log("❌ 错误: 请在 .env 文件中设置 MONITOR_ADDRESSES")
                return

            # 跳过API密钥有效性检测，直接开始监听
            log("📋 跳过API密钥有效性检测，直接开始监听...")

            while True:
                try:
                    log(f"\n🔍 开始检查... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                    
                    # 收集所有地址的符合条件的新代币
                    all_qualified_tokens = []
                    
                    # 串行检查所有地址（避免API限制）
                    for address in MONITOR_ADDRESSES:
                        if address:
                            try:
                                qualified_tokens = await self.check_new_tokens(address)
                                if qualified_tokens:
                                    all_qualified_tokens.extend(qualified_tokens)
                            except Exception as e:
                                log(f"❌ 检查地址 {address} 时出错: {e}")
                                # 增加错误恢复延时
                                await asyncio.sleep(2)
                            await asyncio.sleep(1)  # 地址间增加延时
                    
                    # 保存代币记录
                    self.save_token_records()
                    
                    # 如果有符合条件的新代币，发送统一告警
                    if all_qualified_tokens:
                        message = self.generate_alert_message(all_qualified_tokens)
                        if message:
                            log(f"🚨 发送统一告警: {len(all_qualified_tokens)} 个新代币超过阈值")
                            await send_message_async(message)
                    else:
                        log("✅ 本轮检查完成，无新代币超过阈值")
                    
                    log(f"⏰ 等待 {CHECK_INTERVAL // 60} 分钟后继续监听...")
                    await asyncio.sleep(CHECK_INTERVAL)
                    
                except KeyboardInterrupt:
                    log("\n⏹️  监听器已手动停止")
                    break
                except Exception as e:
                    log(f"❌ 监听过程中出错: {e}")
                    await asyncio.sleep(CHECK_INTERVAL)

class MultiChainMonitor:
    """多链监听器"""
    def __init__(self):
        self.monitors = {}
        self.enabled_chains = []
        
        # 初始化启用的链
        for chain_id, config in CHAINS_CONFIG.items():
            if config['enabled']:
                self.enabled_chains.append(chain_id)
                self.monitors[chain_id] = NewTokenMonitor(chain_id)
        
        # 初始化完成，不输出日志，避免重复
    
    async def run_all_monitors(self):
        """运行所有链的监听器"""
        log(f"🚀 启动多链监听器... (共 {len(self.enabled_chains)} 条链)")
        
        if not self.enabled_chains:
            log("❌ 错误: 没有启用的链")
            return
        
        # 创建所有监听器的任务
        tasks = []
        for chain_id in self.enabled_chains:
            monitor = self.monitors[chain_id]
            task = asyncio.create_task(monitor.run_monitor())
            tasks.append(task)
        
        # 等待所有任务完成
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            log("\n⏹️  多链监听器已手动停止")
        except Exception as e:
            log(f"❌ 多链监听过程中出错: {e}")

def main():
    """主函数"""
    # 显示日志文件位置
    from logger import get_logger
    from config import log_all_config
    
    evm_logger = get_logger()
    log_filename = evm_logger.get_log_file_path()
    log(f"📝 日志文件位置: {os.path.abspath(log_filename)}")
    
    log("🚀 启动 Etherscan V2 API 新代币监听器...")
    
    # 输出配置信息（包括测试Twitter API连接和验证API密钥）
    log_all_config()
    
    # 获取启用的链
    enabled_chains = [chain_id for chain_id, config in CHAINS_CONFIG.items() if config['enabled']]
    
    if not enabled_chains:
        log("❌ 错误: 没有启用的链，请在 config.py 中启用至少一个链")
        return
    
    # 创建并运行监听器
    monitor = MultiChainMonitor()
    asyncio.run(monitor.run_all_monitors())

if __name__ == "__main__":
    main()
