## ✅ 已完成

使用 python + bscscan (在.env文件中配置) 实现一个监听指定的EVM地址列表中是否有指定数额的 ERC20 TOKEN 转入，通过余额变化检测，每 10 分钟执行一次，如果有则使用 webhook 推送。

## 功能特点

- ✅ 基于余额变化的监听机制
- ✅ 支持多地址、多代币监听
- ✅ 指定数额阈值检测（不考虑价值）
- ✅ 每 10 分钟自动检查
- ✅ 余额记录持久化
- ✅ Webhook 通知推送
- ✅ 异步处理，高效稳定

## 使用方法

1. 复制 `env.example` 为 `.env` 并配置参数
2. 安装依赖：`pip install -r requirements.txt`
3. 运行：`python main.py`
