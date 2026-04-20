# [MoeCTF 2022]EquationPy

## 题目信息

- 类型：Reverse
- 题目状态：已解出
- 附件：`EquationPy-38.pyc`
- 核心点：`pyc` 不是机器码，而是 Python 字节码；把字节码反汇编后，可以直接还原出一组线性方程

## Flag

```text
moectf{z3_i5_he1pful!}
```

## Python 逆向和 pyc 逆向是怎么一回事

这题本身就在问这两个问题，所以先把概念说清楚。

Python 逆向和 C/C++ 逆向不一样。`exe`、`elf` 那类文件面对的是机器指令；`pyc` 面对的是 Python 虚拟机字节码。也就是说，`pyc` 仍然保留了大量高级语言层面的信息，比如：

- 常量表 `co_consts`
- 名字表 `co_names`
- 代码对象 `code object`
- 一条条可读的字节码指令

所以 `pyc` 逆向的核心思路通常不是“硬啃汇编”，而是：

1. 先确认它是哪一代 Python 的字节码
2. 取出 `marshal` 序列化后的 `code object`
3. 用 `dis` 反汇编
4. 看是否能直接恢复源码逻辑；如果不能，就按字节码语义手工还原

这道题就是一个很标准的例子。

## 入口与初看

题目附件只有一个 `EquationPy-38.pyc`。文件名里的 `38` 已经很像 Python 3.8 的提示；我本地是 Python 3.10，再看文件头也能确认它不是当前解释器版本生成的：

```text
550d0d0a00000000d5e5d762c42c0000
```

我先没有去找网上反编译器，也没有参考现成 WP，而是直接用 Python 自带能力把它拆开：

```python
import marshal
import dis

with open("EquationPy-38.pyc", "rb") as f:
    f.read(16)          # 跳过 pyc 头
    code = marshal.load(f)

print(code)
print(code.co_names)
print(code.co_consts[:10])
dis.dis(code)
```

这里最关键的一步是 `marshal.load(f)`。`pyc` 的主体其实就是序列化后的 `code object`，拿到它之后，后面就完全进入 Python 自己的世界了。

## 分析过程

反汇编后，很快能看到程序整体结构：

1. 先打印两句提示
2. 读入 `flag`
3. 判断 `len(flag) == 22`
4. 连续做很多次 `ord(flag[i]) * 常数` 的加法
5. 把每一组和一个常数比较
6. 全部满足才输出成功

开头一段字节码已经很明显：

```text
LOAD_NAME                1 (input)
LOAD_CONST               2 ('Input your flag:')
CALL_FUNCTION            1
STORE_NAME               2 (flag)
LOAD_NAME                3 (len)
LOAD_NAME                2 (flag)
CALL_FUNCTION            1
LOAD_CONST               3 (22)
COMPARE_OP               2 (==)
POP_JUMP_IF_FALSE     ...
```

后面就是大量重复结构，例如第一组校验：

```text
ord(flag[0]) * 7072 +
ord(flag[1]) * 2523 +
ord(flag[2]) * 6714 +
...
ord(flag[21]) * 57
== 10743134
```

这已经不是“猜字符串”问题，而是一个标准线性方程组问题。22 个字符就是 22 个未知数，程序一共给了 22 条方程，刚好可以直接求。

## 把字节码还原成方程组

我没有手抄 22 组系数，而是直接对反汇编指令做了一次很轻量的符号执行，只处理这题真正用到的几种操作：

- `LOAD_CONST`
- `LOAD_NAME`
- `BINARY_SUBSCR`
- `CALL_FUNCTION`
- `BINARY_MULTIPLY`
- `BINARY_ADD`
- `COMPARE_OP`

核心思路是把 `ord(flag[i])` 记成第 `i` 个未知数，然后一路把表达式堆栈还原出来。

下面这段脚本就足够把矩阵和最终答案抽出来：

```python
import marshal
import dis
from sympy import Matrix

with open("EquationPy-38.pyc", "rb") as f:
    f.read(16)
    code = marshal.load(f)

ins = list(dis.get_instructions(code))
stack = []
eqs = []
started = False

for insn in ins:
    op = insn.opname
    arg = insn.argval

    if op == "LOAD_NAME":
        stack.append(("name", arg))
    elif op == "LOAD_CONST":
        stack.append(("const", arg))
    elif op == "CALL_FUNCTION":
        argc = insn.arg
        args = [stack.pop() for _ in range(argc)][::-1]
        func = stack.pop()
        if func == ("name", "ord"):
            idx = args[0][2][1]
            stack.append(("var", idx))
            started = True
        elif func == ("name", "len"):
            stack.append(("len",))
        else:
            stack.append(("call", func, args))
    elif op == "POP_TOP":
        stack.pop()
    elif op == "STORE_NAME":
        stack.pop()
    elif op == "BINARY_SUBSCR":
        idx = stack.pop()
        obj = stack.pop()
        stack.append(("sub", obj, idx))
    elif op == "BINARY_MULTIPLY":
        b = stack.pop()
        a = stack.pop()
        stack.append(("mul", a, b))
    elif op == "BINARY_ADD":
        b = stack.pop()
        a = stack.pop()
        stack.append(("add", a, b))
    elif op == "COMPARE_OP":
        b = stack.pop()
        a = stack.pop()
        stack.append(("cmp", insn.argval, a, b))
    elif op == "POP_JUMP_IF_FALSE":
        cond = stack.pop()
        if cond[0] == "cmp" and cond[1] == "==" and started:
            eqs.append(cond)

def linear(expr):
    tag = expr[0]
    if tag == "const":
        return {}, expr[1]
    if tag == "var":
        return {expr[1]: 1}, 0
    if tag == "mul":
        a, b = expr[1], expr[2]
        if a[0] == "const":
            coeffs, bias = linear(b)
            k = a[1]
        else:
            coeffs, bias = linear(a)
            k = b[1]
        return {i: v * k for i, v in coeffs.items()}, bias * k
    if tag == "add":
        c1, b1 = linear(expr[1])
        c2, b2 = linear(expr[2])
        for i, v in c2.items():
            c1[i] = c1.get(i, 0) + v
        return c1, b1 + b2
    raise ValueError(expr)

rows = []
rhs = []
for _, _, left, right in eqs:
    coeffs, _ = linear(left)
    rows.append([coeffs.get(i, 0) for i in range(22)])
    rhs.append(right[1])

M = Matrix(rows)
B = Matrix(rhs)
sol = [int(x) for x in M.LUsolve(B)]
flag = "".join(map(chr, sol))

print(flag)
print(all(sum(rows[r][i] * sol[i] for i in range(22)) == rhs[r] for r in range(22)))
```

运行结果：

```text
moectf{z3_i5_he1pful!}
True
```

这里 `True` 表示 22 条方程全部验证通过，不是误撞出来的字符串。

## 关键证据

- `len(flag) == 22` 直接给出了未知数字符数量
- 字节码中只有 `print`、`input`、`len`、`ord` 这些名字，没有更复杂的加密逻辑
- 主体校验全都是 `ord(flag[i]) * 系数` 的线性组合，没有分支混淆，也没有位运算
- 一共抽出 22 条方程，矩阵满秩，可以唯一解出

我本地最后验证到的关键信息如下：

```text
header= 550d0d0a00000000d5e5d762c42c0000
equations= 22
flag= moectf{z3_i5_he1pful!}
all_ascii= True
verify= True
```

## 总结

这题本质上不是在考 Python 黑魔法，而是在考你会不会把 `pyc` 当作“可读的字节码程序”来看。

真正有效的路线只有两步：

1. 用 `marshal + dis` 把 `pyc` 还原成可分析的字节码逻辑
2. 识别出它实际上是在检查一个 22 元一次方程组，然后直接求解

所以“pyc 文件怎么逆向”这个问题，放到这题里的答案就是：先拿回 `code object`，再站在 Python 虚拟机指令层去理解它，而不是把它想得和本地机器码逆向一样重。
