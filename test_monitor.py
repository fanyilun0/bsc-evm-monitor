import asyncio
from main import NewTokenMonitor
from logger import log

async def test_monitor():
    """测试监听器的代币处理流程"""
    # 初始化监听器
    monitor = NewTokenMonitor()
    
    # 模拟一个新代币事件
    mock_token = {
        'address': '0x73D8bD54F7Cf5FAb43fE4Ef40A62D390644946Db',
        'contract': '0x1234567890abcdef1234567890abcdef12345678',
        'name': 'PublicAI',
        'symbol': 'PUBLIC',
        'decimals': 18,
        'amount': 1500000,  # 超过默认阈值1M
        'raw_balance': 1500000000000000000000000,
        'chain': 'Ethereum Mainnet',
        'explorer': 'https://etherscan.io/token/0x1234567890abcdef1234567890abcdef12345678'
    }
    
    # 生成Alpha事件
    alpha_event = monitor.generate_alpha_event(mock_token)
    if alpha_event:
        log("✅ 成功生成Alpha事件:")
        log(f"   代币: {alpha_event['name']} ({alpha_event['symbol']})")
        log(f"   数量: {alpha_event['amount']}")
        log(f"   地址: {alpha_event['address']}")
        log(f"   合约: {alpha_event['contract']}")
        
        # 处理Alpha事件
        success = await monitor.process_alpha_event(mock_token)
        if success:
            log("✅ Alpha事件处理成功")
        else:
            log("❌ Alpha事件处理失败")
    else:
        log("❌ 生成Alpha事件失败")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_monitor())
