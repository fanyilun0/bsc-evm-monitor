import aiohttp
import asyncio
from config import WEBHOOK_URL, PROXY_URL, USE_PROXY

async def send_message(session, content, headers, proxy):
    """发送单条消息"""
    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    
    try:
        async with session.post(WEBHOOK_URL, json=payload, headers=headers, proxy=proxy) as response:
            if response.status == 200:
                print(f"消息片段发送成功! (长度: {len(content)})")
                return True
            else:
                print(f"消息片段发送失败: {response.status}, {await response.text()}")
                return False
    except Exception as e:
        print(f"消息片段发送出错: {str(e)}")
        return False
