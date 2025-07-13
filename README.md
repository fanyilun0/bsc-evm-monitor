# BSC EVM 代币监听器

一个基于余额变化监听 BSC (Binance Smart Chain) 上指定地址代币转入的 Python 工具。

## 功能特点

- 🔍 监听指定地址列表的指定代币余额变化
- 💰 检测指定数额的代币转入（不考虑价值）
- 📱 通过 Webhook 实时推送通知
- 🔄 记录余额数据，支持断点续传
- 🌐 支持代理访问
- ⚡ 异步处理，高效稳定
- ⏰ 每 10 分钟检查一次

## 工作原理

1. **余额记录**: 每次检查时获取指定地址的指定代币余额
2. **变化检测**: 与上次记录的余额进行比较
3. **转入检测**: 如果余额增加且达到设定阈值，发送通知
4. **数据持久化**: 将余额记录保存到文件，下次启动时继续

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

创建 `.env` 文件并配置以下参数：

```env
# BSC API 密钥 (从 https://bscscan.com/apis 获取)
BSC_API_KEY=your_bscscan_api_key_here

# Webhook URL (钉钉机器人或企业微信机器人)
WEBHOOK_URL=https://your-webhook-url-here

# 代理设置 (可选)
USE_PROXY=false
PROXY_URL=

# 监听的地址列表 (用逗号分隔)
MONITOR_ADDRESSES=0x1234567890abcdef,0xabcdef1234567890

# 监听的代币合约地址 (用逗号分隔)
MONITOR_TOKENS=0x55d398326f99059fF775485246999027B3197955,0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d

# 转入数额阈值 (原始数量，不考虑小数点)
TRANSFER_AMOUNT_THRESHOLD=1000000000000000000

# 检查间隔 (秒，默认 600 = 10分钟)
CHECK_INTERVAL=600
```

## 代币合约地址示例

| 代币 | 合约地址 |
|------|----------|
| USDT | 0x55d398326f99059fF775485246999027B3197955 |
| USDC | 0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d |
| BUSD | 0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56 |
| BNB | 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c |

## 使用方法

```bash
python main.py
```

## 项目结构

```
bsc-evm-monitor/
├── main.py                 # 主程序
├── config.py               # 配置文件
├── webhook.py              # Webhook 发送模块
├── requirements.txt        # 依赖包列表
├── balance_records.json    # 余额记录文件 (自动生成)
├── .env                    # 环境变量配置
└── README.md              # 项目说明
```

## 通知消息格式

```
🚨 检测到代币转入！

地址: 0x1234567890abcdef...
代币: Tether USD (USDT)
转入数量: 1,000.000000 USDT
当前余额: 5,000.000000 USDT
代币合约: 0x55d398326f99059fF775485246999027B3197955
检测时间: 2024-01-01 12:00:00
BSC 浏览器: https://bscscan.com/token/0x55d398326f99059fF775485246999027B3197955?a=0x1234567890abcdef...
```

## 运行日志示例

```
🚀 开始监听 2 个地址的 2 种代币...
📍 监听地址: ['0x1234567890abcdef', '0xabcdef1234567890']
🎯 监听代币: ['0x55d398326f99059fF775485246999027B3197955', '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d']
💰 转入阈值: 1000000000000000000
⏰ 检查间隔: 10 分钟
------------------------------------------------------------

🔍 开始检查... (2024-01-01 12:00:00)
📊 余额无变化: 0x1234567890abcdef (0x55d39832...) = 5000000000
📈 余额增加: 0x1234567890abcdef (0x8AC76a51...) +2000000000
✅ 发送通知: 0x1234567890abcdef 转入 2.000000 USDC
📊 余额无变化: 0xabcdef1234567890 (0x55d39832...) = 0
📊 余额无变化: 0xabcdef1234567890 (0x8AC76a51...) = 0
✅ 本轮检查完成，等待 10 分钟...
```

## 注意事项

1. **API 密钥**: 需要有效的 BSCScan API 密钥
2. **代币合约**: 必须提供正确的代币合约地址
3. **阈值设置**: 阈值为原始数量，不考虑小数点位数
4. **数据持久化**: 余额记录会保存到 `balance_records.json` 文件
5. **首次运行**: 第一次运行时会记录当前余额作为基准
6. **网络要求**: 确保能够访问 BSCScan API

## 故障排除

- **API 密钥错误**: 检查 `.env` 文件中的 `BSC_API_KEY`
- **Webhook 发送失败**: 检查网络连接和 `WEBHOOK_URL` 配置
- **代币信息获取失败**: 确认代币合约地址正确
- **余额获取失败**: 检查地址格式和网络连接
- **配置项为空**: 检查 `.env` 文件中的配置项格式

## 高级配置

### 自定义阈值计算

不同代币的小数点位数不同，设置阈值时需要考虑：

```
# 对于 USDT (6位小数)，监听 1000 USDT 转入
TRANSFER_AMOUNT_THRESHOLD=1000000000

# 对于 BNB (18位小数)，监听 1 BNB 转入  
TRANSFER_AMOUNT_THRESHOLD=1000000000000000000
```

### 批量监听配置

```env
# 监听多个地址
MONITOR_ADDRESSES=0xaddr1,0xaddr2,0xaddr3

# 监听多种代币
MONITOR_TOKENS=0xtoken1,0xtoken2,0xtoken3
```

每个地址的每种代币都会被独立监听和记录。