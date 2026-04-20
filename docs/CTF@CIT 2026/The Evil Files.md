# The Evil Files

## 题目信息

- 类型：Forensics
- 题目状态：已解出
- 题目描述：Dr. Evil be dreamin and schemin
- 附件：`challenge.pdf`
- 核心考点：PDF 伪打码，黑框只遮住了视觉显示，但没有真正移除文本对象

## 入口与现象

附件只有一个 PDF。第一页看上去像是一封 Dr. Evil 发出的邮件，`FROM`、`TO`、`CC` 后面的内容都被黑框遮住了，第一反应很像“红action 取证”。

![PDF 顶部红框区域](../../image/The%20Evil%20Files/header-redaction.png)

这类题最重要的一点是不要先入为主地相信“黑框就等于删掉内容”。PDF 很常见的失误是只画一个黑色矩形把敏感字段盖住，但底层文本对象还完整保留在文档流里，复制、选中或直接解析都能把原文拿出来。

## 分析过程

先直接抽文本层，而不是盯着渲染结果看。用 `pypdf` 读取第一页文本：

```python
from pypdf import PdfReader

reader = PdfReader("challenge.pdf")
print(reader.pages[0].extract_text())
```

输出里最关键的几行是：

```text
FROM: laser.shark.master@villainhq.net
      TO: tiny.turmoil@domination.co
      CC: CIT{m0j0_eng4g3d}
Subject: RE: Plan to take over the world
```

到这里其实已经拿到 flag 了。也就是说，题目并不是要求去恢复损坏文件、爆破密码或者做 OCR，而是单纯检查这份 PDF 有没有把“被遮住的内容”真正删掉。

为了确认不是 `extract_text()` 的偶然行为，我又看了一下第一页的内容流。顶部区域能看到两类连续指令：

```text
0 0 0 rg
100.4 721.55 157.25 13.75 re f*
...
100.45 724.1 Td /F2 12 Tf[...]TJ
```

这里的含义很直接：

1. `0 0 0 rg` 把绘图颜色设置成黑色。
2. `100.4 721.55 157.25 13.75 re f*` 画出一个填充的黑色矩形，也就是我们肉眼看到的黑框。
3. 后面的 `Td /F2 12 Tf ... TJ` 仍然在同一片区域绘制文本对象。

也就是说，这不是“安全 redaction”，而是“先画个黑框，再把文字也用黑色画出来”。显示层看不见，不代表文本消失了。

## 利用过程

1. 打开 `challenge.pdf`，观察到邮件头部的敏感信息被黑框遮住，判断优先方向是 PDF 伪打码。
2. 使用 `pypdf` 提取第一页文本层，直接拿到完整邮件内容。
3. 在文本输出中发现 `CC: CIT{m0j0_eng4g3d}`，确认 flag 已经明文保留在 PDF 中。
4. 继续检查页面内容流，确认黑框和正文是两个独立对象，文本并没有被删除，只是被视觉遮挡。

## 关键 payload / 命令

```powershell
@'
from pypdf import PdfReader

reader = PdfReader("challenge.pdf")
print(reader.pages[0].extract_text())
'@ | python -
```

如果想进一步验证“黑框不等于删字”，可以把内容流也打印出来：

```powershell
@'
from pypdf import PdfReader

reader = PdfReader("challenge.pdf")
content = reader.pages[0].get_contents().get_data().decode("latin1", "ignore")
print(content)
'@ | python -
```

## Flag

```text
CIT{m0j0_eng4g3d}
```

## 总结

这题的核心非常典型：PDF 里的黑框只是视觉层遮挡，不是真正的 redaction。只要文本对象还留在文档里，直接抽文本层就能把所谓“隐藏信息”全部拿回来。遇到这类 PDF 取证题，优先尝试复制文本、导出文本层或检查内容流，通常比一上来做图像处理更有效。
