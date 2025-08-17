
2025-08-17 10:31:02 [INFO] ❌ API请求失败: Invalid variable type: value should be str, int or float, got None of type <class 'NoneType'> (module=account, action=tokentx)


Traceback (most recent call last):


File "/app/main.py", line 213, in make_api_request


async with self.session.get(self.api_url, params=params, proxy=self.proxy, timeout=30) as response:


File "/usr/local/lib/python3.9/site-packages/aiohttp/client.py", line 1187, in __aenter__


self._resp = await self._coro


File "/usr/local/lib/python3.9/site-packages/aiohttp/client.py", line 541, in _request


req = self._request_class(


File "/usr/local/lib/python3.9/site-packages/aiohttp/client_reqrep.py", line 302, in __init__


url2 = url.with_query(params)


File "/usr/local/lib/python3.9/site-packages/yarl/_url.py", line 1185, in with_query


query = get_str_query(*args, **kwargs) or ""


File "/usr/local/lib/python3.9/site-packages/yarl/_query.py", line 97, in get_str_query


return get_str_query_from_sequence_iterable(query.items())


File "/usr/local/lib/python3.9/site-packages/yarl/_query.py", line 50, in get_str_query_from_sequence_iterable


pairs = [


File "/usr/local/lib/python3.9/site-packages/yarl/_query.py", line 51, in <listcomp>


f"{quoter(k)}={quoter(v if type(v) is str else query_var(v))}"


File "/usr/local/lib/python3.9/site-packages/yarl/_query.py", line 33, in query_var


raise TypeError(


TypeError: Invalid variable type: value should be str, int or float, got None of type <class 'NoneType'>


2025-08-17 10:31:02 [INFO] ❌ 获取最近代币交易失败，跳过此地址

---

2025-08-17 11:31:18 [INFO] ❌ API请求失败: 'list' object has no attribute 'lower' (module=account, action=tokentx)


Traceback (most recent call last):


File "/app/main.py", line 218, in make_api_request


if data.get('status') == '0' and 'rate limit' in data.get('result', '').lower():


AttributeError: 'list' object has no attribute 'lower'


2025-08-17 11:31:18 [INFO] ❌ 

---

2025-08-17 10:31:02 [INFO] ❌ API请求失败: Cannot connect to host api.etherscan.io:443 ssl:default [None] (module=block, action=getblocknobytime)


Traceback (most recent call last):


File "/usr/local/lib/python3.9/site-packages/aiohttp/connector.py", line 1100, in _start_tls_connection


tls_transport = await self._loop.start_tls(


File "/usr/local/lib/python3.9/asyncio/base_events.py", line 1240, in start_tls


await waiter


ConnectionResetError




The above exception was the direct cause of the following exception:




Traceback (most recent call last):


File "/app/main.py", line 213, in make_api_request


async with self.session.get(self.api_url, params=params, proxy=self.proxy, timeout=30) as response:


File "/usr/local/lib/python3.9/site-packages/aiohttp/client.py", line 1187, in __aenter__


self._resp = await self._coro


File "/usr/local/lib/python3.9/site-packages/aiohttp/client.py", line 574, in _request


conn = await self._connector.connect(


File "/usr/local/lib/python3.9/site-packages/aiohttp/connector.py", line 540, in connect


proto = await self._create_connection(req, traces, timeout)


File "/usr/local/lib/python3.9/site-packages/aiohttp/connector.py", line 905, in _create_connection


_, proto = await self._create_proxy_connection(req, traces, timeout)


File "/usr/local/lib/python3.9/site-packages/aiohttp/connector.py", line 1353, in _create_proxy_connection


return await self._start_tls_connection(


File "/usr/local/lib/python3.9/site-packages/aiohttp/connector.py", line 1120, in _start_tls_connection


raise client_error(req.connection_key, exc) from exc


aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host api.etherscan.io:443 ssl:default [None]


2025-08-17 10:31:02 [INFO] ❌ 根据时间戳获取区块号失败


---

