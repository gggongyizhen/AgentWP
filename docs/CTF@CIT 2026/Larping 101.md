# Larping 101

## 题目信息

- 类型：Forensics
- 题目状态：已解出
- 附件：`challenge.pptx`
- 核心思路：把 `pptx` 当作 OOXML 压缩包解开，检查未被 PowerPoint 正常引用的隐藏 XML 文件，从中直接恢复 flag

## 入口与现象

题目只给了一个 `challenge.pptx`，题面提示是：

```text
To larp, one must become the larper..

What do you think of my presentation? It feels like it might be missing something so maybe you can tell me what it is?
```

这类题第一反应不是直接看幻灯片内容，而是把 `pptx` 当作 Zip 容器处理。`pptx/docx/xlsx` 本质上都是 OOXML 包，经常会把线索藏在关系文件、元数据、孤儿部件或者非标准 XML 里。

先列出附件内部结构：

```powershell
tar -tf challenge.pptx
```

可以看到里面主要是常规的 4 页幻灯片、若干图片和 XML：

```text
[Content_Types].xml
docProps/core.xml
ppt/_rels/presentation.xml.rels
ppt/presentation.xml
ppt/slides/slide1.xml
ppt/slides/slide2.xml
ppt/slides/slide3.xml
ppt/slides/slide4.xml
ppt/slides/transitions.xml
ppt/media/image1.png
...
```

其中最显眼的异常点是：除了正常的 `slide1.xml` 到 `slide4.xml` 之外，还多了一个 `ppt/slides/transitions.xml`。

## 分析过程

先把文档解包出来，再全局搜可疑字符串：

```powershell
New-Item -ItemType Directory -Force challenge_extracted | Out-Null
tar -xf challenge.pptx -C challenge_extracted
rg -n -a "flag|cit|CTF|hidden|secret|missing|note|comment|larp|become|larper" challenge_extracted
```

搜索结果直接命中了一个异常文件：

```text
challenge_extracted\ppt\slides\transitions.xml:27:            <p:note>legacy feature disabled in runtime</p:note>
```

继续查看这个文件内容：

```powershell
Get-Content -Raw "challenge_extracted\ppt\slides\transitions.xml"
```

可以看到：

```xml
<p:transition id="morph">
    <p:enabled>false</p:enabled>
    <p:note>legacy feature disabled in runtime</p:note>
</p:transition>

<p:debug>
    <p:log level="info">transition engine initialized</p:log>
    <p:log level="warning">compatibility mode enabled</p:log>

    <p:reserved>
        CIT{l4rp_l4rp_l4rp_s4hur}
    </p:reserved>
</p:debug>
```

到这里其实已经拿到 flag 了，但还要再确认为什么它会被“藏住”。

继续检查 `ppt` 的主关系文件：

```powershell
Get-Content -Raw "challenge_extracted\ppt\_rels\presentation.xml.rels"
```

里面只引用了主题、母版、4 张幻灯片和 `presProps.xml`：

```xml
<Relationship Id="rId3" Type=".../slide" Target="slides/slide1.xml"/>
<Relationship Id="rId4" Type=".../slide" Target="slides/slide2.xml"/>
<Relationship Id="rId5" Type=".../slide" Target="slides/slide3.xml"/>
<Relationship Id="rId6" Type=".../slide" Target="slides/slide4.xml"/>
```

并没有任何一条关系指向 `ppt/slides/transitions.xml`。

再看 `[Content_Types].xml`：

```powershell
Get-Content -Raw -LiteralPath "challenge_extracted\[Content_Types].xml"
```

其中只注册了 4 个 slide：

```xml
<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
<Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
<Override PartName="/ppt/slides/slide3.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
<Override PartName="/ppt/slides/slide4.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
```

`transitions.xml` 没有被单独注册，也没有被关系文件引用，本质上就是一个塞在 OOXML 包里的孤儿文件。PowerPoint 打开时不会把它当成正常演示内容渲染出来，但解包检查时它仍然会完整保留。

这也解释了题面那句 “it might be missing something” 的意思：缺失的不是某一页表面上的文字，而是没有被正常展示出来的隐藏部件。

## 利用过程

1. 把 `challenge.pptx` 当作 Zip/OOXML 包而不是普通演示文稿看待。
2. 列出内部文件，发现 `ppt/slides/transitions.xml` 这个不太对劲的 XML。
3. 解包后全局搜字符串，发现该文件含有 `legacy feature disabled in runtime` 之类的可疑调试文本。
4. 直接打开 `transitions.xml`，在 `<p:reserved>` 节点中读到 flag。
5. 通过 `presentation.xml.rels` 和 `[Content_Types].xml` 验证该文件是未被正常引用的孤儿部件，说明这不是 PowerPoint 可见内容，而是刻意藏在附件里的取证线索。

## 关键命令

```powershell
tar -tf challenge.pptx

New-Item -ItemType Directory -Force challenge_extracted | Out-Null
tar -xf challenge.pptx -C challenge_extracted

rg -n -a "flag|cit|CTF|hidden|secret|missing|note|comment|larp|become|larper" challenge_extracted

Get-Content -Raw "challenge_extracted\ppt\slides\transitions.xml"
Get-Content -Raw "challenge_extracted\ppt\_rels\presentation.xml.rels"
Get-Content -Raw -LiteralPath "challenge_extracted\[Content_Types].xml"
```

## Flag

```text
CIT{l4rp_l4rp_l4rp_s4hur}
```

## 总结

这题的关键不是图片隐写，也不是宏或备注，而是把 `pptx` 当成 OOXML 容器来做文件取证。真正的突破点在于发现 `ppt/slides/transitions.xml` 是一个没有被关系文件引用的孤儿 XML，里面残留了调试/保留字段，flag 就明文藏在 `<p:reserved>` 节点中。
