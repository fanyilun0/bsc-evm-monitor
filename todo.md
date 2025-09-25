0. 移除Redis通信的逻辑来调用发推特，改为调用本地接口服务：

1. 发送推文的接口
POST http://127.0.0.1:8008/search/tweets
curl -X 'POST' \
  'http://127.0.0.1:8008/tweet' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "content": "test"
}'

content 可以添加 in_reply_to_tweet_id 这个参数，用来回复推文



2. 查询推文
http://127.0.0.1:8008/search/user_tweets?username=binance&keywords=publicAI&max_results=10
response: 
```json
[
  {
    "id": 1956236227096797200,
    "text": "Binance Alpha is the first platform to feature PublicAI (PUBLIC), with Alpha trading opening on August 15th, 2025, at 07:00 (UTC).\n\nEligible users can claim an airdrop of 430 PUBLIC tokens on the Alpha Events page within 24 hours once trading begins by using Binance Alpha Points. https://t.co/jVPBOoX8MQ",
    "author_id": 877807935493034000,
    "created_at": "2025-08-15T06:07:16+00:00",
    "public_metrics": {
      "retweet_count": 94,
      "reply_count": 203,
      "like_count": 554,
      "quote_count": 25,
      "bookmark_count": 20,
      "impression_count": 498021
    }
  },
  {
    "id": 1955464326443057400,
    "text": "Get ready! Binance Alpha will be the first platform to feature PublicAI (PUBLIC) on August 15th.\n\nEligible users can claim their airdrop using Binance Alpha Points on the Alpha Events page once trading opens. Further details will be announced soon.\n\nPlease stay tuned to Binance’s https://t.co/TTTn5kVfGw",
    "author_id": 877807935493034000,
    "created_at": "2025-08-13T03:00:00+00:00",
    "public_metrics": {
      "retweet_count": 159,
      "reply_count": 232,
      "like_count": 833,
      "quote_count": 33,
      "bookmark_count": 38,
      "impression_count": 524814
    }
  }
]
```
推文id 可以作为发送推文中的 in_reply_to_tweet_id 的属性值

3. 业务逻辑改动：
在监听到后使用 tokenName 和 固定的 binance 进行检索，如果有正确查询到推文， 则对每个推文都进行一次回复

举例说明， 检索这个关键词publicAI，会发送三次推文（三次推文内容是相同的）：
- 发推
- 发两次回复

4. 其中 接口地址是在 config 和 env中进行配置并正确应用


## 获取推文超时处理
由于推特API的限制， 如果在60s没有获取到相关的推文则终止对相关推文的请求；

搜索的关键字需要调整： 拼接 alpha 关键字（如“token alpha”） 来限制查询的推文

对于已经检索过关键字代币， 需要正确缓存，对于已经缓存过的代币，不需要二次检索和发送相关的推文

[
  {
    "id": 1970473813579309300,
    "text": "RT @BinanceWallet: Get ready! Binance Alpha will be the first platform to feature Plasma (XPL) on September 25.\n\nEligible users can claim t…",
    "author_id": 877807935493034000,
    "created_at": "2025-09-23T13:02:21+00:00",
    "public_metrics": {
      "retweet_count": 291,
      "reply_count": 0,
      "like_count": 0,
      "quote_count": 0,
      "bookmark_count": 0,
      "impression_count": 2
    }
  }
]

1. 如果检索到的推文不是最近一周发布的， 则不需要发送任何推文
2. 如果监听到了到新代币的TX，第一时间先缓存， 之后再处理发送推文相关的逻辑； 避免由于发推时产生的错误导致缓存失败
