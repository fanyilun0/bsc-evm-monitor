import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime, timedelta
from config import (
    ETHERSCAN_API_KEYS, MONITOR_ADDRESSES,
    NEW_TOKEN_AMOUNT_THRESHOLD_MIN, NEW_TOKEN_AMOUNT_THRESHOLD_MAX, CHECK_INTERVAL, 
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
        log(f"🎯 区块号控制: 启用严格的区块范围查询，避免重复监听历史交易")
        log(f"🔄 区块号获取策略: API查询 + 时间估算双重保障")
        
        # 显示不同链的平均出块时间
        avg_block_times = {1: 12, 56: 3, 8453: 2}
        avg_time = avg_block_times.get(self.chain_id, 12)
        log(f"⏱️  {self.chain_name} 平均出块时间: ~{avg_time}秒")
    
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
        """加载代币记录 - 简化格式，只存储已处理过的合约地址列表"""
        records_file = get_token_records_file(self.chain_id)
        try:
            with open(records_file, 'r') as f:
                data = json.load(f)
                
                # 验证数据格式为合约地址列表
                if isinstance(data, list):
                    # 确保所有地址都是小写且格式正确
                    contract_list = []
                    for addr in data:
                        if isinstance(addr, str) and addr.startswith('0x') and len(addr) == 42:
                            contract_list.append(addr.lower())
                        else:
                            log(f"⚠️ 跳过无效的合约地址: {addr}")
                    
                    log(f"📂 加载代币记录文件: {records_file}, {len(contract_list)} 个已处理合约地址")
                    return contract_list
                else:
                    log(f"❌ 代币记录文件格式错误，期望数组格式，实际: {type(data)}")
                    return []
                
        except FileNotFoundError:
            log(f"📂 代币记录文件不存在: {records_file}，将创建新文件")
            return []
        except json.JSONDecodeError as e:
            log(f"❌ 代币记录文件JSON格式错误: {e}")
            return []
        except Exception as e:
            log(f"❌ 加载代币记录文件失败: {e}")
            return []
    
    def save_token_records(self):
        """保存代币记录 - 新格式，直接保存合约地址列表"""
        self.save_token_records_to_file(self.token_records)
    
    def save_token_records_to_file(self, contract_list):
        """保存合约地址列表到文件"""
        records_file = get_token_records_file(self.chain_id)
        with open(records_file, 'w') as f:
            json.dump(contract_list, f, indent=2)
    
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
        
        # 清理参数中的None值
        clean_params = {}
        for key, value in params.items():
            if value is not None:
                clean_params[key] = value
        
        clean_params['apikey'] = current_key
        
        # 提取API调用信息用于日志
        module = clean_params.get('module', 'unknown')
        action = clean_params.get('action', 'unknown')
        chain_id = clean_params.get('chainid', self.chain_id)
        
        log(f"🔗 请求URL: {self.api_url}")
        # log(f"📋 请求参数: {clean_params}")
        log(f"🔑 使用API密钥: {current_key[:10]}...")
        log(f"🌐 Etherscan API调用: module={module}, action={action}, chain_id={chain_id}")
        
        try:
            async with self.session.get(self.api_url, params=clean_params, proxy=self.proxy, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 检查API限制和错误
                    if data.get('status') == '0':
                        result = data.get('result', '')
                        
                        # 检查result是否为字符串类型
                        if isinstance(result, str):
                            # 检查API限制
                            if 'rate limit' in result.lower():
                                log(f"⚠️ 遇到API限制: {result} (module={module}, action={action})")
                                
                                if retry_count < self.max_retries:
                                    log(f"🔄 等待 {self.rate_limit_retry_delay} 秒后重试...")
                                    await asyncio.sleep(self.rate_limit_retry_delay)
                                    
                                    # 增加重试延迟
                                    self.rate_limit_retry_delay = min(self.rate_limit_retry_delay * 2, 30)
                                    
                                    return await self.make_api_request(params, retry_count + 1)
                                else:
                                    log(f"❌ 达到最大重试次数，API请求失败 (module={module}, action={action})")
                                    return None
                            
                            # 检查API密钥无效 - 增加更多匹配模式
                            elif any(error_text in result.lower() for error_text in ['invalid api key', 'api key', '#err2']):
                                log(f"⚠️ API密钥无效: {result} (module={module}, action={action})")
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
                    
        except asyncio.TimeoutError:
            log(f"❌ API请求超时 (module={module}, action={action})")
            if retry_count < self.max_retries:
                log(f"🔄 超时后重试...")
                await asyncio.sleep(2)
                return await self.make_api_request(params, retry_count + 1)
            return None
        except aiohttp.ClientConnectorError as e:
            log(f"❌ 连接错误: {e} (module={module}, action={action})")
            if retry_count < self.max_retries:
                log(f"🔄 连接错误后重试...")
                await asyncio.sleep(5)
                return await self.make_api_request(params, retry_count + 1)
            return None
        except Exception as e:
            log(f"❌ API请求失败: {e} (module={module}, action={action})")
            import traceback
            traceback.print_exc()
            return None

    async def get_block_by_timestamp(self, timestamp):
        """根据时间戳获取最接近的区块号 - 增强版本，支持多种API策略"""
        log(f"🔍 根据时间戳获取区块号: {timestamp}")
        log(f"📅 目标时间: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 策略1: 使用 block.getblocknobytime (标准方法)
        params = {
            'chainid': self.chain_id,
            'module': 'block',
            'action': 'getblocknobytime',
            'timestamp': int(timestamp),
            'closest': 'before',
        }
        
        log(f"🌐 策略1: 调用Etherscan API block.getblocknobytime")
        data = await self.make_api_request(params)
        if data and data.get('status') == '1' and data.get('result'):
            try:
                block_number = int(data.get('result', 0))
                if block_number > 0:
                    log(f"✅ 策略1成功: 时间戳 {timestamp} 对应区块号 {block_number}")
                    return block_number
            except (ValueError, TypeError) as e:
                log(f"❌ 策略1结果解析失败: {e}, 原始结果: {data.get('result')}")
        else:
            error_msg = data.get('result', 'Unknown error') if data else 'No response'
            log(f"❌ 策略1失败: {error_msg}")
        
        # 策略2: 使用估算方法（基于最新区块和平均出块时间）
        log(f"🔄 策略2: 使用区块时间估算方法")
        estimated_block = await self.estimate_block_by_average_time(timestamp)
        if estimated_block:
            log(f"✅ 策略2成功: 估算区块号 {estimated_block}")
            return estimated_block
        
        log(f"❌ 所有策略失败，无法获取时间戳 {timestamp} 对应的区块号")
        return None
    
    async def estimate_block_by_average_time(self, target_timestamp):
        """基于平均出块时间估算区块号"""
        try:
            # 获取最新区块号
            latest_block = await self.get_latest_block_number()
            if not latest_block:
                log(f"❌ 无法获取最新区块号，估算失败")
                return None
            
            # 获取最新区块的时间戳
            latest_block_info = await self.get_block_info(latest_block)
            if not latest_block_info:
                log(f"❌ 无法获取最新区块信息，估算失败")
                return None
            
            latest_timestamp = latest_block_info.get('timestamp')
            if not latest_timestamp:
                log(f"❌ 最新区块时间戳无效，估算失败")
                return None
            
            # 计算时间差（秒）
            time_diff = latest_timestamp - target_timestamp
            if time_diff < 0:
                log(f"⚠️ 目标时间戳在未来，使用最新区块")
                return latest_block
            
            # 不同链的平均出块时间（秒）
            avg_block_times = {
                1: 12,      # Ethereum: ~12秒
                56: 3,      # BSC: ~3秒  
                8453: 2     # Base: ~2秒
            }
            
            avg_block_time = avg_block_times.get(self.chain_id, 12)  # 默认12秒
            
            # 估算需要回溯的区块数
            blocks_to_go_back = int(time_diff / avg_block_time)
            estimated_block = max(latest_block - blocks_to_go_back, 0)
            
            log(f"📊 估算参数: 最新区块={latest_block}, 最新时间={latest_timestamp}")
            log(f"📊 时间差={time_diff}秒, 平均出块时间={avg_block_time}秒")
            log(f"📊 回溯区块数={blocks_to_go_back}, 估算区块号={estimated_block}")
            
            return estimated_block
            
        except Exception as e:
            log(f"❌ 区块号估算异常: {e}")
            return None
    
    async def get_block_info(self, block_number):
        """获取指定区块的详细信息"""
        params = {
            'chainid': self.chain_id,
            'module': 'proxy',
            'action': 'eth_getBlockByNumber',
            'tag': hex(block_number),
            'boolean': 'false'
        }
        
        log(f"🌐 获取区块 {block_number} 的详细信息")
        data = await self.make_api_request(params)
        if data and data.get('result'):
            try:
                block_info = data.get('result')
                timestamp = int(block_info.get('timestamp', '0x0'), 16)
                return {'timestamp': timestamp, 'number': block_number}
            except (ValueError, TypeError) as e:
                log(f"❌ 解析区块信息失败: {e}")
                return None
        else:
            log(f"❌ 获取区块信息失败")
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
        """获取地址在指定时间窗口内的ERC20代币交易记录 - 使用严格的区块号控制"""
        if minutes_ago is None:
            minutes_ago = self.time_window_minutes
            
        log(f"🔍 获取 {address} 最近 {minutes_ago} 分钟的ERC20代币交易记录...")
        
        # 计算目标时间戳
        current_time = int(time.time())
        start_timestamp = current_time - (minutes_ago * 60)
        
        log(f"⏰ 时间窗口: {datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')} - {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')} (最近 {minutes_ago} 分钟)")
        
        # 获取对应的起始区块号
        start_block = await self.get_block_by_timestamp(start_timestamp)
        if start_block is None:
            log(f"❌ 无法获取起始区块号，跳过此地址")
            return []
        
        # 获取最新区块号
        latest_block = await self.get_latest_block_number()
        if latest_block is None:
            log(f"❌ 无法获取最新区块号，跳过此地址")
            return []
        
        # 确保区块范围合理
        if start_block > latest_block:
            log(f"⚠️ 起始区块号({start_block})大于最新区块号({latest_block})，使用最新区块号")
            start_block = latest_block
        
        # 构建API请求参数 - 严格使用区块号范围
        params = {
            'chainid': self.chain_id,
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': start_block,
            'endblock': latest_block,
            'page': 1,
            'offset': 10000,  # 最多10000笔交易
            'sort': 'desc',  # 降序，最新的在前面
        }
        
        log(f"📊 严格区块范围: {start_block} - {latest_block} (跨越 {latest_block - start_block} 个区块)")
        log(f"🌐 调用Etherscan API: account.tokentx - 获取地址的代币转账记录")
        log(f"📍 目标地址: {address}")
        
        data = await self.make_api_request(params)
        if data and data.get('status') == '1':
            all_transactions = data.get('result', [])
            log(f"📈 chain_id: {self.chain_id} 区块范围内API返回 {len(all_transactions)} 笔交易记录")
            
            if not all_transactions:
                log(f"📊 chain_id: {self.chain_id} 地址 {address} 在指定区块范围内没有代币交易记录")
                return []
            
            # 过滤转入交易并进行额外的时间戳验证
            recent_transactions = []
            for tx in all_transactions:
                try:
                    # 只关注转入交易 (to 地址是目标地址)
                    if tx.get('to', '').lower() == address.lower():
                        # 额外的时间戳验证（双重保险）
                        tx_timestamp = int(tx.get('timeStamp', 0))
                        if tx_timestamp >= start_timestamp:
                            recent_transactions.append(tx)
                        else:
                            log(f"⏭️ 跳过时间戳过早的交易: {tx.get('hash', 'unknown')[:10]}... 时间: {datetime.fromtimestamp(tx_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
                except (ValueError, TypeError):
                    log(f"⚠️ 跳过时间戳格式错误的交易: {tx.get('timeStamp')}")
                    continue
            
            log(f"📈 区块范围+时间验证后的转入交易: {len(recent_transactions)} 笔")
            
            # 提取唯一的代币合约地址
            token_info = {}
            recent_contracts = set()
            
            for tx in recent_transactions:
                contract = tx.get('contractAddress')
                if contract and contract.lower() not in token_info:
                    # 获取代币基本信息
                    token_name = tx.get('tokenName', 'Unknown')
                    token_symbol = tx.get('tokenSymbol', 'Unknown')
                    
                    # 记录最近交易涉及的合约
                    recent_contracts.add(contract.lower())
                    
                    # 记录转入的代币信息
                    token_obj = {
                        'token': f"{token_name} ({token_symbol})" if token_name != 'Unknown' else 'Unknown',
                        'contract': contract.lower(),
                        'number': 0,  # 余额稍后获取
                        'tx_hash': tx.get('hash', ''),
                        'tx_timestamp': tx.get('timeStamp', 0),
                        'block_number': tx.get('blockNumber', 0)
                    }
                    
                    # 验证数据完整性
                    if all(key in token_obj for key in ['token', 'contract']):
                        token_info[contract.lower()] = token_obj
                    else:
                        log(f"⚠️ 跳过不完整的代币数据: {token_obj}")
            
            return list(token_info.values())
        else:
            error_result = data.get('result', 'Unknown error') if data else 'No response'
            log(f"❌ 获取代币交易失败: {error_result}")
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
        """检查地址的新代币 - 重构后的简化版本，只检查合约地址是否已处理过"""
        log(f"🔍 检查地址 {address} 的代币...")
        
        # 获取最近时间窗口内有活动的代币
        recent_tokens = await self.get_recent_erc20_tokens(address)
        log(f"🔍 最近活动代币: {len(recent_tokens) if recent_tokens else 0} 个")
        
        if not recent_tokens:
            log(f"📊 地址 {address} 最近无代币活动")
            return []
        
        # 找出新代币（未在已处理列表中的合约地址）
        new_contract_tokens = []
        for token in recent_tokens:
            if isinstance(token, dict) and 'contract' in token:
                contract_addr = token['contract'].lower()
                if contract_addr not in self.token_records:
                    new_contract_tokens.append(token)
                    log(f"🆕 发现新合约地址: {contract_addr}")
            else:
                log(f"⚠️ 跳过无效的代币数据: {token}")
        
        log(f"🎯 地址 {address}: 最近活动代币 {len(recent_tokens)} 个，新合约 {len(new_contract_tokens)} 个")
        
        if not new_contract_tokens:
            return []
        
        # 处理新代币：获取余额、检查阈值、发送推文
        qualified_tokens = []
        new_processed_contracts = []
        
        for token in new_contract_tokens:
            try:
                contract_addr = token['contract'].lower()
                
                # 获取余额
                balance = await self.get_token_balance(address, token['contract'])
                
                if balance > 0:
                    # 获取详细信息
                    token_name, token_symbol, token_decimals = await self.get_token_info_simple(token['contract'])
                    formatted_amount = self.format_token_amount(balance, token_decimals)
                    
                    log(f"🆕 新代币详情: {token_name} ({token_symbol}) - 数量: {formatted_amount}")
                    
                    # 检查是否超过阈值
                    if formatted_amount >= NEW_TOKEN_AMOUNT_THRESHOLD_MIN and formatted_amount <= NEW_TOKEN_AMOUNT_THRESHOLD_MAX:
                        # 准备推文数据
                        twitter_token_info = {
                            'address': address,
                            'contract': contract_addr,
                            'token': f"{token_name} ({token_symbol})",
                            'decimals': token_decimals,
                            'amount': formatted_amount,
                            'raw_balance': balance
                        }
                        
                        log(f"🐦 处理推文: {twitter_token_info['token']} - 数量: {twitter_token_info['amount']}")
                        
                        # 处理 Alpha 事件（推文发送）
                        alpha_success = await self.process_alpha_event(twitter_token_info)
                        if alpha_success:
                            qualified_tokens.append(twitter_token_info)
                            log(f"✅ 代币 {twitter_token_info['token']} 推文处理成功")
                        else:
                            log(f"⚠️ 代币 {twitter_token_info['token']} 推文处理失败")
                
                # 无论余额多少或推文是否成功，都将合约地址标记为已处理
                new_processed_contracts.append(contract_addr)
                log(f"📝 标记合约为已处理: {contract_addr}")
                
            except Exception as e:
                log(f"❌ 处理代币失败: {e}")
                # 即使处理失败，也标记为已处理，避免重复尝试
                new_processed_contracts.append(contract_addr)
        
        # 更新已处理合约列表
        if new_processed_contracts:
            self.token_records.extend(new_processed_contracts)
            log(f"💾 新增 {len(new_processed_contracts)} 个已处理合约地址到缓存")
            # 立即保存到文件
            self.save_token_records()
        
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
        message_parts.append(f"- 阈值: {NEW_TOKEN_AMOUNT_THRESHOLD_MIN:,} - {NEW_TOKEN_AMOUNT_THRESHOLD_MAX:,}")
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
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
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
                    
                    # 代币记录已在check_new_tokens中保存，无需重复保存
                    
                    # 如果有符合条件的新代币，发送统一告警
                    if all_qualified_tokens:
                        message = self.generate_alert_message(all_qualified_tokens)
                        if message:
                            log(f"🚨 发送统一告警: {len(all_qualified_tokens)} 个新代币超过阈值")
                            await send_message_async(message)
                    else:
                        log("✅ 本轮检查完成，无新代币超过阈值")
                    
                    log(f"⏰ 等待 {TIME_WINDOW_MINUTES // 60} 分钟后继续监听...")
                    await asyncio.sleep(TIME_WINDOW_MINUTES)
                    
                except KeyboardInterrupt:
                    log("\n⏹️  监听器已手动停止")
                    break
                except Exception as e:
                    log(f"❌ 监听过程中出错: {e}")
                    await asyncio.sleep(TIME_WINDOW_MINUTES)

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
    from config import log_all_config

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
