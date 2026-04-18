# Hens can type?

## 题目信息

- 类型：Forensics
- 题目状态：已解出
- 题目附件：`challenge1.pcapng`
- 题目描述：

```text
UD SOC team recovered a USB traffic capture from a suspicious machine on campus.

Investigators believe a user typed something important… Can you reconstruct what was typed?

Take a closer look you might find what was left behind.
```

- 核心突破点：附件是 Linux `usbmon` 抓到的 USB 流量，真正有用的是 `device 11 / endpoint 0x81` 的 8 字节 HID 键盘报告；按“修饰键 + 最多 6 个 keycode”的标准格式解码后，可以直接还原出用户输入内容

## 入口与现象

题目只给了一份 `challenge1.pcapng`，描述里明确说是 “USB traffic capture”，方向基本已经缩到 USB 取证。

先把包按 `usbmon` 头结构拆开，可以看到抓包里主要有几组中断传输：

- `device 3 / endpoint 0x81`
- `device 3 / endpoint 0x82`
- `device 11 / endpoint 0x81`

其中 `device 11 / endpoint 0x81` 的数据区非常像标准键盘 HID 报告，例如：

```text
0200180000000000
0200070000000000
0200060000000000
0200170000000000
```

这种 8 字节格式正好符合常见键盘输入报告：

- 第 1 字节：modifier（Shift、Ctrl、Alt 等）
- 第 2 字节：保留
- 第 3 到 8 字节：最多 6 个同时按下的 keycode

相比之下，`device 3 / endpoint 0x81` 的数据看起来更像别的 HID 设备，`device 3 / endpoint 0x82` 也只有极少量状态变化，所以真正该跟的是 `device 11`。

## 分析过程

### 1. 先把 `pcapng` 当成 `usbmon` 解析

这份流量不是 Windows 下常见的 USBPcap，而是 Linux `usbmon` 链路层。用 `usbmon` 的二进制头结构解析后，能稳定拿到：

- 传输类型
- 设备号
- 端点号
- 抓到的数据长度
- 实际 HID 数据区

关键头结构大小是 `64` 字节，后面跟着 `len_cap` 长度的数据区。对这题来说，只需要关注：

- `type == 'C'` 的完成包
- `xfer_type == 1` 的中断传输
- `len_cap == 8` 的 HID 报告

### 2. 锁定真正的键盘设备

把不同设备的数据模式简单统计一下，很容易发现 `device 11 / endpoint 0x81` 最像键盘：

- 大量数据都长这样：`02 00 xx 00 00 00 00 00`
- 有不少全零报告，说明是按键释放
- 第一字节经常是 `0x02`，正好对应左 Shift
- 第三字节是很小的 HID keycode，例如 `0x18`、`0x07`、`0x06`

例如：

```text
0200180000000000 -> Shift + keycode 0x18 -> U
0200070000000000 -> Shift + keycode 0x07 -> D
0200060000000000 -> Shift + keycode 0x06 -> C
0200170000000000 -> Shift + keycode 0x17 -> T
0200090000000000 -> Shift + keycode 0x09 -> F
02002f0000000000 -> Shift + keycode 0x2f -> {
```

看到这里其实已经很明显了，用户输入的内容就是一个 `UDCTF{...}` 风格的 flag。

### 3. 按 HID 键盘表恢复完整输入

剩下就是把每个报告里的新按下按键按顺序翻译出来：

- 普通状态用普通键盘映射表
- `modifier` 带 `Shift` 时切到大写/符号映射表
- 遇到全零报告就视为按键释放
- 只记录相对上一帧“新出现”的 keycode，避免长按重复计数

按这个规则解码后，完整输入为：

```text
UDCTF{k3y_StR0K3E_1S_7he_wAy}
```

这里有个容易自作主张改错的点：中间这一段是 `K3E`，看起来很多人会想当然改成 `K3S`。但从流量看，这里对应的真实按键分别是：

```text
02000e0000000000 -> K
0000200000000000 -> 3
0200080000000000 -> E
```

也就是说抓包里确实是按下了 `e` 对应的 keycode `0x08`，不是 `s` 对应的 `0x16`。同时整段输入过程中也没有出现退格，所以这里应该忠实保留为题目里实际输入的内容。

## 利用过程

1. 用 `usbmon` 的 64 字节头结构解析 `challenge1.pcapng`。
2. 只保留 `C` 型完成包里的中断传输。
3. 观察不同设备的数据形态，锁定 `device 11 / endpoint 0x81` 为键盘。
4. 按标准 USB HID 键盘格式解释 8 字节报告。
5. 处理 Shift 和按键释放，只记录新按下的 keycode。
6. 按时间顺序拼接出最终输入内容。

## 关键 payload / 命令

下面这段 Python 可以直接复现整个恢复过程：

```python
import struct
from scapy.utils import RawPcapNgReader

fmt = "<QBBBBHBBqiiII8siiII"

normal = {
    4:'a',5:'b',6:'c',7:'d',8:'e',9:'f',10:'g',11:'h',12:'i',13:'j',
    14:'k',15:'l',16:'m',17:'n',18:'o',19:'p',20:'q',21:'r',22:'s',23:'t',
    24:'u',25:'v',26:'w',27:'x',28:'y',29:'z',30:'1',31:'2',32:'3',33:'4',
    34:'5',35:'6',36:'7',37:'8',38:'9',39:'0',40:'[ENTER]',41:'[ESC]',
    42:'[BS]',43:'[TAB]',44:' ',45:'-',46:'=',47:'[',48:']',49:'\\',
    51:';',52:\"'\",53:'`',54:',',55:'.',56:'/'
}

shift = {
    4:'A',5:'B',6:'C',7:'D',8:'E',9:'F',10:'G',11:'H',12:'I',13:'J',
    14:'K',15:'L',16:'M',17:'N',18:'O',19:'P',20:'Q',21:'R',22:'S',23:'T',
    24:'U',25:'V',26:'W',27:'X',28:'Y',29:'Z',30:'!',31:'@',32:'#',33:'$',
    34:'%',35:'^',36:'&',37:'*',38:'(',39:')',40:'[ENTER]',41:'[ESC]',
    42:'[BS]',43:'[TAB]',44:' ',45:'_',46:'+',47:'{',48:'}',49:'|',
    51:':',52:'\"',53:'~',54:'<',55:'>',56:'?'
}

prev = set()
out = []

for pkt, _ in RawPcapNgReader("challenge1.pcapng"):
    header = struct.unpack(fmt, pkt[:64])
    _, pkt_type, xfer_type, ep, dev, _, _, _, _, _, _, _, len_cap, _, _, _, _, _ = header

    if not (pkt_type == ord('C') and xfer_type == 1 and dev == 11 and ep == 0x81 and len_cap == 8):
        continue

    report = list(pkt[64:72])
    mods = report[0]
    keys = [k for k in report[2:] if k]
    curr = set(keys)
    new_keys = [k for k in keys if k not in prev]

    for key in new_keys:
        table = shift if (mods & 0x22 or mods & 0x02 or mods & 0x20) else normal
        out.append(table.get(key, f"[0x{key:02x}]"))

    prev = curr

print("".join(out))
```

输出：

```text
UDCTF{k3y_StR0K3E_1S_7he_wAy}
```

## Flag

```text
UDCTF{k3y_StR0K3E_1S_7he_wAy}
```

## 总结

这题本质上就是一道 USB 键盘取证题，难点不在 HID 表本身，而在于先分清抓包格式和设备角色。只要识别出这是 `usbmon`，再从多台 HID 设备里筛出真正的键盘，后面的恢复链路就很短：找到 8 字节报告、处理 Shift、去掉长按重复，最后按时间顺序拼接即可。
