# EVM 合约监听与解析技术指南

## 📋 文档概述

本文档详细介绍如何正确监听和解析 EVM 兼容链上的智能合约事件，特别是 ERC20 代币转账事件。涵盖从区块链数据获取、时间窗口控制、交易解析到数据去重的完整技术方案。

## 🎯 核心目标

- **精确监听**: 准确捕获指定时间窗口内的代币转账事件
- **高效解析**: 快速提取和分析合约交易数据
- **智能去重**: 避免重复处理相同的合约地址
- **多链支持**: 兼容不同 EVM 链的特性差异

---

## 📚 目录

1. [区块链监听原理](#1-区块链监听原理)
2. [Etherscan API 使用](#2-etherscan-api-使用)
3. [时间窗口与区块号控制](#3-时间窗口与区块号控制)
4. [ERC20 代币交易解析](#4-erc20-代币交易解析)
5. [数据缓存与去重策略](#5-数据缓存与去重策略)
6. [多链监听架构](#6-多链监听架构)
7. [最佳实践与优化](#7-最佳实践与优化)
8. [常见问题与解决方案](#8-常见问题与解决方案)

---

## 1. 区块链监听原理

### 1.1 EVM 区块链基础

#### 区块结构
```
区块链
├── 区块 #1000000
│   ├── 区块时间戳: 1234567890
│   ├── 交易 #1
│   ├── 交易 #2
│   └── ...
├── 区块 #1000001
└── ...
```

#### 关键概念
- **区块号 (Block Number)**: 区块在链上的唯一序号
- **区块时间戳 (Timestamp)**: 区块生成的 Unix 时间戳
- **交易哈希 (Transaction Hash)**: 交易的唯一标识符
- **合约地址 (Contract Address)**: ERC20 代币的合约地址

### 1.2 不同链的出块特性

| 链名称 | Chain ID | 平均出块时间 | 10分钟区块数 | API 端点 |
|--------|----------|-------------|-------------|----------|
| Ethereum | 1 | ~12秒 | ~50 | api.etherscan.io |
| BSC | 56 | ~3秒 | ~200 | api.bscscan.com |
| Base | 8453 | ~2秒 | ~300 | api.basescan.org |

**重要性**: 不同链的出块时间差异影响：
- 时间窗口对应的区块数量
- API 查询的数据量
- 监听频率的设定

---

## 2. Etherscan API 使用

### 2.1 API V2 架构

Etherscan V2 API 统一端点：
```
https://api.etherscan.io/v2/api
```

#### 核心优势
- ✅ 统一的 API 端点
- ✅ 支持 `chainid` 参数实现多链查询
- ✅ 更稳定的服务质量
- ✅ 更完善的错误处理

### 2.2 关键 API 接口

#### 2.2.1 获取代币转账记录

**接口**: `account.tokentx`

**用途**: 获取指定地址的 ERC20 代币转账记录

**请求参数**:
```python
params = {
    'chainid': 56,                      # 链ID
    'module': 'account',                # 模块
    'action': 'tokentx',                # 操作
    'address': '0x...',                 # 目标地址
    'startblock': 12345000,             # 起始区块
    'endblock': 12345500,               # 结束区块
    'page': 1,                          # 页码
    'offset': 10000,                    # 每页记录数
    'sort': 'desc',                     # 排序(降序)
    'apikey': 'YOUR_API_KEY'            # API密钥
}
```

**响应示例**:
```json
{
  "status": "1",
  "message": "OK",
  "result": [
    {
      "blockNumber": "12345100",
      "timeStamp": "1640000000",
      "hash": "0xabc...",
      "from": "0xsender...",
      "to": "0xreceiver...",
      "contractAddress": "0xtoken...",
      "tokenName": "MyToken",
      "tokenSymbol": "MTK",
      "tokenDecimal": "18",
      "value": "1000000000000000000"
    }
  ]
}
```

#### 2.2.2 根据时间戳获取区块号

**接口**: `block.getblocknobytime`

**用途**: 将时间戳转换为最接近的区块号

**请求参数**:
```python
params = {
    'chainid': 56,
    'module': 'block',
    'action': 'getblocknobytime',
    'timestamp': 1640000000,            # 目标时间戳
    'closest': 'before',                # 取之前最接近的区块
    'apikey': 'YOUR_API_KEY'
}
```

**响应示例**:
```json
{
  "status": "1",
  "message": "OK",
  "result": "12345100"
}
```

#### 2.2.3 获取最新区块号

**接口**: `proxy.eth_blockNumber`

**用途**: 获取链上最新的区块号

**请求参数**:
```python
params = {
    'chainid': 56,
    'module': 'proxy',
    'action': 'eth_blockNumber',
    'apikey': 'YOUR_API_KEY'
}
```

**响应示例**:
```json
{
  "jsonrpc": "2.0",
  "result": "0xbc614e",              # 十六进制格式
  "id": 1
}
```

**注意**: 结果是十六进制，需要转换：
```python
latest_block = int(response['result'], 16)  # 转为十进制
```

#### 2.2.4 获取区块详细信息

**接口**: `proxy.eth_getBlockByNumber`

**用途**: 获取指定区块的详细信息（包括时间戳）

**请求参数**:
```python
params = {
    'chainid': 56,
    'module': 'proxy',
    'action': 'eth_getBlockByNumber',
    'tag': hex(12345100),              # 区块号（十六进制）
    'boolean': 'false',                # 不包含完整交易
    'apikey': 'YOUR_API_KEY'
}
```

#### 2.2.5 获取代币余额

**接口**: `account.tokenbalance`

**用途**: 获取指定地址的代币余额

**请求参数**:
```python
params = {
    'chainid': 56,
    'module': 'account',
    'action': 'tokenbalance',
    'contractaddress': '0xtoken...',   # 代币合约地址
    'address': '0xwallet...',          # 钱包地址
    'tag': 'latest',                   # 最新状态
    'apikey': 'YOUR_API_KEY'
}
```

### 2.3 API 限制与优化

#### 限制说明
- **免费账户**: 5 次/秒，10,000 次/天
- **专业账户**: 更高的限制

#### 优化策略

**1. 多密钥轮换**
```python
import random

def get_random_api_key():
    """随机选择一个API密钥"""
    return random.choice(API_KEYS)
```

**2. 请求间隔控制**
```python
async def wait_for_rate_limit():
    """确保请求间隔"""
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last
        await asyncio.sleep(wait_time)
    
    last_request_time = time.time()
```

**3. 错误重试机制**
```python
async def make_api_request(params, retry_count=0):
    """带重试的API请求"""
    try:
        data = await session.get(API_URL, params=params)
        
        if data.get('status') == '0':
            result = data.get('result', '')
            
            # 检测限制错误
            if 'rate limit' in result.lower():
                if retry_count < MAX_RETRIES:
                    await asyncio.sleep(RATE_LIMIT_RETRY_DELAY)
                    return await make_api_request(params, retry_count + 1)
        
        return data
    except Exception as e:
        log(f"API请求失败: {e}")
        return None
```

---

## 3. 时间窗口与区块号控制

### 3.1 为什么需要精确的区块范围

**问题场景**:
- ❌ 不使用区块范围：每次查询返回所有历史数据
- ❌ 使用时间戳过滤：API 仍然返回大量数据，效率低
- ✅ 使用区块号范围：只查询需要的数据，高效准确

### 3.2 时间戳到区块号的转换

#### 策略 1: API 查询（推荐）

```python
async def get_block_by_timestamp(timestamp):
    """通过API获取区块号"""
    params = {
        'chainid': chain_id,
        'module': 'block',
        'action': 'getblocknobytime',
        'timestamp': int(timestamp),
        'closest': 'before',
    }
    
    data = await make_api_request(params)
    if data and data.get('status') == '1':
        return int(data.get('result', 0))
    
    return None
```

**优点**:
- ✅ 最准确的结果
- ✅ 考虑了实际出块时间的波动

**缺点**:
- ⚠️ 需要额外的API调用
- ⚠️ 可能受限于API限制

#### 策略 2: 时间估算（备用）

```python
async def estimate_block_by_average_time(target_timestamp):
    """基于平均出块时间估算"""
    # 获取最新区块
    latest_block = await get_latest_block_number()
    latest_block_info = await get_block_info(latest_block)
    latest_timestamp = latest_block_info['timestamp']
    
    # 计算时间差
    time_diff = latest_timestamp - target_timestamp
    
    # 平均出块时间
    avg_block_times = {
        1: 12,      # Ethereum
        56: 3,      # BSC
        8453: 2     # Base
    }
    avg_block_time = avg_block_times.get(chain_id, 12)
    
    # 估算区块号
    blocks_to_go_back = int(time_diff / avg_block_time)
    estimated_block = latest_block - blocks_to_go_back
    
    return estimated_block
```

**优点**:
- ✅ 不依赖特定API接口
- ✅ 计算速度快

**缺点**:
- ⚠️ 可能存在误差
- ⚠️ 需要额外获取最新区块信息

### 3.3 实战：10分钟时间窗口监听

#### 完整流程

```python
async def get_recent_erc20_tokens(address, minutes_ago=10):
    """获取最近N分钟的代币交易"""
    
    # 1. 计算时间范围
    current_time = int(time.time())
    start_timestamp = current_time - (minutes_ago * 60)
    
    # 2. 获取对应的区块号
    start_block = await get_block_by_timestamp(start_timestamp)
    if start_block is None:
        # 备用策略
        start_block = await estimate_block_by_average_time(minutes_ago)
    
    # 3. 获取最新区块号
    latest_block = await get_latest_block_number()
    
    # 4. 确保区块范围合理
    if start_block > latest_block:
        start_block = latest_block
    
    # 5. 查询代币交易
    params = {
        'chainid': chain_id,
        'module': 'account',
        'action': 'tokentx',
        'address': address,
        'startblock': start_block,
        'endblock': latest_block,
        'sort': 'desc',
    }
    
    data = await make_api_request(params)
    transactions = data.get('result', [])
    
    # 6. 额外的时间戳验证（双重保险）
    filtered_transactions = []
    for tx in transactions:
        tx_timestamp = int(tx.get('timeStamp', 0))
        if tx_timestamp >= start_timestamp:
            filtered_transactions.append(tx)
    
    return filtered_transactions
```

#### 流程图

```
开始
  ↓
获取当前时间戳
  ↓
计算目标时间戳 (当前时间 - 10分钟)
  ↓
┌─────────────────────────────────┐
│  策略1: API查询区块号            │
│  block.getblocknobytime         │
└─────────────────────────────────┘
  ↓ 成功？
  ├─ 是 → 使用API返回的区块号
  └─ 否 → ┌─────────────────────────┐
          │  策略2: 时间估算         │
          │  基于平均出块时间计算    │
          └─────────────────────────┘
  ↓
获取最新区块号
  ↓
验证区块范围合理性
  ↓
调用 account.tokentx API
  ↓
额外的时间戳过滤（双重保险）
  ↓
返回结果
```

---

## 4. ERC20 代币交易解析

### 4.1 交易数据结构

#### 原始交易数据
```json
{
  "blockNumber": "12345100",
  "timeStamp": "1640000000",
  "hash": "0x123abc...",
  "from": "0xsender123...",
  "to": "0xreceiver456...",
  "contractAddress": "0xtoken789...",
  "tokenName": "SafeMoon",
  "tokenSymbol": "SAFEMOON",
  "tokenDecimal": "18",
  "value": "1000000000000000000000000"
}
```

### 4.2 关键字段解析

| 字段 | 类型 | 说明 | 处理方式 |
|------|------|------|----------|
| `blockNumber` | string | 区块号 | 转为 int |
| `timeStamp` | string | Unix时间戳 | 转为 int，用于时间过滤 |
| `hash` | string | 交易哈希 | 用于追踪和去重 |
| `from` | string | 发送地址 | 转小写规范化 |
| `to` | string | 接收地址 | 转小写规范化 |
| `contractAddress` | string | 代币合约地址 | **关键字段**，用于去重 |
| `tokenName` | string | 代币名称 | 可能为空 |
| `tokenSymbol` | string | 代币符号 | 可能为空 |
| `tokenDecimal` | string | 精度 | 默认 18 |
| `value` | string | 原始数量 | 需要除以 10^decimals |

### 4.3 转入交易过滤

**核心逻辑**：只关注目标地址作为接收方的交易

```python
def filter_incoming_transactions(address, transactions):
    """过滤转入交易"""
    incoming_txs = []
    
    for tx in transactions:
        # 只保留 to 地址是目标地址的交易
        if tx.get('to', '').lower() == address.lower():
            incoming_txs.append(tx)
    
    return incoming_txs
```

**为什么这样做**：
- ✅ 避免误报：不关注用户的转出行为
- ✅ 精确监听：只监听有新代币转入的情况
- ✅ 减少噪音：过滤掉大量无关交易

### 4.4 代币数量格式化

#### 原始值转换

ERC20 代币使用最小单位存储，需要根据精度转换：

```python
def format_token_amount(raw_value, decimals):
    """格式化代币数量
    
    Args:
        raw_value: 原始值（字符串或整数）
        decimals: 代币精度
        
    Returns:
        格式化后的数量
    """
    amount = int(raw_value)
    formatted = amount / (10 ** decimals)
    
    # 如果是整数，不显示小数点
    if formatted == int(formatted):
        return int(formatted)
    
    return formatted
```

#### 示例

```python
# 代币精度为 18
raw_value = "1000000000000000000000000"
decimals = 18

formatted = format_token_amount(raw_value, decimals)
# 结果: 1000000
```

### 4.5 提取唯一代币合约

#### 合约去重逻辑

```python
def extract_unique_tokens(transactions):
    """从交易列表中提取唯一的代币信息"""
    token_info = {}
    
    for tx in transactions:
        contract = tx.get('contractAddress', '').lower()
        
        # 跳过已处理的合约
        if not contract or contract in token_info:
            continue
        
        # 提取代币信息
        token_obj = {
            'contract': contract,
            'token_name': tx.get('tokenName', 'Unknown'),
            'token_symbol': tx.get('tokenSymbol', 'Unknown'),
            'token_decimals': int(tx.get('tokenDecimal', 18)),
            'tx_hash': tx.get('hash', ''),
            'tx_timestamp': int(tx.get('timeStamp', 0)),
            'block_number': int(tx.get('blockNumber', 0))
        }
        
        token_info[contract] = token_obj
    
    return list(token_info.values())
```

**关键点**：
- 使用合约地址作为唯一标识
- 所有地址统一转为小写
- 保留第一笔交易的详细信息

---

## 5. 数据缓存与去重策略

### 5.1 缓存设计理念

#### 设计目标
- ✅ **零重复告警**: 已处理的合约地址不再触发
- ✅ **高性能**: 快速查找和比对
- ✅ **简洁**: 最小化存储空间
- ✅ **链隔离**: 不同链独立管理

#### 旧格式 vs 新格式

**旧格式**（复杂、低效）:
```json
{
  "0xwallet1": [
    {
      "token": "SafeMoon (SAFEMOON)",
      "contract": "0xtoken1",
      "number": 2500000,
      "twitter_processed": false
    }
  ],
  "0xwallet2": [...]
}
```

**新格式**（简洁、高效）:
```json
[
  "0xtoken1",
  "0xtoken2",
  "0xtoken3"
]
```

### 5.2 缓存文件管理

#### 文件命名规则

```
token_records_chain_{chain_id}.json
```

**示例**:
- `token_records_chain_1.json` - Ethereum
- `token_records_chain_56.json` - BSC
- `token_records_chain_8453.json` - Base

#### 加载缓存

```python
def load_token_records(chain_id):
    """加载代币记录"""
    records_file = f'token_records_chain_{chain_id}.json'
    
    try:
        with open(records_file, 'r') as f:
            data = json.load(f)
            
            # 验证格式
            if isinstance(data, list):
                # 确保所有地址都是小写且格式正确
                contract_list = []
                for addr in data:
                    if isinstance(addr, str) and \
                       addr.startswith('0x') and \
                       len(addr) == 42:
                        contract_list.append(addr.lower())
                
                return contract_list
            else:
                log("缓存文件格式错误")
                return []
                
    except FileNotFoundError:
        log("缓存文件不存在，创建新文件")
        return []
    except json.JSONDecodeError:
        log("缓存文件JSON格式错误")
        return []
```

#### 保存缓存

```python
def save_token_records(chain_id, contract_list):
    """保存代币记录"""
    records_file = f'token_records_chain_{chain_id}.json'
    
    with open(records_file, 'w') as f:
        json.dump(contract_list, f, indent=2)
```

### 5.3 去重处理流程

#### 完整流程

```python
async def check_new_tokens(address):
    """检查新代币"""
    
    # 1. 获取最近的代币交易
    recent_transactions = await get_recent_erc20_tokens(address)
    
    # 2. 过滤转入交易
    incoming_txs = filter_incoming_transactions(address, recent_transactions)
    
    # 3. 提取唯一的代币合约
    unique_tokens = extract_unique_tokens(incoming_txs)
    
    # 4. 与缓存比对，找出新合约
    new_tokens = []
    for token in unique_tokens:
        contract = token['contract'].lower()
        
        # 检查是否在缓存中
        if contract not in token_records:
            new_tokens.append(token)
    
    # 5. 处理新代币
    processed_contracts = []
    for token in new_tokens:
        contract = token['contract'].lower()
        
        # 获取余额
        balance = await get_token_balance(address, contract)
        
        if balance > 0:
            # 获取详细信息
            token_info = await get_token_info(contract)
            formatted_amount = format_token_amount(balance, token_info['decimals'])
            
            # 检查阈值
            if is_within_threshold(formatted_amount):
                # 发送告警和推文
                await process_alpha_event(token_info)
        
        # 无论如何都标记为已处理
        processed_contracts.append(contract)
    
    # 6. 更新缓存
    if processed_contracts:
        token_records.extend(processed_contracts)
        save_token_records(chain_id, token_records)
    
    return new_tokens
```

#### 去重流程图

```
获取最近交易
  ↓
过滤转入交易
  ↓
提取唯一合约地址
  ↓
┌─────────────────────┐
│  检查缓存            │
│  contract in cache? │
└─────────────────────┘
  ↓
  ├─ 是 → 跳过（已处理）
  └─ 否 → ┌──────────────────┐
          │  新代币处理       │
          │  - 获取余额       │
          │  - 检查阈值       │
          │  - 发送告警/推文  │
          └──────────────────┘
  ↓
添加到缓存（无论是否发送推文）
  ↓
保存缓存文件
```

### 5.4 关键设计决策

#### 为什么缓存合约地址而不是钱包地址？

**方案对比**:

| 方案 | 优点 | 缺点 |
|------|------|------|
| 按钱包缓存 | 可以追踪每个钱包的历史 | 多钱包重复处理，缓存庞大 |
| **按合约缓存** | **全局去重，缓存精简** | **无法区分不同钱包** |

**选择理由**:
- ✅ 我们关注的是"新代币首次出现"，不是"钱包的历史"
- ✅ 全局去重避免重复告警
- ✅ 缓存大小可控

#### 为什么无论推文是否成功都标记为已处理？

**理由**:
1. **避免无限重试**: 如果推文API临时失败，不应该一直重试
2. **防止垃圾告警**: 已知的合约不应该重复触发
3. **关注新事件**: 专注于发现新的代币事件

---

## 6. 多链监听架构

### 6.1 架构设计

#### 类结构

```
MultiChainMonitor (多链监听器)
  ├── NewTokenMonitor (Ethereum)
  ├── NewTokenMonitor (BSC)
  └── NewTokenMonitor (Base)
```

#### 实现代码

```python
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
    
    async def run_all_monitors(self):
        """运行所有链的监听器"""
        if not self.enabled_chains:
            log("没有启用的链")
            return
        
        # 创建所有监听器的任务
        tasks = []
        for chain_id in self.enabled_chains:
            monitor = self.monitors[chain_id]
            task = asyncio.create_task(monitor.run_monitor())
            tasks.append(task)
        
        # 并发执行所有任务
        await asyncio.gather(*tasks)
```

### 6.2 链配置管理

#### 配置结构

```python
CHAINS_CONFIG = {
    1: {
        'name': 'Ethereum Mainnet',
        'api_url': 'https://api.etherscan.io/v2/api',
        'explorer_url': 'https://etherscan.io',
        'enabled': True
    },
    56: {
        'name': 'BNB Smart Chain Mainnet',
        'api_url': 'https://api.etherscan.io/v2/api',
        'explorer_url': 'https://bscscan.com',
        'enabled': True
    },
    8453: {
        'name': 'Base Mainnet',
        'api_url': 'https://api.etherscan.io/v2/api',
        'explorer_url': 'https://basescan.org',
        'enabled': False  # 可以选择性启用
    }
}
```

#### 动态获取配置

```python
def get_api_url(chain_id):
    """获取链的API URL"""
    return CHAINS_CONFIG.get(chain_id, {}).get('api_url', '')

def get_explorer_url(chain_id):
    """获取链的浏览器URL"""
    return CHAINS_CONFIG.get(chain_id, {}).get('explorer_url', '')

def get_chain_name(chain_id):
    """获取链的名称"""
    return CHAINS_CONFIG.get(chain_id, {}).get('name', 'Unknown Chain')
```

### 6.3 链隔离与数据管理

#### 数据隔离原则

- ✅ 每个链独立的缓存文件
- ✅ 每个链独立的监听器实例
- ✅ 每个链独立的API限制控制

#### 好处

1. **避免冲突**: 不同链的合约地址可能重复
2. **灵活控制**: 可以独立启用/禁用某条链
3. **性能优化**: 并发监听多条链
4. **故障隔离**: 某条链出错不影响其他链

---

## 7. 最佳实践与优化

### 7.1 API 调用优化

#### 1. 批量处理

**原则**: 尽量减少API调用次数

```python
# ❌ 不好的做法：每个交易都查询一次
for tx in transactions:
    balance = await get_token_balance(address, tx['contract'])

# ✅ 好的做法：先去重，再查询
unique_contracts = set(tx['contract'] for tx in transactions)
for contract in unique_contracts:
    balance = await get_token_balance(address, contract)
```

#### 2. 并发请求

**原则**: 独立的请求可以并发执行

```python
# ✅ 并发获取多个地址的交易
tasks = [
    get_recent_erc20_tokens(addr) 
    for addr in MONITOR_ADDRESSES
]
results = await asyncio.gather(*tasks)
```

**注意**: 需要控制并发数量，避免触发API限制

#### 3. 缓存利用

**原则**: 能从缓存获取的数据不要重复查询

```python
# 代币信息缓存
token_info_cache = {}

async def get_token_info_cached(contract):
    """带缓存的代币信息获取"""
    if contract in token_info_cache:
        return token_info_cache[contract]
    
    info = await get_token_info_from_api(contract)
    token_info_cache[contract] = info
    return info
```

### 7.2 时间窗口优化

#### 1. 动态调整时间窗口

```python
# 根据链的出块速度调整时间窗口
time_window_config = {
    1: 10,      # Ethereum: 10分钟
    56: 5,      # BSC: 5分钟（出块快）
    8453: 5     # Base: 5分钟（出块快）
}

time_window = time_window_config.get(chain_id, 10)
```

#### 2. 检查间隔设置

```python
# 检查间隔应该略大于时间窗口，避免重复监听
# 推荐: CHECK_INTERVAL = TIME_WINDOW + 1分钟

TIME_WINDOW_MINUTES = 10
CHECK_INTERVAL = (TIME_WINDOW_MINUTES + 1) * 60  # 11分钟
```

### 7.3 错误处理

#### 1. 分级错误处理

```python
async def safe_api_call(func, *args, **kwargs):
    """安全的API调用包装"""
    try:
        return await func(*args, **kwargs)
    except asyncio.TimeoutError:
        log("API调用超时，将重试")
        return None
    except aiohttp.ClientConnectorError:
        log("网络连接错误")
        return None
    except Exception as e:
        log(f"未知错误: {e}")
        return None
```

#### 2. 降级策略

```python
async def get_block_with_fallback(timestamp):
    """带降级的区块号获取"""
    # 策略1: API查询
    block = await get_block_by_timestamp(timestamp)
    if block:
        return block
    
    # 策略2: 时间估算
    block = await estimate_block_by_average_time(timestamp)
    if block:
        return block
    
    # 策略3: 使用保守估计
    return get_conservative_estimate(timestamp)
```

### 7.4 日志记录

#### 日志分级

```python
# 关键操作
log(f"🚀 开始监听 {chain_name}...")

# 正常信息
log(f"📊 获取到 {len(transactions)} 笔交易")

# 警告
log(f"⚠️ API响应慢，耗时 {elapsed}秒")

# 错误
log(f"❌ 获取区块号失败: {error}")

# 成功
log(f"✅ 处理完成，发现 {count} 个新代币")
```

---

## 8. 常见问题与解决方案

### 8.1 API 限制问题

#### 问题: Max rate limit reached

**原因**: API调用频率过高

**解决方案**:

1. **增加请求间隔**
```python
MIN_REQUEST_INTERVAL = 1.5  # 从1秒增加到1.5秒
```

2. **使用多个API密钥**
```env
ETHERSCAN_API_KEYS=key1,key2,key3
```

3. **减少查询范围**
```python
# 减少监听地址数量
MONITOR_ADDRESSES = ["0xaddr1", "0xaddr2"]  # 只监听重要地址

# 增加检查间隔
CHECK_INTERVAL = 600  # 10分钟一次
```

### 8.2 区块号不准确

#### 问题: 获取的区块范围不对应时间窗口

**原因**: 
- API `getblocknobytime` 返回错误
- 链重组导致区块时间异常
- 平均出块时间估算不准

**解决方案**:

1. **双重验证**
```python
# 使用区块号查询后，额外进行时间戳过滤
filtered_transactions = [
    tx for tx in transactions
    if int(tx.get('timeStamp', 0)) >= start_timestamp
]
```

2. **使用更保守的估算**
```python
# 增加安全边际
safe_start_block = estimated_block - 50  # 往前多查50个区块
```

### 8.3 重复告警

#### 问题: 同一个代币触发多次告警

**原因**:
- 缓存未及时保存
- 多实例同时运行
- 缓存文件被删除或损坏

**解决方案**:

1. **及时保存缓存**
```python
# 每次处理后立即保存
if new_processed_contracts:
    token_records.extend(new_processed_contracts)
    save_token_records()  # 立即保存
```

2. **加锁机制**
```python
import fcntl

def save_token_records_safe(data):
    """线程安全的缓存保存"""
    with open(records_file, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(data, f, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

3. **使用数据库**
```python
# 对于多实例场景，考虑使用Redis或数据库
import redis

redis_client = redis.Redis()

def is_processed(contract):
    """检查合约是否已处理"""
    return redis_client.sismember('processed_contracts', contract)

def mark_processed(contract):
    """标记合约为已处理"""
    redis_client.sadd('processed_contracts', contract)
```

### 8.4 代币信息获取失败

#### 问题: tokenName 和 tokenSymbol 为空

**原因**:
- 合约未实现标准的 ERC20 接口
- 合约是代理合约
- API 数据不完整

**解决方案**:

1. **降级处理**
```python
def get_token_display_name(token_info):
    """获取代币显示名称（带降级）"""
    name = token_info.get('tokenName', '').strip()
    symbol = token_info.get('tokenSymbol', '').strip()
    contract = token_info.get('contractAddress', '')
    
    if name and symbol:
        return f"{name} ({symbol})"
    elif symbol:
        return symbol
    elif name:
        return name
    else:
        return f"Unknown Token ({contract[:10]}...)"
```

2. **从交易历史获取**
```python
async def get_token_info_from_tx(contract):
    """从交易记录中获取代币信息"""
    params = {
        'module': 'account',
        'action': 'tokentx',
        'contractaddress': contract,
        'page': 1,
        'offset': 1,
        'sort': 'desc'
    }
    
    data = await make_api_request(params)
    if data and data.get('result'):
        tx = data['result'][0]
        return {
            'name': tx.get('tokenName', 'Unknown'),
            'symbol': tx.get('tokenSymbol', 'Unknown'),
            'decimals': int(tx.get('tokenDecimal', 18))
        }
    
    return None
```

### 8.5 内存占用过高

#### 问题: 长时间运行后内存占用不断增加

**原因**:
- 交易数据未释放
- 缓存数据无限增长
- 日志文件过大

**解决方案**:

1. **限制数据结构大小**
```python
# 限制缓存大小，定期清理旧数据
MAX_CACHE_SIZE = 10000

def trim_cache_if_needed():
    """裁剪缓存"""
    if len(token_records) > MAX_CACHE_SIZE:
        # 保留最新的记录
        token_records = token_records[-MAX_CACHE_SIZE:]
        save_token_records()
```

2. **及时释放资源**
```python
# 处理完成后清理
async def process_transactions(transactions):
    try:
        # 处理逻辑
        ...
    finally:
        # 清理
        transactions.clear()
        del transactions
```

3. **日志轮转**
```python
# 配置日志轮转
handler = RotatingFileHandler(
    'logs/monitor.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

---

## 9. 性能指标与监控

### 9.1 关键指标

#### 监控指标

| 指标 | 说明 | 正常范围 | 告警阈值 |
|------|------|---------|---------|
| API调用延迟 | 单次API请求耗时 | < 2秒 | > 5秒 |
| 处理周期时长 | 完成一轮检查的时间 | < 1分钟 | > 3分钟 |
| 内存占用 | 进程内存使用量 | < 100MB | > 500MB |
| 缓存文件大小 | token_records文件大小 | < 10KB | > 1MB |
| 新代币发现数 | 每轮发现的新代币数量 | 0-5个 | > 10个 |

#### 记录指标

```python
import time

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {
            'api_calls': 0,
            'api_call_time': [],
            'processing_time': [],
            'tokens_found': 0
        }
    
    async def track_api_call(self, func, *args, **kwargs):
        """追踪API调用"""
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        
        self.metrics['api_calls'] += 1
        self.metrics['api_call_time'].append(elapsed)
        
        return result
    
    def report(self):
        """生成性能报告"""
        avg_api_time = sum(self.metrics['api_call_time']) / len(self.metrics['api_call_time'])
        
        log(f"📊 性能报告:")
        log(f"  API调用次数: {self.metrics['api_calls']}")
        log(f"  平均API延迟: {avg_api_time:.2f}秒")
        log(f"  发现新代币: {self.metrics['tokens_found']}个")
```

---

## 10. 总结与检查清单

### 10.1 核心要点总结

✅ **精确的时间窗口控制**
- 使用区块号范围而非时间戳过滤
- 双重策略确保区块号准确性

✅ **高效的数据解析**
- 只关注转入交易
- 基于合约地址去重

✅ **智能的缓存机制**
- 简化的合约地址列表格式
- 全局去重避免重复告警

✅ **稳定的API调用**
- 多密钥轮换
- 限制控制和重试机制

✅ **多链架构支持**
- 独立的监听器实例
- 隔离的数据管理

### 10.2 实施检查清单

#### 配置检查
- [ ] API密钥已配置且有效
- [ ] 监听地址列表正确
- [ ] 阈值范围合理设置
- [ ] 时间窗口和检查间隔配置正确

#### 功能检查
- [ ] 能够正确获取最新区块号
- [ ] 时间戳能转换为区块号
- [ ] 代币交易能正确解析
- [ ] 转入交易过滤正常

#### 缓存检查
- [ ] 缓存文件能正常加载
- [ ] 新合约能正确添加到缓存
- [ ] 缓存持久化正常
- [ ] 已处理合约不会重复触发

#### 性能检查
- [ ] API调用延迟在正常范围
- [ ] 处理周期时长合理
- [ ] 内存占用稳定
- [ ] 无明显的性能下降

#### 监控检查
- [ ] 日志输出正常
- [ ] 关键指标被记录
- [ ] 异常能被及时发现
- [ ] Webhook通知正常

---

## 附录

### A. 术语表

| 术语 | 解释 |
|------|------|
| EVM | Ethereum Virtual Machine，以太坊虚拟机 |
| ERC20 | 以太坊代币标准 |
| Block Number | 区块号，区块在链上的序号 |
| Timestamp | 时间戳，Unix时间戳 |
| Contract Address | 合约地址，智能合约的唯一标识 |
| Transaction Hash | 交易哈希，交易的唯一标识 |
| Token Decimals | 代币精度，表示小数位数 |
| API Rate Limit | API速率限制 |

### B. 相关资源

- [Etherscan API 文档](https://docs.etherscan.io/)
- [BSCScan API 文档](https://docs.bscscan.com/)
- [BaseScan API 文档](https://docs.basescan.org/)
- [ERC20 标准](https://eips.ethereum.org/EIPS/eip-20)
- [Ethereum 区块浏览器](https://etherscan.io/)

### C. 代码示例仓库

完整的代码示例请参考：
```
https://github.com/your-repo/bsc-evm-monitor
```

---

**文档版本**: v1.0  
**最后更新**: 2025-10-05  
**维护者**: EVM Monitor Team
