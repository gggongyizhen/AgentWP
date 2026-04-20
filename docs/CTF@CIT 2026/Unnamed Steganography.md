# Unnamed Steganography

## 题目信息

- 类型：Misc / Steganography
- 题目状态：已解出
- 目标：从附件 `flag.jpg` 中找到隐藏信息
- 核心突破点：flag 直接写在 JPEG EXIF 的 `ImageDescription` 字段里

题目原始标题和描述没有提供，用户给出的内容还是占位符，所以这里先用 `Unnamed Steganography` 作为文章名。

## 入口与现象

附件只有一张 JPEG 图片，直接打开后可见内容如下：

![题目附件](../../image/Unnamed%20Steganography/flag.jpg)

图片正文只显示一句：

```text
[INSERT A HIDDEN MESSAGE OR SOMETHING..]
```

这类题的第一步先不要急着跑大工具，先看文件结构、可读字符串和元数据。对 `flag.jpg` 做基础检查后，有两个很快就能确认的现象：

1. 文件头是标准 JPEG/JFIF，并带有一段 EXIF。
2. 直接扫可打印字符串时，在文件前部就出现了 `CIT{ur_w4rm1ng_up_n0w}`。

## 分析过程

先看字符串扫描结果，flag 出现得非常靠前：

```text
00000068: CIT{ur_w4rm1ng_up_n0w}
```

这个偏移在 JPEG 头部附近，不像是图像压缩数据区，更像是某个 metadata 字段。继续把 EXIF 结构解析出来，可以看到它确实落在 `ImageDescription` 标签里：

```text
entries 5
ImageDescription 0x10e type 2 count 23 val/off 0x4a
 ascii= CIT{ur_w4rm1ng_up_n0w}
XResolution 0x11a type 5 count 1 val/off 0x62
 rational= 72/1
YResolution 0x11b type 5 count 1 val/off 0x6a
 rational= 72/1
```

同时又补了一轮排除：

- `binwalk flag.jpg` 没识别出额外嵌入文件。
- JPEG 结束标记 `FFD9` 出现在文件末尾，后面没有附加 ZIP/7z/RAR 等尾随数据。
- 文件段结构很简单，只有 `JFIF`、`EXIF`、量化表、霍夫曼表和图像数据，没有二次容器。

因此这题并不是更深层的 LSB 或追加文件题，而是最直接的 metadata 隐写题。题面图片本身只是一个提示，真正的隐藏信息在 EXIF 描述字段里。

## 关键命令 / 中间结果

先扫字符串：

```powershell
@'
from pathlib import Path
import re

b = Path("flag.jpg").read_bytes()
for m in re.finditer(rb"[ -~]{6,}", b):
    s = m.group().decode("ascii", errors="ignore")
    if "CIT{" in s:
        print(hex(m.start()), s)
'@ | .\.venv\Scripts\python -
```

再解析 EXIF，确认字段名和值：

```powershell
@'
from pathlib import Path
from struct import unpack

b = Path("flag.jpg").read_bytes()
start = b.find(b"Exif\x00\x00")
tiff = start + 6
endian = ">" if b[tiff:tiff+2] == b"MM" else "<"
ifd0_off = unpack(endian + "I", b[tiff+4:tiff+8])[0]
base = tiff
pos = base + ifd0_off
count = unpack(endian + "H", b[pos:pos+2])[0]
tags = {0x010E: "ImageDescription"}

for n in range(count):
    e = pos + 2 + n * 12
    tag, typ, cnt, val = unpack(endian + "HHII", b[e:e+12])
    if tag == 0x010E:
        raw = b[base + val:base + val + cnt]
        print(tags[tag], raw.rstrip(b"\x00").decode())
'@ | .\.venv\Scripts\python -
```

## Flag

```text
CIT{ur_w4rm1ng_up_n0w}
```

## 总结

这题的关键不在复杂隐写，而在先做最基础的元数据检查。`flag.jpg` 的 EXIF `ImageDescription` 里已经直接写了 flag，只要先看文件头、字符串和 EXIF，就可以很快结束，不需要把时间浪费在更重的图像隐写工具上。
