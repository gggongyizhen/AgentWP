# wait

## 题目信息

- 类型：Web
- 题目状态：阶段性分析
- 目标：https://bluehens-wait.chals.io/
- 核心疑点：`openresty` 反向代理到 `Werkzeug/Flask`，存在协议层和请求体处理上的异常行为，但目前还没有拿到最终 flag

## Flag

```text
暂未获取
```

## 入口与现象

题目入口很薄，首页只有一个跳转到登录页的按钮：

```text
GET /
GET /login
```

页面文案如下：

- `Chronos Systems — Employee Portal`
- `Access Verification`
- 提示输入 `staff access code`

先做基础枚举后，能确认的路由只有 4 个：

```text
GET  /          -> 首页
GET  /login     -> 登录页
POST /login     -> 校验 access code
GET  /dashboard -> 未登录时 302 到 /login
GET  /healthz   -> 返回 {"status":"ok"}
```

服务栈也比较清晰：

- `80/tcp` 上是 `openresty/1.27.1.2`，只负责 301 到 HTTPS
- `443/tcp` 实际页面返回头是 `Werkzeug/3.1.8 Python/3.12.13`
- 页面不带 JS，也没有 `robots.txt`、公开 API、源码下载点、调试面板等额外入口

## 分析过程

### 1. 先排除最直观的登录绕过

对 `POST /login` 做了常见弱口令、时间主题单词、页面文案、日期字符串、大小写变体、JSON 体、多值参数、缺字段等测试，回包始终一致：

```text
200 OK
Invalid access code.
```

这一轮至少能说明：

- 不是简单弱口令
- 不是 `password` 参数名大小写、数组参数、多值参数这类低级解析问题
- 也不像是把题目描述里的 `wait`、`patience`、`chronos` 之类直接当作 access code

### 2. 枚举隐藏路由

常见敏感路径、Flask 调试路径、OpenAPI 路径、备份文件、静态资源穿越都测过了，只有 `/healthz` 命中：

```text
GET /healthz
-> 200 application/json
-> {"status":"ok"}
```

其余如 `/source`、`/__debugger__`、`/console`、`/openapi.json`、`/backup.zip`、`/config.py` 等都返回标准 404。

### 3. 排查 Cookie / Session 伪造

`/dashboard` 未登录时返回：

```text
302 Location: /login
Vary: Cookie
```

这说明后端大概率会读 Cookie 或 Session，但普通访问和错误登录都不会下发任何 `Set-Cookie`。我分别测试了：

- 常见明文 Cookie 名和值，如 `session=1`、`auth=true`、`logged_in=1`
- 一批常见 Flask 弱 `secret_key`
- 一批常见 Session 字段，如 `logged_in`、`authenticated`、`access_granted`、`is_admin`

目前都没有打到非 302 的响应，因此还不能把它定性成“弱签名 Flask Session”。

### 4. 排查 timing attack

题名叫 `wait`，最容易先怀疑逐字符比较的时间侧信道。但把请求固定到单个后端 IP，并改成原始 TLS 直接发包后，`POST /login` 的响应时间基本稳定在 `0.3s ~ 0.5s`，不同 payload 之间没有稳定差异。

结论：

- 之前通过高层 HTTP 客户端看到的秒级抖动，主要是网络/连接层噪声
- 目前没有足够证据支持“access code 逐字符 sleep 比较”这个利用方向

### 5. 协议层异常：请求体处理值得继续深挖

虽然 timing 分支基本排除了，但在手工发 HTTPS 原始请求时，还是发现了一个值得记下的异常点：

- 站点前面是 `openresty`
- 后面是真正处理业务的 `Werkzeug`
- 对 `POST /login` 人为构造异常 `Content-Length` 时，前后端在“什么时候把请求体视为结束”这件事上表现得不够直观

测试思路大致如下：

```text
POST /login HTTP/1.1
Host: bluehens-wait.chals.io
Content-Type: application/x-www-form-urlencoded
Content-Length: 50

password=x
```

然后继续在同一连接里补第二段数据，站点会把后续字节吞进第一次请求体，最后还是回 `Invalid access code.`。这个现象本身还不足以直接出 flag，但它说明：

- 这题很可能不是单纯的表单弱口令题
- 更像是想让人从代理层和后端解析差异入手
- 如果后续有官方附件、源码，或者能结合 Burp 的 Repeater/Smuggler 做更细的 pause-based desync 测试，这里很可能就是突破口

## 利用过程

当前还没有形成可复现的最终利用链，因此这里只保留已经确认的步骤：

1. 访问首页与登录页，确认页面极简，没有前端脚本和显式隐藏入口。
2. 枚举常见路径，只发现 `/healthz` 会返回 `{"status":"ok"}`。
3. 对 `/login` 做常规参数形态测试，回显始终是 `Invalid access code.`。
4. 对 `/dashboard` 做 Cookie、伪造 Session、弱密钥等测试，始终被 302 回 `/login`。
5. 将请求固定到单个后端 IP 后复测响应时间，排除稳定的 timing side channel。
6. 用原始 TLS 请求观察异常 `Content-Length` 场景，确认题目仍然存在进一步做协议层研究的价值。

## 关键 payload / 命令

```python
import socket
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ip = "143.244.222.115"
body = "password=x"
req = (
    "POST /login HTTP/1.1\r\n"
    "Host: bluehens-wait.chals.io\r\n"
    "Content-Type: application/x-www-form-urlencoded\r\n"
    "Content-Length: 50\r\n"
    "\r\n"
    + body
).encode()

s = socket.create_connection((ip, 443), timeout=10)
ss = ctx.wrap_socket(s, server_hostname="bluehens-wait.chals.io")
ss.sendall(req)
```

以及基础枚举：

```text
GET /
GET /login
GET /dashboard
GET /healthz
POST /login
```

## 总结

这题目前最可靠的结论不是“拿到了什么”，而是“哪些方向已经被排除”：

- 不是薄弱字典口令
- 不是明显的 Cookie/Session 明文伪造
- 不是稳定可利用的 timing attack

现阶段最像正解突破口的，仍然是 `openresty -> Werkzeug` 这层组合在异常请求体、连接复用、pause-based desync 方向上的协议差异。如果后续补到附件或继续用更底层的 HTTP 请求走读，这篇分析可以直接接着往下写。
