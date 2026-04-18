# Blind Hens

## 题目信息

- 类型：Misc
- 题目状态：已解出
- 题目附件：`memo.txt`
- 题目描述：

```text
We recovered a routine internal memo from a workstation flagged during an investigation. Nothing in the visible contents appears unusual, but analysts believe a message was hidden in plain sight.

Review everything carefully even the smallest details can be important. Some internal policies may hold the key.
```

- 核心突破点：行尾空白里的 `tab/space` 隐写先还原出一段 Base64，再结合题面里的 `policy #23` 将 `23` 解释为十六进制异或键 `0x23`

## 入口与现象

先看 `memo.txt` 的正文，内容几乎全是正常的内部通知和一长串 `Policy appendix note xx remains unchanged...`，肉眼很难直接发现异常。

但题面专门强调了两件事：

1. `even the smallest details can be important`
2. `Some internal policies may hold the key`

第一句很像在提示“最小细节”，也就是空格、制表符、标点这类容易被忽略的内容；第二句则像是在提示后续解密的 key 跟 `policy #23` 有关。

检查文件十六进制内容后，可以看到多行文本结尾都带有固定长度的 `space/tab` 混合空白。例如：

```text
Badge access requests must be submitted through the internal portal. <SP><TAB><TAB><SP><SP><TAB><SP><SP>
Conference room reservations now require manager approval.         <SP><TAB><TAB><SP><TAB><TAB><SP><TAB>
Archived invoices older than 2024 should be moved to cold storage. <SP><TAB><TAB><SP><SP><TAB><SP><SP>
```

这说明正文本身只是掩护，真正的数据藏在每一行末尾的空白里。

## 分析过程

### 1. 把行尾空白转成二进制

把每行结尾的空白提取出来，约定：

- `space = 0`
- `tab = 1`

这样每 8 个空白字符正好对应 1 个字节。把所有带尾随空白的行依次转换后，可以得到一串可打印字符：

```text
dmdgd2VYE04VfFRLEhQQfBZTF0AQfEcQQBNHEk0VfBIWfBd8FEsSTRUcXg==
```

这一串字符明显很像 Base64。

### 2. Base64 解码得到第二层密文

对上面的字符串做 Base64 解码，得到 43 字节的内容：

```text
76 67 60 77 65 58 13 4E 15 7C 54 4B 12 14 10 7C 16 53 17 40 10 7C 47 10 40 13 47 12 4D 15 7C 12 16 7C 17 7C 14 4B 12 4D 15 1C 5E
```

直接看这批字节还是没有可读意义，说明还有一层处理。

### 3. 用 `policy #23` 作为异或提示

正文里有一句很突兀的话：

```text
Oh btw please ensure compliance with policy #23
```

如果直接拿十进制 `23` 去异或，结果并不可读；但把它理解成十六进制 `0x23` 后，整段数据会立刻变成标准 flag：

```text
UDCTF{0m6_wh173_5p4c3_d3c0d1n6_15_4_7h1n6?}
```

这里题面里的 `Some internal policies may hold the key` 也就闭合了：`policy #23` 不是正文信息，而是最终解密所需的 xor key。

## 利用过程

1. 打开 `memo.txt`，发现可见正文没有明显异常。
2. 根据题面里 “smallest details” 的提示，检查行尾空白字符。
3. 提取所有尾随 `space/tab`，按 `space=0`、`tab=1` 转成字节。
4. 将得到的结果拼接后，识别出其为 Base64 字符串。
5. 对 Base64 解码，得到第二层二进制密文。
6. 根据 `policy #23` 提示，使用 `0x23` 进行逐字节异或。
7. 还原出最终 flag。

## 关键 payload / 命令

下面这段 PowerShell 可以完整复现提取过程：

```powershell
$lines = Get-Content memo.txt
$s = ''

foreach ($line in $lines) {
    $m = [regex]::Match($line, '[\t ]+$')
    if ($m.Success) {
        $bits = ($m.Value.ToCharArray() | ForEach-Object {
            if ($_ -eq "`t") { '1' } else { '0' }
        }) -join ''
        $s += [char][Convert]::ToInt32($bits, 2)
    }
}

$bytes = [Convert]::FromBase64String($s) | ForEach-Object { $_ -bxor 0x23 }
($bytes | ForEach-Object { [char]$_ }) -join ''
```

输出：

```text
UDCTF{0m6_wh173_5p4c3_d3c0d1n6_15_4_7h1n6?}
```

## Flag

```text
UDCTF{0m6_wh173_5p4c3_d3c0d1n6_15_4_7h1n6?}
```

## 总结

这题本质上是一个非常典型的文本空白隐写题，但它没有把 payload 直接藏成明文，而是多套了一层 Base64 和一层异或。真正有价值的线索只有两个：一个是题面强调“最小细节”，把注意力引到行尾空白；另一个是正文里那句突兀的 `policy #23`，提示最终要用 `0x23` 做异或。两条线索拼起来以后，恢复 flag 的链路就很短了。
