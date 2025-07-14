import asyncio
import aiohttp
import json
import time
from datetime import datetime
from config import (
    BSC_API_KEY, BSC_API_URL, MONITOR_ADDRESSES,
    NEW_TOKEN_AMOUNT_THRESHOLD, CHECK_INTERVAL, TOKEN_RECORDS_FILE,
    WEBHOOK_URL, PROXY_URL, USE_PROXY
)
from webhook import send_message_async

class NewTokenMonitor:
    def __init__(self):
        self.session = None
        self.token_records = self.load_token_records()
        self.proxy = PROXY_URL if USE_PROXY else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def load_token_records(self):
        """加载代币记录 - 新格式"""
        try:
            with open(TOKEN_RECORDS_FILE, 'r') as f:
                data = json.load(f)
                print(f"📂 加载代币记录文件: {len(data)} 个地址")
                
                # 验证数据格式
                if not isinstance(data, dict):
                    print("⚠️ 代币记录文件格式错误，使用空数据")
                    return {}
                
                # 检查每个地址的数据格式
                for address, tokens in data.items():
                    if not isinstance(tokens, list):
                        print(f"⚠️ 地址 {address} 的代币数据格式错误，重置为空列表")
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
                            print(f"⚠️ 跳过无效的代币数据: {token}")
                    
                    data[address] = valid_tokens
                
                return data
                
        except FileNotFoundError:
            print("📂 代币记录文件不存在，将创建新文件")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ 代币记录文件JSON格式错误: {e}")
            return {}
        except Exception as e:
            print(f"❌ 加载代币记录文件失败: {e}")
            return {}
    
    def save_token_records(self):
        """保存代币记录"""
        with open(TOKEN_RECORDS_FILE, 'w') as f:
            json.dump(self.token_records, f, indent=2)
    
    async def check_api_status(self):
        """检查API密钥状态"""
        print("🔑 检查 BSCScan API 密钥状态...")
        print(f"🔑 API密钥: {BSC_API_KEY[:10]}..." if BSC_API_KEY else "❌ API密钥未设置")
        
        # 使用一个简单的API调用来测试密钥
        params = {
            'module': 'stats',
            'action': 'bnbsupply',
            'apikey': BSC_API_KEY
        }
        
        print(f"🔗 请求URL: {BSC_API_URL}")
        print(f"📋 请求参数: {params}")
        
        try:
            async with self.session.get(BSC_API_URL, params=params, proxy=self.proxy) as response:
                print(f"📡 HTTP状态码: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📄 完整API状态响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    if data.get('status') == '1':
                        print("✅ BSCScan API 密钥有效")
                        return True
                    else:
                        print(f"❌ BSCScan API 密钥无效或有问题: {data.get('message', 'Unknown error')}")
                        print(f"❌ 响应状态: {data.get('status')}")
                        return False
                else:
                    response_text = await response.text()
                    print(f"❌ API响应状态码错误: {response.status}")
                    print(f"❌ 错误响应内容: {response_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ API状态检查失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_all_erc20_tokens(self, address):
        """获取地址的所有ERC20代币交易记录，提取代币合约地址"""
        print(f"🔍 获取 {address} 的ERC20代币交易记录...")
        
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': 0,
            'endblock': 999999999,
            'page': 1,
            'offset': 10000,
            'sort': 'desc',
            'apikey': BSC_API_KEY
        }
        
        try:
            await asyncio.sleep(0.5)  # 增加延时
            async with self.session.get(BSC_API_URL, params=params, proxy=self.proxy, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"📊 代币交易API响应: status={data.get('status')}, message={data.get('message')}")
                    
                    if data.get('status') == '1':
                        transactions = data.get('result', [])
                        print(f"📈 获取到 {len(transactions)} 笔交易记录")
                        
                        # 提取唯一的代币合约地址和余额信息
                        token_info = {}
                        for tx in transactions:
                            contract = tx.get('contractAddress')
                            if contract and contract.lower() not in token_info:
                                # 获取代币基本信息
                                token_name = tx.get('tokenName', 'Unknown')
                                token_symbol = tx.get('tokenSymbol', 'Unknown')
                                
                                # 确保数据格式正确
                                token_obj = {
                                    'token': f"{token_name} ({token_symbol})" if token_name != 'Unknown' else 'Unknown',
                                    'contract': contract.lower(),
                                    'number': 0  # 余额稍后获取
                                }
                                
                                # 验证数据完整性
                                if all(key in token_obj for key in ['token', 'contract', 'number']):
                                    token_info[contract.lower()] = token_obj
                                else:
                                    print(f"⚠️ 跳过不完整的代币数据: {token_obj}")
                        
                        result = list(token_info.values())
                        print(f"🎯 发现 {len(result)} 个唯一代币")
                        print(f"🔍 返回数据类型: {type(result)}, 长度: {len(result)}")
                        
                        # 验证返回的数据
                        for i, token in enumerate(result):
                            if not isinstance(token, dict) or 'contract' not in token:
                                print(f"⚠️ 第 {i} 个代币数据格式错误: {token}")
                        
                        return result
                    else:
                        print(f"⚠️ 获取代币交易失败: {data.get('message', 'Unknown error')}")
                else:
                    print(f"❌ HTTP错误: {response.status}")
        except Exception as e:
            print(f"❌ 获取 {address} 的代币交易记录失败: {e}")
            import traceback
            traceback.print_exc()
        return []
    
    async def get_token_balance(self, address, token_contract):
        """获取指定地址的代币余额"""
        params = {
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': token_contract,
            'address': address,
            'tag': 'latest',
            'apikey': BSC_API_KEY
        }
        
        print(f"💰 获取代币余额 - 地址: {address}, 代币: {token_contract}")
        print(f"🔗 请求URL: {BSC_API_URL}")
        print(f"📋 请求参数: {params}")
        
        try:
            await asyncio.sleep(0.3)  # 增加延时避免API限制
            async with self.session.get(BSC_API_URL, params=params, proxy=self.proxy, timeout=15) as response:
                print(f"📡 HTTP状态码: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📄 完整余额API响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    if data.get('status') == '1':
                        balance = int(data.get('result', 0))
                        print(f"💰 代币余额: {token_contract[:10]}... = {balance}")
                        return balance
                    else:
                        print(f"⚠️ 获取余额失败: {data.get('message', 'Unknown error')}")
                        print(f"⚠️ 响应状态: {data.get('status')}")
                        print(f"⚠️ 响应结果: {data.get('result')}")
                else:
                    response_text = await response.text()
                    print(f"❌ 余额查询HTTP错误: {response.status}")
                    print(f"❌ 错误响应内容: {response_text}")
        except Exception as e:
            print(f"⚠️ 获取余额失败 - 地址: {address}, 代币: {token_contract}, 错误: {e}")
            import traceback
            traceback.print_exc()
        return 0
    
    async def get_token_info_simple(self, token_contract):
        """仅通过tokentx接口获取代币信息"""
        print(f"🔍 获取代币详细信息: {token_contract}")
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': token_contract,
            'page': 1,
            'offset': 1,
            'sort': 'desc',
            'apikey': BSC_API_KEY
        }
        try:
            await asyncio.sleep(0.4)
            async with self.session.get(BSC_API_URL, params=params, proxy=self.proxy, timeout=15) as response:
                print(f"📡 HTTP状态码: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"📄 代币交易记录API响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    if data.get('status') == '1' and data.get('result'):
                        tx = data['result'][0]
                        token_name = tx.get('tokenName', 'Unknown')
                        token_symbol = tx.get('tokenSymbol', 'Unknown')
                        token_decimals = int(tx.get('tokenDecimal', 18))
                        print(f"✅ 代币信息: 名称={token_name}, 符号={token_symbol}, 精度={token_decimals}")
                        return token_name, token_symbol, token_decimals
                    else:
                        print(f"⚠️ 获取代币交易记录失败: {data.get('message', 'Unknown')}")
                else:
                    response_text = await response.text()
                    print(f"❌ 代币交易记录HTTP错误: {response.status}")
                    print(f"❌ 错误响应内容: {response_text}")
        except Exception as e:
            print(f"❌ 获取代币交易记录失败: {e}")
            import traceback
            traceback.print_exc()
        # fallback
        short_addr = token_contract[:6] + '...' + token_contract[-4:]
        return f"Token_{short_addr}", f"T{token_contract[2:6]}", 18
    
    def format_token_amount(self, amount, decimals):
        """格式化代币数量"""
        return amount / (10 ** decimals)
    
    async def check_new_tokens(self, address):
        """检查地址的新代币"""
        print(f"🔍 检查地址 {address} 的代币...")
        
        # 获取当前所有代币
        current_tokens = await self.get_all_erc20_tokens(address)
        print(f"🔍 当前代币数据类型: {type(current_tokens)}, 长度: {len(current_tokens) if current_tokens else 0}")
        
        # 获取上次记录的代币
        previous_tokens = self.token_records.get(address, [])
        print(f"🔍 上次记录代币数据类型: {type(previous_tokens)}, 长度: {len(previous_tokens)}")
        
        # 提取上次记录的合约地址集合
        try:
            previous_contracts = {token['contract'] for token in previous_tokens}
            print(f"🔍 上次记录合约地址集合: {len(previous_contracts)} 个")
        except Exception as e:
            print(f"❌ 创建合约地址集合失败: {e}")
            print(f"🔍 上次记录代币数据: {previous_tokens}")
            previous_contracts = set()
        
        # 找出新代币（比较合约地址）
        new_tokens = []
        try:
            for token in current_tokens:
                if isinstance(token, dict) and 'contract' in token:
                    if token['contract'] not in previous_contracts:
                        new_tokens.append(token)
                else:
                    print(f"⚠️ 跳过无效的代币数据: {token}")
        except Exception as e:
            print(f"❌ 比较代币时出错: {e}")
            print(f"🔍 当前代币数据: {current_tokens}")
        
        print(f"📊 地址 {address}: 当前代币 {len(current_tokens)} 个，上次记录 {len(previous_tokens)} 个，新代币 {len(new_tokens)} 个")
        
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
                    
                    print(f"🆕 新代币: {token['token']} - 数量: {formatted_amount:,.{token_decimals}f}")
                    
                    # 判断是否超过阈值
                    if formatted_amount >= NEW_TOKEN_AMOUNT_THRESHOLD:
                        print(f"✅ 新代币 {token_symbol} 数量 {formatted_amount:,.{token_decimals}f} 超过阈值 {NEW_TOKEN_AMOUNT_THRESHOLD:,}")
                        qualified_tokens.append({
                            'address': address,
                            'contract': token['contract'],
                            'token': token['token'],
                            'decimals': token_decimals,
                            'amount': formatted_amount,
                            'raw_balance': balance
                        })
                    else:
                        print(f"📉 新代币数量 {formatted_amount:,.{token_decimals}f} 未达到阈值 {NEW_TOKEN_AMOUNT_THRESHOLD:,}")
                else:
                    print(f"⚪ 新代币 {token['contract'][:10]}... 余额为 0，跳过")
            except Exception as e:
                print(f"❌ 处理新代币失败: {e}")
        
        # 更新记录（包含所有代币，新旧都有）
        try:
            all_tokens = previous_tokens.copy()
            all_tokens.extend(new_tokens)
            self.token_records[address] = all_tokens
        except Exception as e:
            print(f"❌ 更新代币记录失败: {e}")
        
        return qualified_tokens
    
    def generate_alert_message(self, all_qualified_tokens):
        """生成统一的告警消息"""
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
        message_parts.append("🚨 检测到新代币超过阈值！")
        message_parts.append("")
        
        total_tokens = len(all_qualified_tokens)
        total_addresses = len(tokens_by_address)
        
        message_parts.append(f"📊 统计信息:")
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
                message_parts.append(f"     数量: {token['amount']:,.{token['decimals']}f}")
                message_parts.append(f"     合约: {token['contract']}")
                message_parts.append(f"     浏览器: https://bscscan.com/token/{token['contract']}?a={address}")
                message_parts.append("")
        
        message_parts.append("⚠️ 这些地址首次出现上述代币，请注意风险！")
        
        return "\n".join(message_parts)
    
    async def run_monitor(self):
        """运行监听器"""
        print(f"🚀 开始监听 {len(MONITOR_ADDRESSES)} 个地址的新代币...")
        print(f"📍 监听地址: {MONITOR_ADDRESSES}")
        print(f"💰 新代币阈值: {NEW_TOKEN_AMOUNT_THRESHOLD:,}")
        print(f"⏰ 检查间隔: {CHECK_INTERVAL // 60} 分钟")
        print("-" * 80)
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # 验证API密钥状态
            if not BSC_API_KEY:
                print("❌ 错误: 请在 .env 文件中设置 BSC_API_KEY")
                return
            
            if not WEBHOOK_URL:
                print("❌ 错误: 请在 .env 文件中设置 WEBHOOK_URL")
                return
            
            if not MONITOR_ADDRESSES:
                print("❌ 错误: 请在 .env 文件中设置 MONITOR_ADDRESSES")
                return

            if not await self.check_api_status():
                print("❌ API密钥无效或有问题，无法继续监听。请检查 .env 文件中的 BSC_API_KEY。")
                return

            while True:
                try:
                    print(f"\n🔍 开始检查... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                    
                    # 收集所有地址的符合条件的新代币
                    all_qualified_tokens = []
                    
                    # 串行检查所有地址（避免API限制）
                    for address in MONITOR_ADDRESSES:
                        if address:
                            qualified_tokens = await self.check_new_tokens(address)
                            if qualified_tokens:
                                all_qualified_tokens.extend(qualified_tokens)
                            await asyncio.sleep(1)  # 地址间增加延时
                    
                    # 保存代币记录
                    self.save_token_records()
                    
                    # 如果有符合条件的新代币，发送统一告警
                    if all_qualified_tokens:
                        message = self.generate_alert_message(all_qualified_tokens)
                        if message:
                            print(f"🚨 发送统一告警: {len(all_qualified_tokens)} 个新代币超过阈值")
                            await send_message_async(message)
                    else:
                        print("✅ 本轮检查完成，无新代币超过阈值")
                    
                    print(f"⏰ 等待 {CHECK_INTERVAL // 60} 分钟后继续监听...")
                    await asyncio.sleep(CHECK_INTERVAL)
                    
                except KeyboardInterrupt:
                    print("\n⏹️  监听器已手动停止")
                    break
                except Exception as e:
                    print(f"❌ 监听过程中出错: {e}")
                    await asyncio.sleep(CHECK_INTERVAL)

def main():
    """主函数"""
    print("🚀 启动 BSC EVM 新代币监听器...")
    
    monitor = NewTokenMonitor()
    asyncio.run(monitor.run_monitor())

if __name__ == "__main__":
    main()
