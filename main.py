import asyncio
import aiohttp
import json
import time
from datetime import datetime
from config import (
    BSC_API_KEY, BSC_API_URL, MONITOR_ADDRESSES, MONITOR_TOKENS,
    TRANSFER_AMOUNT_THRESHOLD, CHECK_INTERVAL, BALANCE_FILE,
    WEBHOOK_URL, PROXY_URL, USE_PROXY
)
from webhook import send_message

class BSCTokenMonitor:
    def __init__(self):
        self.session = None
        self.balance_records = self.load_balance_records()
        self.proxy = PROXY_URL if USE_PROXY else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def load_balance_records(self):
        """加载余额记录"""
        try:
            with open(BALANCE_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_balance_records(self):
        """保存余额记录"""
        with open(BALANCE_FILE, 'w') as f:
            json.dump(self.balance_records, f, indent=2)
    
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
        
        try:
            async with self.session.get(BSC_API_URL, params=params, proxy=self.proxy) as response:
                data = await response.json()
                if data.get('status') == '1':
                    return int(data.get('result', 0))
        except Exception as e:
            print(f"获取余额失败 - 地址: {address}, 代币: {token_contract}, 错误: {e}")
        return 0
    
    async def get_token_info(self, token_contract):
        """获取代币信息"""
        # 获取代币名称
        params_name = {
            'module': 'token',
            'action': 'tokenname',
            'contractaddress': token_contract,
            'apikey': BSC_API_KEY
        }
        
        # 获取代币符号
        params_symbol = {
            'module': 'token',
            'action': 'tokensymbol',
            'contractaddress': token_contract,
            'apikey': BSC_API_KEY
        }
        
        # 获取代币精度
        params_decimals = {
            'module': 'token',
            'action': 'tokendecimals',
            'contractaddress': token_contract,
            'apikey': BSC_API_KEY
        }
        
        try:
            # 并发获取代币信息
            async with self.session.get(BSC_API_URL, params=params_name, proxy=self.proxy) as response:
                name_data = await response.json()
                token_name = name_data.get('result', 'Unknown') if name_data.get('status') == '1' else 'Unknown'
            
            async with self.session.get(BSC_API_URL, params=params_symbol, proxy=self.proxy) as response:
                symbol_data = await response.json()
                token_symbol = symbol_data.get('result', 'Unknown') if symbol_data.get('status') == '1' else 'Unknown'
            
            async with self.session.get(BSC_API_URL, params=params_decimals, proxy=self.proxy) as response:
                decimals_data = await response.json()
                token_decimals = int(decimals_data.get('result', 18)) if decimals_data.get('status') == '1' else 18
            
            return token_name, token_symbol, token_decimals
        except Exception as e:
            print(f"获取代币信息失败 - 代币: {token_contract}, 错误: {e}")
            return 'Unknown', 'Unknown', 18
    
    def format_token_amount(self, amount, decimals):
        """格式化代币数量"""
        return amount / (10 ** decimals)
    
    async def check_balance_changes(self, address, token_contract):
        """检查余额变化"""
        current_balance = await self.get_token_balance(address, token_contract)
        
        # 生成记录键
        record_key = f"{address}_{token_contract}"
        
        # 获取上次记录的余额
        previous_balance = self.balance_records.get(record_key, 0)
        
        # 计算余额变化
        balance_change = current_balance - previous_balance
        
        # 更新余额记录
        self.balance_records[record_key] = current_balance
        
        return balance_change, current_balance, previous_balance
    
    async def process_balance_increase(self, address, token_contract, increase_amount, current_balance):
        """处理余额增加"""
        threshold = int(TRANSFER_AMOUNT_THRESHOLD)
        
        if increase_amount >= threshold:
            # 获取代币信息
            token_name, token_symbol, token_decimals = await self.get_token_info(token_contract)
            
            # 格式化数量
            formatted_increase = self.format_token_amount(increase_amount, token_decimals)
            formatted_current = self.format_token_amount(current_balance, token_decimals)
            
            # 构造消息
            message = f"""🚨 检测到代币转入！

地址: {address}
代币: {token_name} ({token_symbol})
转入数量: {formatted_increase:,.{token_decimals}f} {token_symbol}
当前余额: {formatted_current:,.{token_decimals}f} {token_symbol}
代币合约: {token_contract}
检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
BSC 浏览器: https://bscscan.com/token/{token_contract}?a={address}"""
            
            # 发送通知
            await send_message(self.session, message, self.headers, self.proxy)
            print(f"✅ 发送通知: {address} 转入 {formatted_increase:,.{token_decimals}f} {token_symbol}")
    
    async def monitor_address_token(self, address, token_contract):
        """监听单个地址的指定代币"""
        try:
            balance_change, current_balance, previous_balance = await self.check_balance_changes(address, token_contract)
            
            if balance_change > 0:
                print(f"📈 余额增加: {address} ({token_contract[:10]}...) +{balance_change}")
                await self.process_balance_increase(address, token_contract, balance_change, current_balance)
            elif balance_change < 0:
                print(f"📉 余额减少: {address} ({token_contract[:10]}...) {balance_change}")
            else:
                print(f"📊 余额无变化: {address} ({token_contract[:10]}...) = {current_balance}")
                
        except Exception as e:
            print(f"❌ 监听失败 - 地址: {address}, 代币: {token_contract}, 错误: {e}")
    
    async def run_monitor(self):
        """运行监听器"""
        print(f"🚀 开始监听 {len(MONITOR_ADDRESSES)} 个地址的 {len(MONITOR_TOKENS)} 种代币...")
        print(f"📍 监听地址: {MONITOR_ADDRESSES}")
        print(f"🎯 监听代币: {MONITOR_TOKENS}")
        print(f"💰 转入阈值: {TRANSFER_AMOUNT_THRESHOLD}")
        print(f"⏰ 检查间隔: {CHECK_INTERVAL // 60} 分钟")
        print("-" * 60)
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            while True:
                try:
                    print(f"\n🔍 开始检查... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                    
                    # 监听所有地址和代币组合
                    tasks = []
                    for address in MONITOR_ADDRESSES:
                        for token_contract in MONITOR_TOKENS:
                            if address and token_contract:
                                tasks.append(self.monitor_address_token(address, token_contract))
                    
                    # 并发执行所有检查
                    await asyncio.gather(*tasks)
                    
                    # 保存余额记录
                    self.save_balance_records()
                    
                    print(f"✅ 本轮检查完成，等待 {CHECK_INTERVAL // 60} 分钟...")
                    await asyncio.sleep(CHECK_INTERVAL)
                    
                except KeyboardInterrupt:
                    print("\n⏹️  监听器已手动停止")
                    break
                except Exception as e:
                    print(f"❌ 监听过程中出错: {e}")
                    await asyncio.sleep(CHECK_INTERVAL)

def main():
    """主函数"""
    if not BSC_API_KEY:
        print("❌ 错误: 请在 .env 文件中设置 BSC_API_KEY")
        return
    
    if not WEBHOOK_URL:
        print("❌ 错误: 请在 .env 文件中设置 WEBHOOK_URL")
        return
    
    if not MONITOR_ADDRESSES:
        print("❌ 错误: 请在 .env 文件中设置 MONITOR_ADDRESSES")
        return
    
    if not MONITOR_TOKENS:
        print("❌ 错误: 请在 .env 文件中设置 MONITOR_TOKENS")
        return
    
    monitor = BSCTokenMonitor()
    asyncio.run(monitor.run_monitor())

if __name__ == "__main__":
    main()
